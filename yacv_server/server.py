import asyncio
import atexit
import hashlib
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from threading import Thread
from typing import Optional, Dict, Union, AsyncGenerator, List

import tqdm.asyncio
from OCP.TopoDS import TopoDS_Shape
from aiohttp import web
from dataclasses_json import dataclass_json, config
from tqdm.contrib.logging import logging_redirect_tqdm

from glbs import glb_sequence_to_glbs
from mylogger import logger
from pubsub import BufferedPubSub
from tessellate import _hashcode, tessellate_count, tessellate

FRONTEND_BASE_PATH = os.getenv('FRONTEND_BASE_PATH', '../dist')
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
    obj: Optional[TopoDS_Shape] = field(default=None, metadata=config(exclude=lambda obj: True))
    """The OCCT object, if any (not serialized)"""


# noinspection PyUnusedLocal
async def _index_handler(request: web.Request) -> web.Response:
    return web.HTTPTemporaryRedirect(location='index.html')


class Server:
    app = web.Application()
    runner: web.AppRunner
    thread: Optional[Thread] = None
    do_shutdown = asyncio.Event()
    show_events = BufferedPubSub[UpdatesApiData]()
    object_events: Dict[str, BufferedPubSub[bytes]] = {}
    object_events_lock = asyncio.Lock()

    def __init__(self, *args, **kwargs):
        # --- Routes ---
        # - APIs
        self.app.router.add_route('GET', f'{UPDATES_API_PATH}', self._api_updates)
        self.app.router.add_route('GET', f'{OBJECTS_API_PATH}/{{name}}', self._api_object)
        # - Static files from the frontend
        self.app.router.add_get('/{path:(.*/|)}', _index_handler)  # Any folder -> index.html
        self.app.router.add_static('/', path=FRONTEND_BASE_PATH, name='static_frontend')
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

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Stops the web server"""
        if self.thread is None:
            print('Cannot stop server because it is not running')
            return
        # FIXME: Wait for at least one client to confirm ready before stopping in case we are too fast?
        self.loop.call_soon_threadsafe(lambda *a: self.do_shutdown.set())
        self.thread.join(timeout=12)
        self.thread = None
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
        # print(f'Server started at {site.name}')
        # Wait for a signal to stop the server while running
        await self.do_shutdown.wait()
        # print('Shutting down server...')
        await runner.cleanup()

    async def _api_updates(self, request: web.Request) -> web.WebSocketResponse:
        """Handles a publish-only websocket connection that send show_object events along with their hashes and URLs"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async def _send_api_updates():
            subscription = self.show_events.subscribe()
            try:
                async for data in subscription:
                    # noinspection PyUnresolvedReferences
                    await ws.send_str(data.to_json())
            finally:
                await subscription.aclose()

        # Start sending updates to the client automatically
        send_task = asyncio.create_task(_send_api_updates())
        try:
            logger.debug('Client connected: %s', request.remote)
            # Wait for the client to close the connection (or send a message)
            await ws.receive()
        finally:
            # Make sure to stop sending updates to the client and close the connection
            send_task.cancel()
            await ws.close()
            logger.debug('Client disconnected: %s', request.remote)

        return ws

    obj_counter = 0

    def _show_common(self, name: Optional[str], hash: str, start: float, obj: Optional[TopoDS_Shape] = None):
        name = name or f'object_{self.obj_counter}'
        self.obj_counter += 1
        precomputed_info = UpdatesApiData(name=name, hash=hash, obj=obj)
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
        """Publishes any single-file GLTF object to the server (GLB format recommended)."""
        start = time.time()
        # Precompute the info and send it to the client as if it was a CAD object
        precomputed_info = self._show_common(name, hashlib.md5(gltf).hexdigest(), start)
        # Also pre-populate the GLTF data for the object API
        publish_to = BufferedPubSub[bytes]()
        publish_to.publish_nowait(gltf)
        publish_to.publish_nowait(b'')  # Signal the end of the stream
        self.object_events[precomputed_info.name] = publish_to

    def show_cad(self, obj: Union[TopoDS_Shape, any], name: Optional[str] = None, **kwargs):
        """Publishes a CAD object to the server"""
        start = time.time()
        # Try to grab a shape if a different type of object was passed
        if not isinstance(obj, TopoDS_Shape):
            # Build123D
            if 'part' in dir(obj):
                obj = obj.part
            if 'sketch' in dir(obj):
                obj = obj.sketch
            if 'line' in dir(obj):
                obj = obj.line
            # Build123D & CadQuery
            while 'wrapped' in dir(obj) and not isinstance(obj, TopoDS_Shape):
                obj = obj.wrapped
            if not isinstance(obj, TopoDS_Shape):
                raise ValueError(f'Cannot show object of type {type(obj)} (submit issue?)')

        self._show_common(name, _hashcode(obj), start, obj)

    async def _api_object(self, request: web.Request) -> web.StreamResponse:
        """Returns the object file with the matching name, building it if necessary."""

        # Start exporting the object (or fail if not found)
        export_data = self._export(request.match_info['name'])
        response = web.StreamResponse()
        try:
            # First exported element is the object itself, grab it to collect data
            export_obj = await anext(export_data)

            # Create a new stream response with custom content type and headers
            response.content_type = 'model/gltf-binary-sequence'
            response.headers['Content-Disposition'] = f'attachment; filename="{request.match_info["name"]}.glbs"'
            total_parts = 1 if export_obj is None else tessellate_count(export_obj)
            response.headers['X-Object-Parts'] = str(total_parts)
            await response.prepare(request)

            # Convert the GLB sequence to a GLBS sequence and write it to the response
            with logging_redirect_tqdm(tqdm_class=tqdm.asyncio.tqdm):
                if logger.isEnabledFor(logging.INFO):
                    # noinspection PyTypeChecker
                    export_data = tqdm.asyncio.tqdm(export_data, total=total_parts)
                async for chunk in glb_sequence_to_glbs(export_data, total_parts):
                    await response.write(chunk)
        finally:
            # Close the export data subscription
            await export_data.aclose()
            # Close the response (if not an error)
            if response.prepared:
                await response.write_eof()
        return response

    async def _export(self, name: str) -> AsyncGenerator[Union[TopoDS_Shape, bytes], None]:
        """Export the given previously-shown object to a sequence of GLB files, building it if necessary."""
        start = time.time()
        # Check that the object to build exists and grab it if it does
        found = False
        obj: Optional[TopoDS_Shape] = None
        subscription = self.show_events.subscribe(include_future=False)
        try:
            async for data in subscription:
                if data.name == name:
                    obj = data.obj
                    found = True  # Required because obj could be None
                    break
        finally:
            await subscription.aclose()
        if not found:
            raise web.HTTPNotFound(text=f'No object named {name} was previously shown')

        # First published element is the TopoDS_Shape, which is None for glTF objects
        yield obj

        # Use the lock to ensure that we don't build the object twice
        async with self.object_events_lock:
            # If there are no object events for this name, we need to build the object
            if name not in self.object_events:
                # Prepare the pubsub for the object
                publish_to = BufferedPubSub[bytes]()
                self.object_events[name] = publish_to

                def _build_object():
                    # Build the object
                    part_count = 0
                    for tessellation_update in tessellate(obj):
                        # We publish the object parts as soon as we have a new tessellation
                        list_of_bytes = tessellation_update.gltf.save_to_bytes()
                        publish_to.publish_nowait(b''.join(list_of_bytes))
                        part_count += 1
                    publish_to.publish_nowait(b'')  # Signal the end of the stream
                    logger.info('export(%s) took %.3f seconds, %d parts', name, time.time() - start, part_count)

                # We should build it fully even if we are cancelled, so we use a separate task
                # Furthermore, building is CPU-bound, so we use the default executor
                asyncio.get_running_loop().run_in_executor(None, _build_object)

        # In either case return the elements of a subscription to the async generator
        subscription = self.object_events[name].subscribe()
        try:
            async for chunk in subscription:
                if chunk == b'':
                    break
                yield chunk
        finally:
            await subscription.aclose()

    async def export_all(self) -> AsyncGenerator[bytes, None]:
        """Export all previously shown objects to a single GLBS file, returned as an async generator.

        This is useful for fully-static deployments where the frontend handles everything."""
        # Check that the object to build exists and grab it if it does
        all_object_names: List[str] = []
        total_export_size = 0
        subscription = self.show_events.subscribe(include_future=False)
        try:
            async for data in subscription:
                all_object_names.append(data.name)
                if data.obj is not None:
                    total_export_size += tessellate_count(data.obj)
                else:
                    total_export_size += 1
        finally:
            await subscription.aclose()

        # Create a generator that merges the export of all objects
        async def _merge_exports() -> AsyncGenerator[bytes, None]:
            for i, name in enumerate(all_object_names):
                obj_subscription = self._export(name)
                try:
                    obj = await anext(obj_subscription)
                    glb_parts = obj_subscription
                    if logger.isEnabledFor(logging.INFO):
                        total = tessellate_count(obj) if obj is not None else 1
                        # noinspection PyTypeChecker
                        glb_parts = tqdm.asyncio.tqdm(obj_subscription, total=total)
                    async for glb_part in glb_parts:
                        yield glb_part
                finally:
                    await obj_subscription.aclose()

        # Need to have a single subscription to all objects to write a valid GLBS file
        subscription = _merge_exports()
        try:
            with logging_redirect_tqdm(tqdm_class=tqdm.asyncio.tqdm):
                glbs_parts = subscription
                if logger.isEnabledFor(logging.INFO):
                    # noinspection PyTypeChecker
                    glbs_parts = tqdm.asyncio.tqdm(glbs_parts, total=total_export_size, position=0)
                glbs_parts = glb_sequence_to_glbs(glbs_parts, total_export_size)
                async for glbs_part in glbs_parts:
                    yield glbs_part
        finally:
            await subscription.aclose()
