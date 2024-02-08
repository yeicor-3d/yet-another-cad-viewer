import logging
import os
import time

from aiohttp import web

from server import Server

server = Server()
"""The server instance. This is the main entry point to serve CAD objects and other data to the frontend."""

if 'YACV_DISABLE_SERVER' not in os.environ:
    # Start a new server ASAP to let the polling client connect while still building CAD objects
    # This is a bit of a hack, but it is seamless to the user. This behavior can be disabled by setting
    # the environment variable YACV_DISABLE_SERVER to a non-empty value
    server.start()


def _get_app() -> web.Application:
    """Required by aiohttp-devtools"""
    logging.basicConfig(level=logging.DEBUG)
    from logo.logo import build_logo
    server.show_object(build_logo(), 'logo')
    return server.app


if __name__ == '__main__':
    # Publish the logo to the server (reusing code from the aiohttp-devtools)
    _get_app()
    # Keep the server running for testing
    time.sleep(60)
