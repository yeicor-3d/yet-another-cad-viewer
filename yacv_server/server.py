import asyncio
import atexit
import os
import signal
import sys
import time
from dataclasses import dataclass
from threading import Thread
from typing import Optional, Dict, Union

import aiohttp_cors
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
from aiohttp import web
from aiohttp_sse import sse_response
from build123d import Shape, Axis, Location, Vector
from dataclasses_json import dataclass_json

from cad import get_shape, grab_all_cad, image_to_gltf
from mylogger import logger
from pubsub import BufferedPubSub
from tessellate import _hashcode, tessellate

# Find the frontend folder (optional, but recommended)
FILE_DIR = os.path.dirname(__file__)
FRONTEND_BASE_PATH = os.getenv('FRONTEND_BASE_PATH', os.path.join(FILE_DIR, 'frontend'))
if not os.path.exists(FRONTEND_BASE_PATH):
    if os.path.exists(os.path.join(FILE_DIR, '..', 'dist')):  # Fallback to dev build
        FRONTEND_BASE_PATH = os.path.join(FILE_DIR, '..', 'dist')
    else:
        logger.warning('Frontend not found at %s', FRONTEND_BASE_PATH)
        FRONTEND_BASE_PATH = None

# Define the API paths (also available at the root path for simplicity)
UPDATES_API_PATH = '/api/updates'
OBJECTS_API_PATH = '/api/object'  # /{name}


@dataclass_json
@dataclass
class UpdatesApiData:
    """Data sent to the client through the updates API"""
    name: str
    """Name of the object. Should be unique unless you want to overwrite the previous object"""
    hash: str
    """Hash of the object, to detect changes without rebuilding the object"""


class UpdatesApiFullData(UpdatesApiData):
    obj: Optional[TopoDS_Shape]
    """The OCCT object, if any (not serialized)"""
    kwargs: Optional[Dict[str, any]]
    """The show_object options, if any (not serialized)"""

    def __init__(self, name: str, hash: str, obj: Optional[TopoDS_Shape] = None,
                 kwargs: Optional[Dict[str, any]] = None):
        self.name = name
        self.hash = hash
        self.obj = obj
        self.kwargs = kwargs

    def to_json(self) -> str:
        # noinspection PyUnresolvedReferences
        return super().to_json()


# noinspection PyUnusedLocal
async def _index_handler(request: web.Request) -> web.Response:
    return web.HTTPTemporaryRedirect(location='index.html')


