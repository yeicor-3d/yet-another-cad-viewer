import os
import time

from OCP.TopoDS import TopoDS_Shape
from aiohttp import web

from server import Server

server = Server()

if 'YACV_DISABLE_SERVER' not in os.environ:
    # Start a new server ASAP to let the polling client connect while still building CAD objects
    # This is a bit of a hack, but it is seamless to the user. This behavior can be disabled by setting
    # the environment variable YACV_DISABLE_SERVER to a non-empty value
    server.start()


def get_app() -> web.Application:
    """Required by aiohttp-devtools"""
    from logo.logo import build_logo
    server.show_object(build_logo())
    return server.app


def show_object(obj: TopoDS_Shape):
    """Show a CAD object in the default server"""
    server.show_object(obj)


if __name__ == '__main__':
    # Publish the logo to the server (reusing code from the aiohttp-devtools)
    get_app()
    # Keep the server running for testing
    time.sleep(60)
