import asyncio
import atexit
import os
import signal
from threading import Thread
from typing import Optional

from OCP.TopoDS import TopoDS_Shape
from aiohttp import web

FRONTEND_BASE_PATH = os.getenv('FRONTEND_BASE_PATH', '../dist')


# noinspection PyUnusedLocal
async def _index_handler(request: web.Request) -> web.Response:
    return web.HTTPTemporaryRedirect(location='index.html')


class Server:
    app = web.Application()
    runner: web.AppRunner
    thread: Optional[Thread] = None

    def __init__(self, *args, **kwargs):
        # --- Routes ---
        # - API
        # self.app.router.add_route({'POST','GET'}, '/api/{collection}', api_handler)
        # - Static files from the frontend
        self.app.router.add_get('/{path:(.*/|)}', _index_handler)  # Any folder -> index.html
        self.app.router.add_static('/', path=FRONTEND_BASE_PATH, name='static_frontend')
        # --- Misc ---
        self.runner = web.AppRunner(self.app)

    def start(self):
        """Starts the web server in the background"""
        assert self.thread is None, "Server already started"
        self.thread = Thread(target=self.run_server, name='yacv_server', daemon=True)
        signal.signal(signal.SIGINT | signal.SIGTERM, self.stop)
        atexit.register(self.stop)
        self.thread.start()

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Stops the web server"""
        print('Stopping server...')
        if self.thread is None:
            print('Cannot stop server because it is not running')
            return
        asyncio.run(self.runner.shutdown())
        asyncio.run(self.app.cleanup())
        self.thread = None  # FIXME: Not properly cleaned up (join blocks forever)
        print('Cleanup done')

    def run_server(self):
        """Runs the web server"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.runner.setup())
        site = web.TCPSite(self.runner, os.getenv('YACV_HOST', 'localhost'), int(os.getenv('YACV_PORT', 32323)))
        loop.run_until_complete(site.start())
        loop.run_forever()

    def show_object(self, obj: TopoDS_Shape):
        pass


def get_app() -> web.Application:
    """Required by aiohttp-devtools"""
    return Server().app
