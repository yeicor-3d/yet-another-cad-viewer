import os

from build123d import *  # Also works with cadquery objects!

# Optional: enable logging to see what's happening
import logging
logging.basicConfig(level=logging.DEBUG)

from yacv_server import show_object, export_all  # Check out all show_* methods for more features!

# %%

# Create a simple object
with BuildPart() as obj:
    Box(10, 10, 5)
    Cylinder(4, 5, mode=Mode.SUBTRACT)

# Show it in the frontend
show_object(obj, 'object')

# %%

# If running on CI, export the object to a .glb file compatible with the frontend
if 'CI' in os.environ:
    export_all('export')
