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
from gltf import create_gltf, _checkerboard_image


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
        tolerance: float = 0.1,
        angular_tolerance: float = 0.1,
) -> Generator[TessellationUpdate, None, None]:
    """Tessellate a whole shape into a list of triangle vertices and a list of triangle indices.

    NOTE: The logic of the method is weird because multiprocessing was tested, but it seems too inefficient
    with slow native packages.
    """
    shape = Shape(ocp_shape)
    features = []

    # Submit tessellation tasks
    for face in shape.faces():
        features.append(_tessellate_element(face.wrapped, tolerance, angular_tolerance))
    for edge in shape.edges():
        features.append(_tessellate_element(edge.wrapped, tolerance, angular_tolerance))
    for vertex in shape.vertices():
        features.append(_tessellate_element(vertex.wrapped, tolerance, angular_tolerance))

    # Collect results as they come in
    for i, future in enumerate(features):
        sub_shape, gltf = future
        yield TessellationUpdate(
            progress=(i + 1) / len(features),
            shape=sub_shape,
            gltf=gltf,
        )


# Define the function that will tessellate each element in parallel
def _tessellate_element(
        element: TopoDS_Shape, tolerance: float, angular_tolerance: float) -> Tuple[TopoDS_Shape, GLTF2]:
    if isinstance(element, TopoDS_Face):
        return element, _tessellate_face(element, tolerance, angular_tolerance)
    elif isinstance(element, TopoDS_Edge):
        return element, _tessellate_edge(element, angular_tolerance, angular_tolerance)
    elif isinstance(element, TopoDS_Vertex):
        return element, _tessellate_vertex(element)
    else:
        raise ValueError(f"Unknown element type: {element}")


TriMesh = Tuple[list[Vector], list[Tuple[int, int, int]]]


def _tessellate_face(
        ocp_face: TopoDS_Face,
        tolerance: float = 0.1,
        angular_tolerance: float = 0.1
) -> GLTF2:
    """Tessellate a face into a list of triangle vertices and a list of triangle indices"""
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
    mode = TRIANGLES
    material = Material(pbrMetallicRoughness=PbrMetallicRoughness(
        baseColorFactor=[0.3, 1.0, 0.2, 1.0], metallicFactor=0.1, baseColorTexture=TextureInfo(index=0)),
        alphaCutoff=None)
    return create_gltf(vertices, indices, tex_coord, mode, material, images=[_checkerboard_image])


def _tessellate_edge(
        ocp_edge: TopoDS_Edge,
        angular_deflection: float = 0.1,
        curvature_deflection: float = 0.1,
) -> GLTF2:
    """Tessellate a wire or edge into a list of ordered vertices"""
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
    indices = np.array(list(map(lambda i: [i, i + 1], range(len(vertices) - 1))), dtype=np.uint8)
    tex_coord = np.array([], dtype=np.float32)
    mode = LINE_STRIP
    material = Material(
        pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[0.0, 0.0, 0.3, 1.0]),
        alphaCutoff=None)
    return create_gltf(np.array(vertices), indices, tex_coord, mode, material)


def _tessellate_vertex(ocp_vertex: TopoDS_Vertex) -> GLTF2:
    """Tessellate a vertex into a list of triangle vertices and a list of triangle indices"""
    c = Vertex(ocp_vertex).center()
    vertices = np.array([[c.X, c.Y, c.Z]])
    indices = np.array([0])
    tex_coord = np.array([], dtype=np.float32)
    mode = POINTS
    material = Material(
        pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[1.0, 0.5, 0.5, 1.0]),
        alphaCutoff=None)
    return create_gltf(vertices, indices, tex_coord, mode, material)


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
