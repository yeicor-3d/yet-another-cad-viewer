import asyncio
import logging
import os

from OCP.TopoDS import TopoDS_Shape
from build123d import *
from build123d import Shape


def build_logo() -> TopoDS_Shape:
    """Builds the CAD part of the logo"""
    with BuildPart(Plane.XY.offset(50)) as logo_obj:
        Box(22, 40, 30)
        fillet(edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 10)
        offset(solid(), 2, openings=faces().group_by(Axis.Z)[0] + faces().filter_by(Plane.XZ))
        text_at_plane = Plane.YZ
        text_at_plane.origin = faces().group_by(Axis.X)[-1].face().center()
        with BuildSketch(text_at_plane.location):
            Text('Yet Another\nCAD Viewer', 7, font_path='/usr/share/fonts/TTF/OpenSans-Regular.ttf')
        extrude(amount=1)

    return logo_obj.part.wrapped


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Start an offline "server" to merge the CAD part of the logo with the animated GLTF part of the logo
    os.environ['YACV_DISABLE_SERVER'] = '1'
    from __init__ import show_object, server
    ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets'))

    # Add the CAD part of the logo to the server
    obj = build_logo()
    Shape(obj).export_stl(os.path.join(ASSETS_DIR, 'logo.stl'))
    show_object(obj, 'logo')

    # Save the complete logo to a single GLB file
    with open(os.path.join(ASSETS_DIR, 'logo.glb'), 'wb') as f:
        async def writer():
            f.write(await server.export('logo'))

        asyncio.run(writer())

    print('Logo saved to', os.path.join(ASSETS_DIR, 'logo.glb'))
