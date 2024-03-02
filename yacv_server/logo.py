import asyncio
import logging
import os

from build123d import *


def build_logo(text: bool = True) -> Part:
    """Builds the CAD part of the logo"""
    with BuildPart(Plane.XY.offset(50)) as logo_obj:
        Box(22, 40, 30)
        fillet(edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 10)
        offset(solid(), 2, openings=faces().group_by(Axis.Z)[0] + faces().filter_by(Plane.XZ))
        if text:
            text_at_plane = Plane.YZ
            text_at_plane.origin = faces().group_by(Axis.X)[-1].face().center()
            with BuildSketch(text_at_plane.location):
                Text('Yet Another\nCAD Viewer', 7, font_path='/usr/share/fonts/TTF/OpenSans-Regular.ttf')
            extrude(amount=1)

    return logo_obj.part


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Start an offline "server" to export the CAD part of the logo in a way compatible with the frontend
    os.environ['YACV_DISABLE_SERVER'] = '1'
    from yacv_server import show_object, server

    ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets'))

    # Add the CAD part of the logo to the server
    obj = build_logo()
    # DEBUG: Shape(obj).export_stl(os.path.join(ASSETS_DIR, 'logo.stl'))
    show_object(obj, 'logo')

    # Save the complete logo to a single GLB file
    with open(os.path.join(ASSETS_DIR, 'logo.glb'), 'wb') as f:
        async def writer():
            f.write(await server.export('logo'))


        asyncio.run(writer())

    print('Logo saved to', os.path.join(ASSETS_DIR, 'logo.glb'))
