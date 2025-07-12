"""
Utilities to work with CAD objects
"""
import hashlib
import io
import re
from typing import Optional, Union, Tuple

from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS_Shape
from build123d import Compound, Color

from yacv_server.gltf import GLTFMgr

CADCoreLike = Union[TopoDS_Shape, TopLoc_Location]  # Faces, Edges, Vertices and Locations for now
CADLike = Union[CADCoreLike, any]  # build123d and cadquery types
ColorTuple = Tuple[float, float, float, float]


def get_color(obj: any) -> Optional[ColorTuple]:
    """Get color from a CAD Object or any other color-like object"""
    if 'color' in dir(obj):
        obj = obj.color
    if isinstance(obj, tuple):
        c = None
        if len(obj) == 3:
            c = obj + (1,)
        elif len(obj) == 4:
            c = obj
        # noinspection PyTypeChecker
        return [min(max(float(x), 0), 1) for x in c]
    if isinstance(obj, Color):
        return obj.to_tuple()
    return None


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

    # Handle iterables like Build123d ShapeList by extracting all sub-shapes and making a compound
    if isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set) or isinstance(obj, dict):
        try:
            if isinstance(obj, dict):
                obj_iter = iter(obj.values())
            else:
                obj_iter = iter(obj)
            # print(obj, ' -> ', obj_iter)
            shapes_raw = [get_shape(sub_obj, error=False) for sub_obj in obj_iter]
            # Silently drop non-shapes
            shapes_raw_filtered = [shape for shape in shapes_raw if shape is not None]
            if len(shapes_raw_filtered) > 0:  # Continue if we found at least one shape
                # Sorting is required to improve hashcode consistency
                shapes_raw_filtered_sorted = sorted(shapes_raw_filtered, key=lambda x: _hashcode(x))
                # Build a single compound shape (skip locations/axes here, they can't be in a Compound)
                shapes_bd = [Compound(shape) for shape in shapes_raw_filtered_sorted if shape is not None and not isinstance(shape, TopLoc_Location)]
                return get_shape(Compound(shapes_bd), error)
        except TypeError:
            pass

    if error:
        raise ValueError(f'Cannot show object of type {type(obj)} (submit issue?)')
    else:
        return None


def grab_all_cad() -> set[Tuple[str, CADCoreLike]]:
    """ Grab all shapes by inspecting the stack """
    import inspect
    stack = inspect.stack()
    shapes = set()
    for frame in stack:
        for key, value in frame.frame.f_locals.items():
            shape = get_shape(value, error=False)
            if shape and shape not in shapes:
                shapes.add((key, shape))
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
    _format: str
    if save_mime == 'image/jpeg':
        _format = 'JPEG'
    elif save_mime == 'image/png':
        _format = 'PNG'
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
    img.save(img_buf, format=_format)
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


def _hashcode(obj: Union[bytes, CADCoreLike], **extras) -> str:
    """Utility to compute the STABLE hash code of a shape"""
    # NOTE: obj.HashCode(MAX_HASH_CODE) is not stable across different runs of the same program
    # This is best-effort and not guaranteed to be unique
    hasher = hashlib.md5(usedforsecurity=False)
    for k, v in extras.items():
        hasher.update(str(k).encode())
        hasher.update(str(v).encode())
    if isinstance(obj, bytes):
        hasher.update(obj)
    elif isinstance(obj, TopLoc_Location):
        sub_data = io.BytesIO()
        obj.DumpJson(sub_data)
        hasher.update(sub_data.getvalue())
    elif isinstance(obj, TopoDS_Shape):
        map_of_shapes = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(obj, map_of_shapes)
        for i in range(1, map_of_shapes.Extent() + 1):
            sub_shape = map_of_shapes.FindKey(i)
            sub_data = io.BytesIO()
            TopoDS_Shape.DumpJson(sub_shape, sub_data)
            val = sub_data.getvalue()
            val = re.sub(b'"this": "[^"]*"', b'', val)  # Remove memory address
            hasher.update(val)
    else:
        raise ValueError(f'Cannot hash object of type {type(obj)}')
    return hasher.hexdigest()
