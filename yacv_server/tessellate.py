import concurrent
import copy
import hashlib
import io
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Tuple, Generator

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS_Face, TopoDS_Edge, TopoDS_Shape, TopoDS_Vertex
from build123d import Face, Vector, Shape, Vertex
from pygltflib import LINE_STRIP, GLTF2, Material, PbrMetallicRoughness, TRIANGLES, POINTS, TextureInfo

import mylogger
from gltf import GLTFMgr


@dataclass
class TessellationUpdate:
    """Tessellation update"""
    progress: float
    """Progress in percent"""

    # Current shape
    shape: TopoDS_Shape
    """(Sub)shape that was tessellated"""
    gltf: GLTF2
    """The valid GLTF containing only the current shape"""

    @property
    def kind(self) -> str:
        """The kind of the shape"""
        if isinstance(self.shape, TopoDS_Face):
            return "face"
        elif isinstance(self.shape, TopoDS_Edge):
            return "edge"
        elif isinstance(self.shape, TopoDS_Vertex):
            return "vertex"
        else:
            raise ValueError(f"Unknown shape type: {self.shape}")


def tessellate_count(ocp_shape: TopoDS_Shape) -> int:
    """Count the number of elements that will be tessellated"""
    shape = Shape(ocp_shape)
    return len(shape.faces()) + len(shape.edges()) + len(shape.vertices())


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
            _tessellate_edge(mgr, edge.wrapped, tolerance, angular_tolerance)
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
    face = Face(ocp_face)
    face.mesh(tolerance, angular_tolerance)
    loc = TopLoc_Location()
    poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
    if poly is None:
        mylogger.logger.warn("No triangulation found for face")
        return GLTF2()
    tri_mesh = face.tessellate(tolerance, angular_tolerance)

    # Get UV of each face from the parameters
    uv = [
        [v.X(), v.Y()]
        for v in (poly.UVNode(i) for i in range(1, poly.NbNodes() + 1))
    ]

    vertices = np.array(list(map(lambda v: [v.X, v.Y, v.Z], tri_mesh[0])))
    indices = np.array(tri_mesh[1])
    tex_coord = np.array(uv)
    mgr.add_face(vertices, indices, tex_coord)


def _tessellate_edge(
        mgr: GLTFMgr,
        ocp_edge: TopoDS_Edge,
        angular_deflection: float = 1e-3,
        curvature_deflection: float = 0.1,
):
    curve = BRepAdaptor_Curve(ocp_edge)
    discretizer = GCPnts_TangentialDeflection(curve, angular_deflection, curvature_deflection)
    assert discretizer.NbPoints() > 1, "Edge is too small??"

    # TODO: get and apply transformation??

    # add vertices
    vertices: list[list[float]] = [
        [v.X(), v.Y(), v.Z()]
        for v in (
            discretizer.Value(i)  # .Transformed(transformation)
            for i in range(1, discretizer.NbPoints() + 1)
        )
    ]
    mgr.add_edge(np.array(vertices))


def _tessellate_vertex(mgr: GLTFMgr, ocp_vertex: TopoDS_Vertex):
    c = Vertex(ocp_vertex).center()
    mgr.add_vertex(c)


def _hashcode(obj: TopoDS_Shape) -> str:
    """Utility to compute the hash code of a shape recursively without the need to tessellate it"""
    # NOTE: obj.HashCode(MAX_HASH_CODE) is not stable across different runs of the same program
    # This is best-effort and not guaranteed to be unique
    data = io.BytesIO()
    map_of_shapes = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(obj, map_of_shapes)
    for i in range(1, map_of_shapes.Extent() + 1):
        sub_shape = map_of_shapes.FindKey(i)
        sub_data = io.BytesIO()
        TopoDS_Shape.DumpJson(sub_shape, sub_data)
        val = sub_data.getvalue()
        val = re.sub(b'"this": "[^"]*"', b'', val)  # Remove memory address
        data.write(val)
    to_hash = data.getvalue()
    return hashlib.md5(to_hash, usedforsecurity=False).hexdigest()
