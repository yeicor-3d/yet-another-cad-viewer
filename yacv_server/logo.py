import os
from typing import Union, Dict

from build123d import *

ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.path.dirname(__file__), '..', 'assets'))


def build_logo(text: bool = True) -> Dict[str, Union[Part, Location, str]]:
    """Builds the CAD part of the logo"""
    with BuildPart(Plane.XY.offset(50)) as logo_obj:
        Box(22, 40, 30)
        fillet(edges().filter_by(Axis.Y).group_by(Axis.Z)[-1], 10)
        offset(solid(), 2, openings=faces().group_by(Axis.Z)[0] + faces().filter_by(Plane.XZ))
        if text:
            text_at_plane = Plane.YZ
            text_at_plane.origin = faces().group_by(Axis.X)[-1].face().center()
            with BuildSketch(text_at_plane.location):
                Text('Yet Another\nCAD Viewer', 6, font_path='/usr/share/fonts/TTF/Hack-Regular.ttf')
            extrude(amount=1)

    # Highlight text edges with a custom color
    to_highlight = logo_obj.edges().group_by(Axis.X)[-1]
    logo_obj_hl = Compound(to_highlight).translate((1e-3, 0, 0))  # To avoid z-fighting
    logo_obj_hl.color = (0, 0.3, 0.3, 1)

    # Add a logo image to the CAD part
    logo_img_location = logo_obj.faces().group_by(Axis.X)[0].face().center_location
    logo_img_location *= Location((0, 0, 4e-2), (0, 0, 90))  # Avoid overlapping and adjust placement
    logo_img_path = os.path.join(ASSETS_DIR, 'img.jpg')
    img_glb_bytes, img_name = image_to_gltf(logo_img_path, logo_img_location, height=18)

    # Add an animated fox to the CAD part
    fox_glb_bytes = open(os.path.join(ASSETS_DIR, 'fox.glb'), 'rb').read()

    return {'fox': fox_glb_bytes, 'logo': logo_obj, 'logo_hl': logo_obj_hl, 'location': logo_img_location, img_name: img_glb_bytes}


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)

    testing_server = os.getenv('TESTING_SERVER') is not None

    if not testing_server:
        # Start an offline server to export the CAD part of the logo in a way compatible with the frontend
        # If this is not set, the server will auto-start on import and show_* calls will provide live updates
        os.environ['YACV_DISABLE_SERVER'] = 'True'

    from yacv_server import export_all, show, image_to_gltf

    # Build the CAD part of the logo
    logo = build_logo()

    # Add the CAD part of the logo to the server
    show(*[obj for obj in logo.values()], names=[name for name in logo.keys()])

    if testing_server:
        # remove('location')  # Test removing a part
        pass
    else:
        # Save the complete logo to multiple GLB files
        export_all(os.path.join(ASSETS_DIR, 'logo_build'))
        print('Logo saved!')
