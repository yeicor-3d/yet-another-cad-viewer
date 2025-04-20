import io
import os
import urllib.parse
from http import HTTPStatus, HTTPMethod
from http.server import SimpleHTTPRequestHandler

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

    def __init__(self, *args, yacv: 'yacv.YACV', **kwargs):
        self.yacv = yacv
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
        if not self.requestline.startswith(HTTPMethod.HEAD):
            # Chunked transfer encoding!
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", "0")
        self.end_headers()

        if self.requestline.startswith(HTTPMethod.HEAD):
            return

        # Keep a shared read lock to know if any frontend is still working before shutting down
        with self.yacv.frontend_lock.r_locked():

            # Avoid accepting new connections while shutting down
            if self.yacv.shutting_down.is_set() and self.yacv.at_least_one_client.is_set():
                self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, 'Server is shutting down')
                return
            self.yacv.at_least_one_client.set()
            logger.debug('Updates client connected')

            def write_chunk(_chunk_data: str):
                self.wfile.write(hex(len(_chunk_data))[2:].encode('utf-8'))
                self.wfile.write(b'\r\n')
                self.wfile.write(_chunk_data.encode('utf-8'))
                self.wfile.write(b'\r\n')
                self.wfile.flush()

            write_chunk('retry: 100\n\n')

            subscription = self.yacv.show_events.subscribe(yield_timeout=1.0)  # Keep-alive interval
            try:
                for data in subscription:
                    if data is None:
                        write_chunk(':keep-alive\n\n')
                    else:
                        logger.debug('Sending info about %s: %s', data.name, data)
                        # noinspection PyUnresolvedReferences
                        to_send = data.to_json()
                        write_chunk(f'data: {to_send}\n\n')
            except (BrokenPipeError, ConnectionResetError):  # Client disconnected normally
                pass
            finally:
                subscription.close()

        logger.debug('Updates client disconnected')

    def _api_object(self, obj_name: str):
        """Returns the object file with the matching name, building it if necessary."""
        # Export the object (or fail if not found)
        _export = self.yacv.export(obj_name)
        if _export is None:
            self.send_error(HTTPStatus.NOT_FOUND, f'Object {obj_name} not found')
            return io.BytesIO()

        exported_glb, _hash = _export

        # Wrap the GLB in a response and return it
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'model/gltf-binary')
        self.send_header('Content-Length', str(len(exported_glb)))
        self.send_header('Content-Disposition', f'attachment; filename="{obj_name}.glb"')
        self.send_header('E-Tag', f'"{_hash}"')
        self.end_headers()
        self.wfile.write(exported_glb)
        return None
