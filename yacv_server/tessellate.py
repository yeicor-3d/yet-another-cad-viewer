import hashlib
import io
import re

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS_Face, TopoDS_Edge, TopoDS_Shape, TopoDS_Vertex
from build123d import Shape, Vertex
from pygltflib import GLTF2

import mylogger
from gltf import GLTFMgr


# TODO: Migrate to ocp-tessellate to reuse the tessellation logic


def tessellate(
        ocp_shape: TopoDS_Shape,
        tolerance: float = 1e-3,
        angular_tolerance: float = 0.1,
        faces: bool = True,
        edges: bool = True,
        vertices: bool = True,
) -> GLTF2:
    """Tessellate a whole shape into a list of triangle vertices and a list of triangle indices."""
    mgr = GLTFMgr()
    shape = Shape(ocp_shape)

    # Perform tessellation tasks
    if faces:
        for face in shape.faces():
            _tessellate_face(mgr, face.wrapped, tolerance, angular_tolerance)
    if edges:
        for edge in shape.edges():
            _tessellate_edge(mgr, edge.wrapped, angular_tolerance, angular_tolerance)
    if vertices:
        for vertex in shape.vertices():
            _tessellate_vertex(mgr, vertex.wrapped)

    return mgr.gltf


def _tessellate_face(
        mgr: GLTFMgr,
        ocp_face: TopoDS_Face,
        tolerance: float = 1e-3,
        angular_tolerance: float = 0.1
):
    face = Shape(ocp_face)
    face.mesh(tolerance, angular_tolerance)
    poly = BRep_Tool.Triangulation_s(face.wrapped, TopLoc_Location())
    if poly is None:
        mylogger.logger.warn("No triangulation found for face")
        return GLTF2()
    tri_mesh = face.tessellate(tolerance, angular_tolerance)

    # Get UV of each face from the parameters
    uv = [
        (v.X(), v.Y())
        for v in (poly.UVNode(i) for i in range(1, poly.NbNodes() + 1))
    ]

    vertices = [(v.X, v.Y, v.Z) for v in tri_mesh[0]]
    indices = tri_mesh[1]
    mgr.add_face(vertices, indices, uv)


def _tessellate_edge(
        mgr: GLTFMgr,
        ocp_edge: TopoDS_Edge,
        angular_deflection: float = 0.1,
        curvature_deflection: float = 0.1,
):
    curve = BRepAdaptor_Curve(ocp_edge)
    discretizer = GCPnts_TangentialDeflection(curve, angular_deflection, curvature_deflection)
    assert discretizer.NbPoints() > 1, "Edge is too small??"

    # add vertices
    vertices = [
        (v.X(), v.Y(), v.Z())
        for v in (
            discretizer.Value(i)  # .Transformed(transformation)
            for i in range(1, discretizer.NbPoints() + 1)
        )
    ]
    mgr.add_edge(vertices)


def _tessellate_vertex(mgr: GLTFMgr, ocp_vertex: TopoDS_Vertex):
    c = Vertex(ocp_vertex).center()
    mgr.add_vertex((c.X, c.Y, c.Z))


def _hashcode(obj: TopoDS_Shape) -> str:
    """Utility to compute the hash code of a shape recursively without the need to tessellate it"""
    # NOTE: obj.HashCode(MAX_HASH_CODE) is not stable across different runs of the same program
    # This is best-effort and not guaranteed to be unique
    map_of_shapes = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(obj, map_of_shapes)
    hasher = hashlib.md5(usedforsecurity=False)
    for i in range(1, map_of_shapes.Extent() + 1):
        sub_shape = map_of_shapes.FindKey(i)
        sub_data = io.BytesIO()
        TopoDS_Shape.DumpJson(sub_shape, sub_data)
        val = sub_data.getvalue()
        val = re.sub(b'"this": "[^"]*"', b'', val)  # Remove memory address
        hasher.update(val)
    return hasher.hexdigest()
