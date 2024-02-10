import asyncio
import logging
import os

from OCP.TopoDS import TopoDS_Shape
from build123d import *


def build_logo() -> TopoDS_Shape:
    """Builds the CAD part of the logo"""
    with BuildPart() as logo_obj:
        Box(1, 2, 3)
    return logo_obj.part.wrapped


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Start an offline "server" to merge the CAD part of the logo with the animated GLTF part of the logo
    os.environ['YACV_DISABLE_SERVER'] = '1'
    from __init__ import show_object, server
    ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets'))

    # 1. Add the CAD part of the logo to the server
    obj = build_logo()
    show_object(obj, 'logo')

    # 2. Load the GLTF part of the logo
    with open(os.path.join(ASSETS_DIR, 'fox.glb'), 'rb') as f:
        gltf = f.read()
    show_object(gltf, 'fox.glb')

    # 3. Save the complete logo to a GLBS file
    with open(os.path.join(ASSETS_DIR, 'logo.glbs'), 'wb') as f:
        async def writer():
            async for chunk in server.export_all():
                f.write(chunk)

        asyncio.run(writer())

    print('Logo saved to', os.path.join(ASSETS_DIR, 'logo.glbs'))
