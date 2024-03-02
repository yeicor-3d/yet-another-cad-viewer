"""
Utilities to work with CAD objects
"""
from typing import Optional, Union, List, Tuple

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape

CADLike = Union[TopoDS_Shape, TopLoc_Location]  # Faces, Edges, Vertices and Locations for now


def get_shape(obj: any, error: bool = True) -> Optional[CADLike]:
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


def grab_all_cad() -> List[Tuple[str, CADLike]]:
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

# TODO: Image to CAD utility and show_image shortcut on server.
