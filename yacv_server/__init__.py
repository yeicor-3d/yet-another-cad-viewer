import os
import time

from OCP.TopoDS import TopoDS_Shape

from server import Server

server = Server()

if 'YACV_DISABLE_SERVER' not in os.environ:
    # Start a new server ASAP to let the polling client connect while still building CAD objects
    # This is a bit of a hack, but it is seamless to the user. This behavior can be disabled by setting
    # the environment variable YACV_DISABLE_SERVER to a non-empty value
    server.start()


def show_object(obj: TopoDS_Shape):
    """Show a CAD object in the default server"""
    server.show_object(obj)


if __name__ == '__main__':
    # Publish the logo to the server
    from logo.logo import build_logo

    assert server is not None
    server.show_object(build_logo())

    time.sleep(60)