class Server:
    app = web.Application()
    runner: web.AppRunner
    thread: Optional[Thread] = None
    startup_complete = asyncio.Event()
    do_shutdown = asyncio.Event()
    at_least_one_client = asyncio.Event()
    show_events = BufferedPubSub[UpdatesApiFullData]()
    object_events: Dict[str, BufferedPubSub[bytes]] = {}
    object_events_lock = asyncio.Lock()
    frontend_lock = asyncio.Lock()  # To avoid exiting too early while frontend makes requests

    def __init__(self, *args, **kwargs):
        # --- Routes ---
        # - APIs
        self.app.router.add_route('GET', f'{UPDATES_API_PATH}', self._api_updates)
        self.app.router.add_route('GET', f'{OBJECTS_API_PATH}/{{name}}', self._api_object)
        # - Single websocket/objects/frontend entrypoint to ease client configuration
        self.app.router.add_get('/', self._entrypoint)
        # - Static files from the frontend
        self.app.router.add_get('/{path:(.*/|)}', _index_handler)  # Any folder -> index.html
        if FRONTEND_BASE_PATH is not None:
            self.app.router.add_static('/', path=FRONTEND_BASE_PATH, name='static_frontend')
        # --- CORS ---
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        for route in list(self.app.router.routes()):
            cors.add(route)
        # --- Misc ---
        self.loop = asyncio.new_event_loop()

    def start(self):
        """Starts the web server in the background"""
        assert self.thread is None, "Server currently running, cannot start another one"
        # Start the server in a separate daemon thread
        self.thread = Thread(target=self._run_server, name='yacv_server', daemon=True)
        signal.signal(signal.SIGINT | signal.SIGTERM, self.stop)
        atexit.register(self.stop)
        self.thread.start()
        logger.info('Server started (requested)...')
        # Wait for the server to be ready before returning
        while not self.startup_complete.is_set():
            time.sleep(0.01)
        logger.info('Server started (received)...')

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Stops the web server"""
        if self.thread is None:
            print('Cannot stop server because it is not running')
            return

        if os.getenv('YACV_STOP_EARLY', '') == '':
            # Make sure we can hold the lock for more than 100ms (to avoid exiting too early)
            logger.info('Stopping server (waiting for at least one frontend request first, cancel with CTRL+C)...')
            try:
                while not self.at_least_one_client.is_set():
                    time.sleep(0.01)
            except KeyboardInterrupt:
                pass

            logger.info('Stopping server (waiting for no more frontend requests)...')
            acquired = time.time()
            while time.time() - acquired < 1.0:
                if self.frontend_lock.locked():
                    acquired = time.time()
                time.sleep(0.01)

        # Stop the server in the background
        self.loop.call_soon_threadsafe(lambda *a: self.do_shutdown.set())
        logger.info('Stopping server (sent)...')

        # Wait for the server to stop gracefully
        self.thread.join(timeout=30)
        self.thread = None
        logger.info('Stopping server (confirmed)...')
        if len(args) >= 1 and args[0] in (signal.SIGINT, signal.SIGTERM):
            sys.exit(0)  # Exit with success

    def _run_server(self):
        """Runs the web server"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._run_server_async())
        self.loop.stop()
        self.loop.close()

    async def _run_server_async(self):
        """Runs the web server (async)"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, os.getenv('YACV_HOST', 'localhost'), int(os.getenv('YACV_PORT', 32323)))
        await site.start()
        logger.info('Server started (sent)...')
        self.startup_complete.set()
        # Wait for a signal to stop the server while running
        await self.do_shutdown.wait()
        logger.info('Stopping server (received)...')
        await runner.shutdown()
        # await runner.cleanup()  # Gets stuck?
        logger.info('Stopping server (done)...')

    async def _entrypoint(self, request: web.Request) -> web.StreamResponse:
        """Main entrypoint to the server, which automatically serves the frontend/updates/objects"""
        if request.query.get('api_updates', '') != '':  # ?api_updates -> updates API
            return await self._api_updates(request)
        elif request.query.get('api_object', '') != '':  # ?api_object={name} -> object API
            request.match_info['name'] = request.query['api_object']
            return await self._api_object(request)
        else:  # Anything else -> frontend index.html
            return await _index_handler(request)

    async def _api_updates(self, request: web.Request) -> web.StreamResponse:
        """Handles a publish-only websocket connection that send show_object events along with their hashes and URLs"""
        self.at_least_one_client.set()
        async with sse_response(request) as resp:
            logger.debug('Client connected: %s', request.remote)
            resp.ping_interval = 0.1  # HACK: forces flushing of the buffer

            # Send buffered events first, while keeping a lock
            async with self.frontend_lock:
                for data in self.show_events.buffer():
                    logger.debug('Sending info about %s to %s: %s', data.name, request.remote, data)
                    # noinspection PyUnresolvedReferences
                    await resp.send(data.to_json())

            # Send future events over the same connection
            subscription = self.show_events.subscribe(include_buffered=False)
            try:
                async for data in subscription:
                    logger.debug('Sending info about %s to %s: %s', data.name, request.remote, data)
                    # noinspection PyUnresolvedReferences
                    await resp.send(data.to_json())
            finally:
                await subscription.aclose()
                logger.debug('Client disconnected: %s', request.remote)

        return resp

    obj_counter = 0

    def _show_common(self, name: Optional[str], hash: str, start: float, obj: Optional[TopoDS_Shape] = None,
                     kwargs=None):
        name = name or f'object_{self.obj_counter}'
        self.obj_counter += 1
        # Remove a previous object with the same name
        for old_event in self.show_events.buffer():
            if old_event.name == name:
                self.show_events.delete(old_event)
                if name in self.object_events:
                    del self.object_events[name]
                break
        precomputed_info = UpdatesApiFullData(name=name, hash=hash, obj=obj, kwargs=kwargs or {})
        self.show_events.publish_nowait(precomputed_info)
        logger.info('show_object(%s, %s) took %.3f seconds', name, hash, time.time() - start)
        return precomputed_info

    def show(self, any_object: Union[bytes, TopoDS_Shape, any], name: Optional[str] = None, **kwargs):
        """Publishes "any" object to the server"""
        if isinstance(any_object, bytes):
            self.show_gltf(any_object, name, **kwargs)
        else:
            self.show_cad(any_object, name, **kwargs)

    def show_gltf(self, gltf: bytes, name: Optional[str] = None, **kwargs):
        """Publishes any single-file GLTF object to the server."""
        start = time.time()
        # Precompute the info and send it to the client as if it was a CAD object
        precomputed_info = self._show_common(name, _hashcode(gltf, **kwargs), start, kwargs=kwargs)
        # Also pre-populate the GLTF data for the object API
        publish_to = BufferedPubSub[bytes]()
        publish_to.publish_nowait(gltf)
        publish_to.publish_nowait(b'')  # Signal the end of the stream
        self.object_events[precomputed_info.name] = publish_to

    def show_image(self, source: str | bytes, center: any, ppmm: int, name: Optional[str] = None,
                   save_mime: str = 'image/jpeg', **kwargs):
        """Publishes an image as a quad GLTF object, indicating the center location and pixels per millimeter."""
        # Convert the image to a GLTF CAD object
        gltf, name = image_to_gltf(source, center, ppmm, name, save_mime)
        # Publish it like any other GLTF object
        self.show_gltf(gltf, name, **kwargs)

    def show_cad(self, obj: Union[TopoDS_Shape, any], name: Optional[str] = None, **kwargs):
        """Publishes a CAD object to the server"""
        start = time.time()

        # Get the shape of a CAD-like object
        obj = get_shape(obj)

        # Convert Z-up (OCCT convention) to Y-up (GLTF convention)
        if isinstance(obj, TopoDS_Shape):
            obj = Shape(obj).rotate(Axis.X, -90).wrapped
        elif isinstance(obj, TopLoc_Location):
            tmp_location = Location(obj)
            tmp_location.position = Vector(tmp_location.position.X, tmp_location.position.Z, -tmp_location.position.Y)
            tmp_location.orientation = Vector(tmp_location.orientation.X - 90, tmp_location.orientation.Y,
                                              tmp_location.orientation.Z)
            obj = tmp_location.wrapped

        self._show_common(name, _hashcode(obj, **kwargs), start, obj, kwargs)

    def show_cad_all(self, **kwargs):
        """Publishes all CAD objects to the server"""
        for name, obj in grab_all_cad():
            self.show_cad(obj, name, **kwargs)

    async def _api_object(self, request: web.Request) -> web.Response:
        """Returns the object file with the matching name, building it if necessary."""
        async with self.frontend_lock:
            # Export the object (or fail if not found)
            exported_glb = await self.export(request.match_info['name'])

            # Wrap the GLB in a response and return it
            response = web.Response(body=exported_glb)
            response.content_type = 'model/gltf-binary'
            response.headers['Content-Disposition'] = f'attachment; filename="{request.match_info["name"]}.glb"'
            return response

    def shown_object_names(self) -> list[str]:
        """Returns the names of all objects that have been shown"""
        return list([obj.name for obj in self.show_events.buffer()])

    def _shown_object(self, name: str) -> Optional[UpdatesApiFullData]:
        """Returns the object with the given name, if it exists"""
        for obj in self.show_events.buffer():
            if obj.name == name:
                return obj
        return None

    async def export(self, name: str) -> bytes:
        """Export the given previously-shown object to a single GLB file, building it if necessary."""
        start = time.time()

        # Check that the object to build exists and grab it if it does
        event = self._shown_object(name)
        if not event:
            raise web.HTTPNotFound(text=f'No object named {name} was previously shown')

        # Use the lock to ensure that we don't build the object twice
        async with self.object_events_lock:
            # If there are no object events for this name, we need to build the object
            if name not in self.object_events:
                # Prepare the pubsub for the object
                publish_to = BufferedPubSub[bytes]()
                self.object_events[name] = publish_to

                def _build_object():
                    # Build and publish the object (once)
                    gltf = tessellate(event.obj, tolerance=event.kwargs.get('tolerance', 0.1),
                                      angular_tolerance=event.kwargs.get('angular_tolerance', 0.1),
                                      faces=event.kwargs.get('faces', True),
                                      edges=event.kwargs.get('edges', True),
                                      vertices=event.kwargs.get('vertices', True))
                    glb_list_of_bytes = gltf.save_to_bytes()
                    publish_to.publish_nowait(b''.join(glb_list_of_bytes))
                    logger.info('export(%s) took %.3f seconds, %d parts', name, time.time() - start,
                                len(gltf.meshes[0].primitives))

                # await asyncio.get_running_loop().run_in_executor(None, _build_object)
                # The previous line has problems with auto-closed loop on script exit
                # and is cancellable, so instead run blocking code in async context :(
                logger.debug('Building object %s... %s', name, event.obj)
                _build_object()

        # In either case return the elements of a subscription to the async generator
        subscription = self.object_events[name].subscribe()
        try:
            return await anext(subscription)
        finally:
            await subscription.aclose()

    def export_all(self, folder: str) -> None:
        """Export all previously-shown objects to GLB files in the given folder"""
        import asyncio

        async def _export_all():
            os.makedirs(folder, exist_ok=True)
            for name in self.shown_object_names():
                with open(os.path.join(folder, f'{name}.glb'), 'wb') as f:
                    f.write(await self.export(name))

        asyncio.run(_export_all())
