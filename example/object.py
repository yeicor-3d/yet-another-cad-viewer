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

# Show it in the frontend with hot-reloading (texture and other keyword arguments are optional)
texture = (  # MIT License Framework7 Line Icons: https://www.svgrepo.com/svg/437552/checkmark-seal
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAASAQAAAAB+tbP6AAAAQ0lEQVQI12P4b3+A4Z/8AYYHBw8w"
    "HHxwgOH8HyD+AsRPDjDMP+fAYD+fgcESiGfYOTCcqTnAcK4GogakFqQHpBdoBgAbGiPSbdzkhgAAAABJRU5ErkJggg==")
show(example, example_hl, texture=texture)

# %%

# If running on CI, export the objects to .glb files for a static deployment
if 'CI' in os.environ:
    export_all('export')
