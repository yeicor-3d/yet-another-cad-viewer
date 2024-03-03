import asyncio
import logging
import os
from typing import Tuple

from build123d import *

ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets'))


def build_logo(text: bool = True) -> Tuple[Part, Location, str]:
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

    logo_img_location = logo_obj.faces().group_by(Axis.X)[0].face().center_location  # Avoid overlapping:
    logo_img_location.position = Vector(logo_img_location.position.X - 4e-2, logo_img_location.position.Y,
                                        logo_img_location.position.Z)
    logo_img_path = os.path.join(ASSETS_DIR, 'img.jpg')
    return logo_obj.part, logo_img_location, logo_img_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Start an offline server to export the CAD part of the logo in a way compatible with the frontend
    # If this is not set, the server will auto-start on import and show_* calls will provide live updates
    os.environ['YACV_DISABLE_SERVER'] = '1'
    from yacv_server import show, show_image

    # Add the CAD part of the logo to the server
    logo, img_location, img_path = build_logo()
    show(logo, 'base')
    show(img_location, 'location')
    show_image(img_path, img_location, 20)


    async def exporter():
        # We need access to the actual server object for advanced features like exporting to file
        from yacv_server import server
        for name in server.shown_object_names():
            print(f'Exporting {name} to GLB...')
            with open(os.path.join(ASSETS_DIR, 'logo_build', f'{name}.glb'), 'wb') as f:
                f.write(await server.export(name))


    # Save the complete logo to multiple GLB files (async required)
    asyncio.run(exporter())

    print('Logo saved!')
