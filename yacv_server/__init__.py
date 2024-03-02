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

# Expose some nice aliases using the default server instance
show = server.show
show_object = show
show_all = server.show_cad_all


def _get_app() -> web.Application:
    """Required by aiohttp-devtools"""
    logging.basicConfig(level=logging.DEBUG)
    from logo import build_logo
    from build123d import Axis
    logo = build_logo(False)
    server.show_cad(logo, 'Logo')
    server.show_cad(logo.faces().group_by(Axis.X)[0].face().center_location, 'Location')
    return server.app


if __name__ == '__main__':
    # Publish the logo to the server (reusing code from the aiohttp-devtools)
    _get_app()
    # Keep the server running for testing
    time.sleep(60)
