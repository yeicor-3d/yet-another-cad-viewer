import concurrent
import copyreg
from concurrent.futures import ProcessPoolExecutor, Executor
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Callable

import OCP
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.TopoDS import TopoDS_Face, TopoDS_Edge, TopoDS_Shape
from build123d import Face, Vector, Shape
from partcad.wrappers import cq_serialize


class UVMode(Enum):
    """UV mode for tesselation"""

    TRIPLANAR = 0
    """Triplanar UV mapping"""
    FACE = 1
    """Use UV coordinates from each face"""


@dataclass
class TessellationUpdate:
    """Tessellation update"""

    # Progress
    root: TopoDS_Shape
    """The root shape that is being tessellated"""
    progress: float
    """Progress in percent"""

    # Current shape
    shape: TopoDS_Shape
    """Shape that was tessellated"""
    vertices: list[Vector]
    """List of vertices"""
    indices: Optional[list[Tuple[int, int, int]]]
    """List of indices (only for faces)"""


progress_callback_t = Callable[[TessellationUpdate], None]


def _inflate_vec(*values: float):
    pnt = OCP.gp.gp_Vec(values[0], values[1], values[2])
    return pnt


def _reduce_vec(pnt: OCP.gp.gp_Vec):
    return _inflate_vec, (pnt.X(), pnt.Y(), pnt.Z())


def tessellate(
        ocp_shape: TopoDS_Shape,
        progress_callback: progress_callback_t = None,
        tolerance: float = 0.1,
        angular_tolerance: float = 0.1,
        uv: Optional[UVMode] = None,
        executor: Executor = ProcessPoolExecutor(),  # Set to ThreadPoolExecutor if pickling fails...
):
    """Tessellate a whole shape into a list of triangle vertices and a list of triangle indices.

    It uses multiprocessing to speed up the process, and publishes progress updates to the callback.
    """
    shape = Shape(ocp_shape)
    _register_pickle_if_needed()
    with executor:
        futures = []

        # Submit tessellation tasks
        for face in shape.faces():
            futures.append(executor.submit(_tessellate_element, face.wrapped, tolerance, angular_tolerance, uv))
        for edge in shape.edges():
            futures.append(executor.submit(_tessellate_element, edge.wrapped, tolerance, angular_tolerance, uv))

        # Collect results as they come in
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            tessellation, shape = future.result()
            is_face = isinstance(shape, TopoDS_Face)
            update = TessellationUpdate(
                root=ocp_shape,
                progress=(i + 1) / len(futures),
                shape=shape,
                vertices=tessellation[0] if is_face else tessellation,
                indices=tessellation[1] if is_face else None,
            )
            progress_callback(update)


_pickle_registered = False


def _register_pickle_if_needed():
    global _pickle_registered
    if _pickle_registered:
        return
    cq_serialize.register()
    copyreg.pickle(OCP.gp.gp_Vec, _reduce_vec)


# Define the function that will tessellate each element in parallel
def _tessellate_element(element: TopoDS_Shape, tolerance, angular_tolerance, uv):
    if isinstance(element, TopoDS_Face):
        return _tessellate_face(element, tolerance, angular_tolerance, uv), element
    elif isinstance(element, TopoDS_Edge):
        return _tessellate_edge(element, angular_tolerance, angular_tolerance), element


TriMesh = Tuple[list[Vector], list[Tuple[int, int, int]]]


def _tessellate_face(
        ocp_face: TopoDS_Face,
        tolerance: float = 0.1,
        angular_tolerance: float = 0.1,
        uv: Optional[UVMode] = None,
) -> TriMesh:
    """Tessellate a face into a list of triangle vertices and a list of triangle indices"""
    face = Face(ocp_face)
    tri_mesh = face.tessellate(tolerance, angular_tolerance)

    # TODO: UV mapping

    return tri_mesh


def _tessellate_edge(
        ocp_edge: TopoDS_Edge,
        angular_deflection: float = 0.1,
        curvature_deflection: float = 0.1,
) -> list[Vector]:
    """Tessellate a wire or edge into a list of ordered vertices"""
    curve = BRepAdaptor_Curve(ocp_edge)
    discretizer = GCPnts_TangentialDeflection(curve, angular_deflection, curvature_deflection)
    assert discretizer.NbPoints() > 1, "Edge is too small??"

    # TODO: get transformation??

    # add vertices
    vertices: list[Vector] = [
        Vector(v.X(), v.Y(), v.Z())
        for v in (
            discretizer.Value(i)  # .Transformed(transformation)
            for i in range(1, discretizer.NbPoints() + 1)
        )
    ]

    return vertices
