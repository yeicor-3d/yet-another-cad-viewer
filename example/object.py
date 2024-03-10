# Optional: enable logging to see what's happening
import logging
import os

from build123d import *  # Also works with cadquery objects!

logging.basicConfig(level=logging.DEBUG)

from yacv_server import show, export_all  # Check out other exported methods for more features!

# %%

# Create a simple object
with BuildPart() as obj:
    Box(10, 10, 5)
    Cylinder(4, 5, mode=Mode.SUBTRACT)

# Show it in the frontend with hot-reloading
show(obj)

# %%

# If running on CI, export the objects to .glb files for a static deployment
if 'CI' in os.environ:
    export_all('export')
