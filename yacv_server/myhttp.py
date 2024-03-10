import io
import os
import threading
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler

from iterators import TimeoutIterator

from yacv_server.mylogger import logger

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


class HTTPHandler(SimpleHTTPRequestHandler):
    yacv: 'yacv.YACV'
    frontend_lock: threading.Lock  # To avoid exiting too early while frontend makes requests
    at_least_one_client: threading.Event

    def __init__(self, *args, yacv: 'yacv.YACV', **kwargs):
        self.yacv = yacv
        self.frontend_lock = threading.Lock()
        self.at_least_one_client = threading.Event()
        super().__init__(*args, **kwargs, directory=FRONTEND_BASE_PATH)

    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    def end_headers(self):
        # Add CORS headers to the response
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        super().end_headers()

    def translate_path(self, path: str) -> str:
        """Translate a path to the local filesystem, adds some basic security checks"""
        path = super().translate_path(path)
        path = os.path.realpath(path)  # Avoid symlink hacks
        if self.directory:  # Ensure proper subdirectory
            base = os.path.abspath(self.directory)
            if not os.path.abspath(path).startswith(base):
                self.send_error(HTTPStatus.FORBIDDEN, "Path is not in the frontend directory")
                return ''
        return path

    def send_head(self):
        path_parts = self.path.split('?', 1)
        if len(path_parts) == 1:
            path_parts.append('')
        [path, query_str] = path_parts
        query = urllib.parse.parse_qs(query_str)
        if path == UPDATES_API_PATH or path == '/' and query.get('api_updates') is not None:
            return self._api_updates()
        elif path.startswith(OBJECTS_API_PATH) or path == '/' and query.get('api_object') is not None:
            if path.startswith(OBJECTS_API_PATH):
                obj_name = self.path[len(OBJECTS_API_PATH) + 1:]
            else:
                obj_name = query.get('api_object').pop()
            return self._api_object(obj_name)
        elif path.endswith('/'):  # Frontend index.html
            self.path += 'index.html'
            return super().send_head()
        else:  # Normal frontend file
            return super().send_head()

    def _api_updates(self):
        """Handles a publish-only websocket connection that send show_object events along with their hashes and URLs"""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        # Chunked transfer encoding!
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.at_least_one_client.set()
        logger.debug('Updates client connected')

        def write_chunk(_chunk_data: str):
            self.wfile.write(hex(len(_chunk_data))[2:].encode('utf-8'))
            self.wfile.write(b'\r\n')
            self.wfile.write(_chunk_data.encode('utf-8'))
            self.wfile.write(b'\r\n')
            self.wfile.flush()

        write_chunk('retry: 100\n\n')

        # Send buffered events first, while keeping a lock
        with self.frontend_lock:
            for data in self.yacv.show_events.buffer():
                logger.debug('Sending info about %s: %s', data.name, data)
                # noinspection PyUnresolvedReferences
                to_send = data.to_json()
                write_chunk(f'data: {to_send}\n\n')

        # Send future events over the same connection
        # Also send keep-alive to know if the client is still connected
        subscription = self.yacv.show_events.subscribe(include_buffered=False)
        it = TimeoutIterator(subscription, sentinel=None, reset_on_next=True, timeout=5.0)  # Keep-alive interval
        try:
            for data in it:
                if data is None:
                    write_chunk(':keep-alive\n\n')
                else:
                    logger.debug('Sending info about %s: %s', data.name, data)
                    # noinspection PyUnresolvedReferences
                    to_send = data.to_json()
                    write_chunk(f'data: {to_send}\n\n')
        except BrokenPipeError:  # Client disconnected normally
            pass
        finally:
            logger.debug('Updates client disconnected')
            try:
                it.interrupt()
                next(it)  # Make sure the iterator is interrupted before trying to close the subscription
                subscription.close()
            except BaseException as e:
                logger.debug('Ignoring error while closing subscription: %s', e)

    def _api_object(self, obj_name: str):
        """Returns the object file with the matching name, building it if necessary."""
        with self.frontend_lock:
            # Export the object (or fail if not found)
            exported_glb = self.yacv.export(obj_name)
            if exported_glb is None:
                self.send_error(HTTPStatus.NOT_FOUND, f'Object {obj_name} not found')
                return io.BytesIO()

            # Wrap the GLB in a response and return it
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'model/gltf-binary')
            self.send_header('Content-Length', str(len(exported_glb)))
            self.send_header('Content-Disposition', f'attachment; filename="{obj_name}.glb"')
            self.end_headers()
            self.wfile.write(exported_glb)
