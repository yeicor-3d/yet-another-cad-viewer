import asyncio
import atexit
import os
import signal
import sys
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
    do_shutdown = asyncio.Event()

    def __init__(self, *args, **kwargs):
        # --- Routes ---
        # - API
        # self.app.router.add_route({'POST','GET'}, '/api/{collection}', api_handler)
        # - Static files from the frontend
        self.app.router.add_get('/{path:(.*/|)}', _index_handler)  # Any folder -> index.html
        self.app.router.add_static('/', path=FRONTEND_BASE_PATH, name='static_frontend')
        # --- Misc ---
        self.loop = asyncio.new_event_loop()

    def start(self):
        """Starts the web server in the background"""
        assert self.thread is None, "Server already started"
        # Start the server in a separate daemon thread
        self.thread = Thread(target=self.run_server, name='yacv_server', daemon=True)
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

    def run_server(self):
        """Runs the web server"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run_server_async())
        self.loop.stop()
        self.loop.close()

    async def run_server_async(self):
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

    def show_object(self, obj: TopoDS_Shape):
        pass


def get_app() -> web.Application:
    """Required by aiohttp-devtools"""
    return Server().app
