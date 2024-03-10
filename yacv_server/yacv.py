import atexit
import inspect
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Optional, Dict, Union, Callable

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
# noinspection PyProtectedMember
from build123d import Shape, Axis, Location, Vector
from dataclasses_json import dataclass_json

from myhttp import HTTPHandler
from yacv_server.cad import get_shape, grab_all_cad, image_to_gltf, CADLike
from yacv_server.mylogger import logger
from yacv_server.pubsub import BufferedPubSub
from yacv_server.tessellate import _hashcode, tessellate


@dataclass_json
@dataclass
class UpdatesApiData:
    """Data sent to the client through the updates API"""
    name: str
    """Name of the object. Should be unique unless you want to overwrite the previous object"""
    hash: str
    """Hash of the object, to detect changes without rebuilding the object"""
    is_remove: bool
    """Whether to remove the object from the scene"""


class UpdatesApiFullData(UpdatesApiData):
    obj: Optional[CADLike]
    """The OCCT object, if any (not serialized)"""
    kwargs: Optional[Dict[str, any]]
    """The show_object options, if any (not serialized)"""

    def __init__(self, name: str, _hash: str, is_remove: bool = False, obj: Optional[CADLike] = None,
                 kwargs: Optional[Dict[str, any]] = None):
        self.name = name
        self.hash = _hash
        self.is_remove = is_remove
        self.obj = obj
        self.kwargs = kwargs

    def to_json(self) -> str:
        # noinspection PyUnresolvedReferences
        return super().to_json()


