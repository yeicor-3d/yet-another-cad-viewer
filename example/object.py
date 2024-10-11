# Optional: enable logging to see what's happening
import logging
import os

from build123d import *  # Also works with cadquery objects!
from build123d import Compound

logging.basicConfig(level=logging.DEBUG)

from yacv_server import show, export_all  # Check out other exported methods for more features!

# %%

# Create a simple object
with BuildPart() as example:
    Box(10, 10, 5)
    Cylinder(4, 5, mode=Mode.SUBTRACT)

# Custom colors (optional)
example.color = (0.1, 0.3, 0.1, 1)  # RGBA
to_highlight = example.edges().group_by(Axis.Z)[-1]
example_hl = Compound(to_highlight).translate((0, 0, 1e-3))  # To avoid z-fighting
example_hl.color = (1, 1, .0, 1)

# Show it in the frontend with hot-reloading
show(example, example_hl)

# %%

# If running on CI, export the objects to .glb files for a static deployment
if 'CI' in os.environ:
    export_all('export')
