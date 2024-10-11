import atexit
import copy
import inspect
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from threading import Thread
from typing import Optional, Dict, Union, Callable, List, Tuple

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
# noinspection PyProtectedMember
from build123d import Shape, Axis, Location, Vector
from dataclasses_json import dataclass_json

from yacv_server.cad import _hashcode, ColorTuple, get_color
from yacv_server.cad import get_shape, grab_all_cad, CADCoreLike, CADLike
from yacv_server.gltf import get_version
from yacv_server.myhttp import HTTPHandler
from yacv_server.mylogger import logger
from yacv_server.pubsub import BufferedPubSub
from yacv_server.rwlock import RWLock
from yacv_server.tessellate import tessellate


@dataclass_json
@dataclass
class UpdatesApiData:
    """Data sent to the client through the updates API"""
    name: str
    """Name of the object. Should be unique unless you want to overwrite the previous object"""
    hash: str
    """Hash of the object, to detect changes without rebuilding the object"""
    is_remove: Optional[bool]
    """Whether to remove the object from the scene. If None, this is a shutdown request"""


YACVSupported = Union[bytes, CADCoreLike]


class UpdatesApiFullData(UpdatesApiData):
    obj: YACVSupported
    """The OCCT object (not serialized)"""
    color: Optional[ColorTuple]
    """The color of the object, if any (not serialized)"""
    kwargs: Optional[Dict[str, any]]
    """The show_object options, if any (not serialized)"""

    def __init__(self, obj: YACVSupported, name: str, _hash: str, is_remove: Optional[bool] = False,
                 color: Optional[ColorTuple] = None,
                 kwargs: Optional[Dict[str, any]] = None):
        self.name = name
        self.hash = _hash
        self.is_remove = is_remove
        self.obj = obj
        self.color = color
        self.kwargs = kwargs

    def to_json(self) -> str:
        # noinspection PyUnresolvedReferences
        return super().to_json()


