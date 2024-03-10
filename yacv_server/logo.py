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
                Text('Yet Another\nCAD Viewer', 7, font_path='/usr/share/fonts/TTF/OpenSans-Regular.ttf')
            extrude(amount=1)

    logo_img_location = logo_obj.faces().group_by(Axis.X)[0].face().center_location  # Avoid overlapping:
    logo_img_location.position = Vector(logo_img_location.position.X - 4e-2, logo_img_location.position.Y,
                                        logo_img_location.position.Z)
    logo_img_path = os.path.join(ASSETS_DIR, 'img.jpg')

    fox_glb_bytes = open(os.path.join(ASSETS_DIR, 'fox.glb'), 'rb').read()

    return {'fox': fox_glb_bytes, 'logo': logo_obj, 'location': logo_img_location, 'img_path': logo_img_path}


def show_logo(parts: Dict[str, Union[Part, Location, str]]) -> None:
    """Shows the prebuilt logo parts"""
    from yacv_server import show_image, show_object
    for name, part in parts.items():
        if isinstance(part, str):
            show_image(source=part, center=parts['location'], height=18, auto_clear=False)
        else:
            show_object(part, name, auto_clear=False)


if __name__ == "__main__":
    from yacv_server import export_all, remove
    import logging

    logging.basicConfig(level=logging.DEBUG)

    testing_server = bool(os.getenv('TESTING_SERVER', 'False'))

    if not testing_server:
        # Start an offline server to export the CAD part of the logo in a way compatible with the frontend
        # If this is not set, the server will auto-start on import and show_* calls will provide live updates
        os.environ['YACV_DISABLE_SERVER'] = 'True'

        # Build the CAD part of the logo
    logo = build_logo()

    # Add the CAD part of the logo to the server
    show_logo(logo)

    if testing_server:
        remove('location')  # Test removing a part
    else:
        # Save the complete logo to multiple GLB files
        export_all(os.path.join(ASSETS_DIR, 'logo_build'))
        print('Logo saved!')
