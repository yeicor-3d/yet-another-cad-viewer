"""
Utilities to work with CAD objects
"""
import hashlib
from typing import Optional, Union, List, Tuple

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape

from yacv_server.gltf import GLTFMgr

CADCoreLike = Union[TopoDS_Shape, TopLoc_Location]  # Faces, Edges, Vertices and Locations for now
CADLike = Union[CADCoreLike, any]  # build123d and cadquery types


def get_shape(obj: CADLike, error: bool = True) -> Optional[CADCoreLike]:
    """ Get the shape of a CAD-like object """

    # Try to grab a shape if a different type of object was passed
    if isinstance(obj, TopoDS_Shape) or isinstance(obj, TopLoc_Location):
        return obj

    # Return locations (drawn as axes)
    if 'wrapped' in dir(obj) and isinstance(obj.wrapped, TopLoc_Location):
        return obj.wrapped

    # Build123D
    if 'part' in dir(obj):
        obj = obj.part
    if 'sketch' in dir(obj):
        obj = obj.sketch
    if 'line' in dir(obj):
        obj = obj.line

    # Build123D & CadQuery
    while 'wrapped' in dir(obj) and not isinstance(obj, TopoDS_Shape) and not isinstance(obj, TopLoc_Location):
        obj = obj.wrapped

    # Return shapes
    if isinstance(obj, TopoDS_Shape):
        return obj

    if error:
        raise ValueError(f'Cannot show object of type {type(obj)} (submit issue?)')
    else:
        return None


def grab_all_cad() -> List[Tuple[str, CADCoreLike]]:
    """ Grab all shapes by inspecting the stack """
    import inspect
    stack = inspect.stack()
    shapes = []
    for frame in stack:
        for key, value in frame.frame.f_locals.items():
            shape = get_shape(value, error=False)
            if shape:
                shapes.append((key, shape))
    return shapes


def image_to_gltf(source: str | bytes, center: any, width: Optional[float] = None, height: Optional[float] = None,
                  name: Optional[str] = None, save_mime: str = 'image/jpeg', power_of_two: bool = True) \
        -> Tuple[bytes, str]:
    """Convert an image to a GLTF CAD object."""
    from PIL import Image
    import io
    import os
    from build123d import Plane
    from build123d import Location
    from build123d import Vector

    # Handle arguments
    if name is None:
        if isinstance(source, str):
            name = os.path.basename(source)
        else:
            hasher = hashlib.md5()
            hasher.update(source)
            name = 'image_' + hasher.hexdigest()
    format: str
    if save_mime == 'image/jpeg':
        format = 'JPEG'
    elif save_mime == 'image/png':
        format = 'PNG'
    else:
        raise ValueError(f'Unsupported save MIME type (for GLTF files): {save_mime}')

    # Get the plane of the image
    center_loc = get_shape(center)
    if not isinstance(center_loc, TopLoc_Location):
        raise ValueError('Center location not valid')
    plane = Plane(Location(center_loc))

    # Load the image to a byte buffer
    img = Image.open(source)
    img_buf = io.BytesIO()

    # Use the original dimensions for scaling the model
    if width is None and height is None:
        raise ValueError('At least one of width or height must be specified')  # Fallback to pixels == mm?
    elif width is None:
        width = img.width / img.height * height
    elif height is None:
        height = height or img.height / img.width * width  # Apply default aspect ratio if unspecified

    # Resize the image to a power of two if requested (recommended for GLTF)
    if power_of_two:
        new_width = 2 ** (img.width - 1).bit_length()
        new_height = 2 ** (img.height - 1).bit_length()
        img = img.resize((new_width, new_height))

    # Save the image to a buffer
    img.save(img_buf, format=format)
    img_buf = img_buf.getvalue()

    # Convert coordinates system as a last step (gltf is Y-up instead of Z-up)
    def vert(v: Vector) -> Vector:
        return Vector(v.X, v.Z, -v.Y)

    # Build the gltf
    mgr = GLTFMgr(image=(img_buf, save_mime))
    mgr.add_face([
        vert(plane.origin - plane.x_dir * width / 2 + plane.y_dir * height / 2),
        vert(plane.origin + plane.x_dir * width / 2 + plane.y_dir * height / 2),
        vert(plane.origin + plane.x_dir * width / 2 - plane.y_dir * height / 2),
        vert(plane.origin - plane.x_dir * width / 2 - plane.y_dir * height / 2),
    ], [
        (0, 2, 1),
        (0, 3, 2),
    ], [
        (0, 0),
        (1, 0),
        (1, 1),
        (0, 1),
    ], (1, 1, 1, 1))

    # Return the GLTF binary blob and the suggested name of the image
    return b''.join(mgr.build().save_to_bytes()), name