class YACV:
    """The main yacv_server class, which manages the web server and the CAD objects."""

    # Startup
    server_thread: Optional[Thread]
    """The main thread running the server (will spawn other threads for each request)"""
    server: Optional[ThreadingHTTPServer]
    """The server object"""
    startup_complete: threading.Event
    """Event to signal when the server has started"""

    # Running
    show_events: BufferedPubSub[UpdatesApiFullData]
    """PubSub for show events (objects to be shown in/removed from the scene)"""
    build_events: Dict[str, BufferedPubSub[bytes]]
    """PubSub for build events (objects that were built)"""
    build_events_lock: threading.Lock
    """Lock to ensure that objects are only built once"""

    # Shutdown
    at_least_one_client: threading.Event
    """Event to signal when at least one client has connected"""
    shutting_down: threading.Event
    """Event to signal when the server is shutting down"""
    frontend_lock: RWLock
    """Lock to ensure that the frontend has finished working before we shut down"""

    def __init__(self):
        self.server_thread = None
        self.server = None
        self.startup_complete = threading.Event()
        self.show_events = BufferedPubSub()
        self.build_events = {}
        self.build_events_lock = threading.Lock()
        self.at_least_one_client = threading.Event()
        self.shutting_down = threading.Event()
        self.frontend_lock = RWLock()
        logger.info('Using yacv-server v%s', get_version())

    def start(self):
        """Starts the web server in the background"""
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
            logger.error('Cannot stop server because it is not running')
            return

        # Inform the server that we are shutting down
        self.shutting_down.set()
        # noinspection PyTypeChecker
        self.show_events.publish(UpdatesApiFullData(name='__shutdown', _hash='', is_remove=None, obj=None))

        # If we were too fast, ensure that at least one client has connected
        graceful_secs_connect = float(os.getenv('YACV_GRACEFUL_SECS_CONNECT', 12.0))
        if graceful_secs_connect > 0:
            start = time.time()
            try:
                if not self.at_least_one_client.is_set():
                    logger.warning(
                        'Waiting for at least one frontend request before stopping server, cancel with CTRL+C...')
                while (not self.at_least_one_client.wait(graceful_secs_connect / 10) and
                       time.time() - start < graceful_secs_connect):
                    time.sleep(0.01)
            except KeyboardInterrupt:
                pass

        # Wait for the server to stop gracefully (all frontends to stop working)
        graceful_secs_request = float(os.getenv('YACV_GRACEFUL_SECS_WORK', 1000000))
        with self.frontend_lock.w_locked(timeout=graceful_secs_request):
            # Stop the server
            self.server.shutdown()

            # Wait for the server thread to stop
            self.server_thread.join(timeout=30)
            self.server_thread = None
            if len(args) >= 1 and args[0] in (signal.SIGINT, signal.SIGTERM):
                sys.exit(0)  # Exit with success

    def _run_server(self):
        """Runs the web server"""
        logger.info('Starting server...')
        self.server = ThreadingHTTPServer(
            (os.getenv('YACV_HOST', 'localhost'), int(os.getenv('YACV_PORT', 32323))),
            lambda a, b, c: HTTPHandler(a, b, c, yacv=self))
        # noinspection HttpUrlsUsage
        logger.info(f'Serving at http://{self.server.server_name}:{self.server.server_port}')
        self.startup_complete.set()
        self.server.serve_forever()

    def show(self, *objs: List[YACVSupported], names: Optional[Union[str, List[str]]] = None, **kwargs):
        # Prepare the arguments
        start = time.time()
        names = names or [_find_var_name(obj) for obj in objs]
        if isinstance(names, str):
            names = [names]
        assert len(names) == len(objs), 'Number of names must match the number of objects'

        # Handle auto clearing of previous objects
        if kwargs.get('auto_clear', True):
            self.clear(except_names=names)

        # Remove a previous object event with the same name
        for old_event in self.show_events.buffer():
            if old_event.name in names:
                self.show_events.delete(old_event)
                if old_event.name in self.build_events:
                    del self.build_events[old_event.name]

        # Publish the show event
        for obj, name in zip(objs, names):
            color = get_color(obj)
            if not isinstance(obj, bytes):
                obj = _preprocess_cad(obj, **kwargs)
            _hash = _hashcode(obj, color, **kwargs)
            event = UpdatesApiFullData(name=name, _hash=_hash, obj=obj, color=color, kwargs=kwargs or {})
            self.show_events.publish(event)

        logger.info('show %s took %.3f seconds', names, time.time() - start)

    def show_cad_all(self, **kwargs):
        """Publishes all CAD objects in the current scope to the server"""
        all_cad = list(grab_all_cad())  # List for reproducible iteration order
        self.show(*[cad for _, cad in all_cad], names=[name for name, _ in all_cad], **kwargs)

    def remove(self, name: str):
        """Removes a previously-shown object from the scene"""
        show_events = self._show_events(name)
        if len(show_events) > 0:
            # Ensure only the new remove event remains for this name
            for old_show_event in show_events:
                self.show_events.delete(old_show_event)

            # Delete any cached object builds
            with self.build_events_lock:
                if name in self.build_events:
                    del self.build_events[name]

            # Publish the remove event
            show_event = copy.copy(show_events[-1])
            show_event.is_remove = True
            self.show_events.publish(show_event)

    def clear(self, except_names: List[str] = None):
        """Clears all previously-shown objects from the scene"""
        if except_names is None:
            except_names = []
        for event in self.show_events.buffer():
            if event.name not in except_names:
                self.remove(event.name)

    def shown_object_names(self, apply_removes: bool = True) -> List[str]:
        """Returns the names of all objects that have been shown"""
        res = set()
        for obj in self.show_events.buffer():
            if not obj.is_remove or not apply_removes:
                res.add(obj.name)
            else:
                res.discard(obj.name)
        return list(res)

    def _show_events(self, name: str, apply_removes: bool = True) -> List[UpdatesApiFullData]:
        """Returns the show events with the given name"""
        res = []
        for event in self.show_events.buffer():
            if event.name == name:
                if not event.is_remove or not apply_removes:
                    res.append(event)
                else:
                    # Also remove the previous events
                    for old_event in res:
                        if old_event.name == event.name:
                            res.remove(old_event)
        return res

    def export(self, name: str) -> Optional[Tuple[bytes, str]]:
        """Export the given previously-shown object to a single GLB blob, building it if necessary."""
        start = time.time()

        # Check that the object to build exists and grab it if it does
        events = self._show_events(name)
        if len(events) == 0:
            logger.warning('Object %s not found', name)
            return None
        event = events[-1]

        # Use the lock to ensure that we don't build the object twice
        with self.build_events_lock:
            # If there are no object events for this name, we need to build the object
            if name not in self.build_events:
                logger.debug('Building object %s with hash %s', name, event.hash)

                # Prepare the pubsub for the object
                publish_to = BufferedPubSub[bytes]()
                self.build_events[name] = publish_to

                # Build and publish the object (once)
                if isinstance(event.obj, bytes):  # Already a GLTF
                    publish_to.publish(event.obj)
                else:  # CAD object to tessellate and convert to GLTF
                    gltf = tessellate(event.obj, tolerance=event.kwargs.get('tolerance', 0.1),
                                      angular_tolerance=event.kwargs.get('angular_tolerance', 0.1),
                                      faces=event.kwargs.get('faces', True),
                                      edges=event.kwargs.get('edges', True),
                                      vertices=event.kwargs.get('vertices', True),
                                      obj_color=event.color)
                    glb_list_of_bytes = gltf.save_to_bytes()
                    glb_bytes = b''.join(glb_list_of_bytes)
                    publish_to.publish(glb_bytes)
                    logger.info('export(%s) took %.3f seconds, %s', name, time.time() - start,
                                sizeof_fmt(len(glb_bytes)))

            # In either case return the elements of a subscription to the async generator
            subscription = self.build_events[name].subscribe()
            try:
                return next(subscription), event.hash
            finally:
                subscription.close()

    def export_all(self, folder: str,
                   export_filter: Callable[[str, Optional[CADCoreLike]], bool] = lambda name, obj: True):
        """Export all previously-shown objects to GLB files in the given folder"""
        os.makedirs(folder, exist_ok=True)
        for name in self.shown_object_names():
            if export_filter(name, self._show_events(name)[-1].obj):
                with open(os.path.join(folder, f'{name}.glb'), 'wb') as f:
                    f.write(self.export(name)[0])


# noinspection PyUnusedLocal
def _preprocess_cad(obj: CADLike, **kwargs) -> CADCoreLike:
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

    return obj


_find_var_name_count = 0


def _find_var_name(obj: any, avoid_levels: int = 2) -> str:
    """A hacky way to get a stable name for an object that may change over time"""
    global _find_var_name_count
    obj_shape = get_shape(obj, error=False) or obj
    for frame in inspect.stack()[avoid_levels:]:
        for key, value in frame.frame.f_locals.items():
            if get_shape(value, error=False) is obj_shape:
                return key
    _find_var_name_count += 1
    return 'unknown_var_' + str(_find_var_name_count)


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
