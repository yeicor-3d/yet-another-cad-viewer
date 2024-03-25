import os

from yacv_server.cad import image_to_gltf
from yacv_server.yacv import YACV

yacv = YACV()
"""The server instance. This is the main entry point to serve CAD objects and other data to the frontend."""

if 'YACV_DISABLE_SERVER' not in os.environ:
    # Start a new server ASAP to let the polling client connect while still building CAD objects
    # This is a bit of a hack, but it is seamless to the user. This behavior can be disabled by setting
    # the environment variable YACV_DISABLE_SERVER to a non-empty value
    yacv.start()

# Expose some nice aliases using the default server instance
show = yacv.show
show_all = yacv.show_cad_all
image_to_gltf = image_to_gltf
export_all = yacv.export_all
remove = yacv.remove
clear = yacv.clear