class YACV:
    server_thread: Optional[Thread]
    server: Optional[ThreadingHTTPServer]
    startup_complete: threading.Event
    show_events: BufferedPubSub[UpdatesApiFullData]
    object_events: Dict[str, BufferedPubSub[bytes]]
    object_events_lock: threading.Lock

    def __init__(self):
        self.server_thread = None
        self.server = None
        self.startup_complete = threading.Event()
        self.at_least_one_client = threading.Event()
        self.show_events = BufferedPubSub()
        self.object_events = {}
        self.object_events_lock = threading.Lock()
        self.frontend_lock = threading.Lock()

    def start(self):
        """Starts the web server in the background"""
        print('yacv>start')
        assert self.server_thread is None, "Server currently running, cannot start another one"
        assert self.startup_complete.is_set() is False, "Server already started"
        # Start the server in a separate daemon thread
        self.server_thread = Thread(target=self._run_server, name='yacv_server', daemon=True)
        signal.signal(signal.SIGINT | signal.SIGTERM, self.stop)
        atexit.register(self.stop)
        self.server_thread.start()
        logger.info('Server started (requested)...')
        # Wait for the server to be ready before returning
        while not self.startup_complete.wait():
            time.sleep(0.01)
        logger.info('Server started (received)...')

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Stops the web server"""
        if self.server_thread is None:
            print('Cannot stop server because it is not running')
            return

        graceful_secs_connect = float(os.getenv('YACV_GRACEFUL_SECS_CONNECT', 12.0))
        graceful_secs_request = float(os.getenv('YACV_GRACEFUL_SECS_REQUEST', 5.0))
        # Make sure we can hold the lock for more than 100ms (to avoid exiting too early)
        logger.info('Stopping server (waiting for at least one frontend request first, cancel with CTRL+C)...')
        start = time.time()
        try:
            while not self.at_least_one_client.wait(
                    graceful_secs_connect / 10) and time.time() - start < graceful_secs_connect:
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass

        logger.info('Stopping server (waiting for no more frontend requests)...')
        start = time.time()
        try:
            while time.time() - start < graceful_secs_request:
                if self.frontend_lock.locked():
                    start = time.time()
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass

        # Stop the server in the background
        self.server.shutdown()
        logger.info('Stopping server (sent)...')

        # Wait for the server to stop gracefully
        self.server_thread.join(timeout=30)
        self.server_thread = None
        logger.info('Stopping server (confirmed)...')
        if len(args) >= 1 and args[0] in (signal.SIGINT, signal.SIGTERM):
            sys.exit(0)  # Exit with success

    def _run_server(self):
        """Runs the web server"""
        print('yacv>run_server', inspect.stack())
        logger.info('Starting server...')
        self.server = ThreadingHTTPServer(
            (os.getenv('YACV_HOST', 'localhost'), int(os.getenv('YACV_PORT', 32323))),
            lambda a, b, c: HTTPHandler(a, b, c, yacv=self))
        # noinspection HttpUrlsUsage
        logger.info(f'Serving at http://{self.server.server_name}:{self.server.server_port}')
        self.startup_complete.set()
        self.server.serve_forever()

    def _show_common(self, name: Optional[str], _hash: str, start: float, obj: Optional[CADLike] = None,
                     kwargs=None):
        if kwargs.get('auto_clear', True):
            self.clear()
        name = name or f'object_{len(self.show_events.buffer())}'
        # Remove a previous object with the same name
        for old_event in self.show_events.buffer():
            if old_event.name == name:
                self.show_events.delete(old_event)
                if name in self.object_events:
                    del self.object_events[name]
                break
        precomputed_info = UpdatesApiFullData(name=name, _hash=_hash, obj=obj, kwargs=kwargs or {})
        self.show_events.publish(precomputed_info)
        logger.info('show_object(%s, %s) took %.3f seconds', name, _hash, time.time() - start)
        return precomputed_info

    def show(self, any_object: Union[bytes, CADLike, any], name: Optional[str] = None, **kwargs):
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
        publish_to.publish(gltf)
        publish_to.publish(b'')  # Signal the end of the stream
        self.object_events[precomputed_info.name] = publish_to

    def show_image(self, source: str | bytes, center: any, width: Optional[float] = None,
                   height: Optional[float] = None, name: Optional[str] = None, save_mime: str = 'image/jpeg', **kwargs):
        """Publishes an image as a quad GLTF object, indicating the center location and pixels per millimeter."""
        # Convert the image to a GLTF CAD object
        gltf, name = image_to_gltf(source, center, width, height, name, save_mime)
        # Publish it like any other GLTF object
        self.show_gltf(gltf, name, **kwargs)

    def show_cad(self, obj: Union[CADLike, any], name: Optional[str] = None, **kwargs):
        """Publishes a CAD object to the server"""
        start = time.time()

        # Get the shape of a CAD-like object
        obj = get_shape(obj)

        # Convert Z-up (OCCT convention) to Y-up (GLTF convention)
        if isinstance(obj, TopoDS_Shape):
            obj = Shape(obj).rotate(Axis.X, -90).wrapped
        elif isinstance(obj, TopLoc_Location):
            tmp_location = Location(obj)
            tmp_location.position = Vector(tmp_location.position.X, tmp_location.position.Z,
                                           -tmp_location.position.Y)
            tmp_location.orientation = Vector(tmp_location.orientation.X - 90, tmp_location.orientation.Y,
                                              tmp_location.orientation.Z)
            obj = tmp_location.wrapped

        self._show_common(name, _hashcode(obj, **kwargs), start, obj, kwargs)

    def show_cad_all(self, **kwargs):
        """Publishes all CAD objects in the current scope to the server"""
        for name, obj in grab_all_cad():
            self.show_cad(obj, name, **kwargs)

    def remove(self, name: str):
        """Removes a previously-shown object from the scene"""
        shown_object = self._shown_object(name)
        if shown_object:
            shown_object.is_remove = True
            with self.object_events_lock:
                if name in self.object_events:
                    del self.object_events[name]
            self.show_events.publish(shown_object)

    def clear(self):
        """Clears all previously-shown objects from the scene"""
        for event in self.show_events.buffer():
            self.remove(event.name)

    def shown_object_names(self) -> list[str]:
        """Returns the names of all objects that have been shown"""
        return list([obj.name for obj in self.show_events.buffer()])

    def _shown_object(self, name: str) -> Optional[UpdatesApiFullData]:
        """Returns the object with the given name, if it exists"""
        for obj in self.show_events.buffer():
            if obj.name == name:
                return obj
        return None

    def export(self, name: str) -> Optional[bytes]:
        """Export the given previously-shown object to a single GLB file, building it if necessary."""
        start = time.time()

        # Check that the object to build exists and grab it if it does
        event = self._shown_object(name)
        if event is None:
            return None

        # Use the lock to ensure that we don't build the object twice
        with self.object_events_lock:
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
                    publish_to.publish(b''.join(glb_list_of_bytes))
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
                return next(subscription)
            finally:
                subscription.close()

    def export_all(self, folder: str,
                   export_filter: Callable[[str, Optional[CADLike]], bool] = lambda name, obj: True):
        """Export all previously-shown objects to GLB files in the given folder"""
        os.makedirs(folder, exist_ok=True)
        for name in self.shown_object_names():
            if export_filter(name, self._shown_object(name).obj):
                with open(os.path.join(folder, f'{name}.glb'), 'wb') as f:
                    f.write(self.export(name))
