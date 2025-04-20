from typing import List, Dict, Tuple, Optional

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Face, TopoDS_Edge, TopoDS_Shape, TopoDS_Vertex
from build123d import Vertex, Face, Location, Compound
from pygltflib import GLTF2

from yacv_server.cad import CADCoreLike, ColorTuple
from yacv_server.gltf import GLTFMgr
from yacv_server.mylogger import logger


def tessellate(
        cad_like: CADCoreLike,
        tolerance: float = 0.1,
        angular_tolerance: float = 0.1,
        faces: bool = True,
        edges: bool = True,
        vertices: bool = True,
        obj_color: Optional[ColorTuple] = None,
        texture: Optional[Tuple[bytes, str]] = None,
) -> GLTF2:
    """Tessellate a whole shape into a list of triangle vertices and a list of triangle indices."""
    if texture is None:
        mgr = GLTFMgr()
    else:
        mgr = GLTFMgr(texture)

    if isinstance(cad_like, TopLoc_Location):
        mgr.add_location(Location(cad_like))

    elif isinstance(cad_like, TopoDS_Shape):
        shape = Compound(cad_like)

        # Perform tessellation tasks
        edge_to_faces: Dict[str, List[TopoDS_Face]] = {}
        vertex_to_faces: Dict[str, List[TopoDS_Face]] = {}
        if faces and hasattr(shape, 'faces'):
            shape_faces = shape.faces()
            for face in shape_faces:
                _tessellate_face(mgr, face.wrapped, tolerance, angular_tolerance, obj_color)
                if edges:
                    for edge in face.edges():
                        edge_to_faces[edge.wrapped] = edge_to_faces.get(edge.wrapped, []) + [face.wrapped]
                if vertices:
                    for vertex in face.vertices():
                        vertex_to_faces[vertex.wrapped] = vertex_to_faces.get(vertex.wrapped, []) + [face.wrapped]
            if len(shape_faces) > 0: obj_color = None  # Don't color edges/vertices if faces are colored
        if edges and hasattr(shape, 'edges'):
            shape_edges = shape.edges()
            for edge in shape_edges:
                _tessellate_edge(mgr, edge.wrapped, edge_to_faces.get(edge.wrapped, []), angular_tolerance,
                                 angular_tolerance, obj_color)
            if len(shape_edges) > 0: obj_color = None  # Don't color vertices if edges are colored
        if vertices and hasattr(shape, 'vertices'):
            for vertex in shape.vertices():
                _tessellate_vertex(mgr, vertex.wrapped, vertex_to_faces.get(vertex.wrapped, []), obj_color)

    else:
        raise TypeError(f"Unsupported type: {type(cad_like)}: {cad_like}")

    return mgr.build()


def _tessellate_face(
        mgr: GLTFMgr,
        ocp_face: TopoDS_Face,
        tolerance: float = 1e-3,
        angular_tolerance: float = 0.1,
        color: Optional[ColorTuple] = None,
):
    face = Compound(ocp_face)
    # face.mesh(tolerance, angular_tolerance)
    tri_mesh = face.tessellate(tolerance, angular_tolerance)
    # noinspection PyArgumentList
    poly = BRep_Tool.Triangulation_s(face.wrapped, TopLoc_Location())
    if poly is None:
        logger.warn("No triangulation found for face")
        return GLTF2()

    # Get UV of each face from the parameters
    uv = [
        (v.X(), v.Y())
        for v in (poly.UVNode(i) for i in range(1, poly.NbNodes() + 1))
    ]

    vertices = tri_mesh[0]
    indices = tri_mesh[1]
    mgr.add_face(vertices, indices, uv, color)
    return None


def _push_point(v: Tuple[float, float, float], faces: List[TopoDS_Face]) -> Tuple[float, float, float]:
    # Use the connected faces to push edges/vertices and make them always visible
    push_dir = (0, 0, 0)
    for ocp_face in faces:
        normal = Face(ocp_face).normal_at(v)
        push_dir = (push_dir[0] + normal.X, push_dir[1] + normal.Y, push_dir[2] + normal.Z)
    if push_dir != (0, 0, 0):
        # Normalize the push direction by the number of faces and a constant factor
        # NOTE: Don't overdo it, or metrics will be (more) wrong
        n = 1e-3 / len(faces)
        push_dir = (push_dir[0] * n, push_dir[1] * n, push_dir[2] * n)
        # Push the vertex by the normal
        v = (v[0] + push_dir[0], v[1] + push_dir[1], v[2] + push_dir[2])
    return v


def _tessellate_edge(
        mgr: GLTFMgr,
        ocp_edge: TopoDS_Edge,
        faces: List[TopoDS_Face],
        angular_deflection: float = 0.1,
        curvature_deflection: float = 0.1,
        color: Optional[ColorTuple] = None,
):
    # Use a curve discretizer to get the vertices
    curve = BRepAdaptor_Curve(ocp_edge)
    discretizer = GCPnts_TangentialDeflection(curve, angular_deflection, curvature_deflection)
    assert discretizer.NbPoints() > 1, "Edge is too small??"

    # add vertices
    vertices = [
        _push_point((v.X(), v.Y(), v.Z()), faces)
        for v in (
            discretizer.Value(i)  # .Transformed(transformation)
            for i in range(1, discretizer.NbPoints() + 1)
        )
    ]

    # Convert strip of vertices to a list of pairs of vertices
    vertices = [(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
    mgr.add_edge(vertices, color)


def _tessellate_vertex(mgr: GLTFMgr, ocp_vertex: TopoDS_Vertex, faces: List[TopoDS_Face],
                          color: Optional[ColorTuple] = None):
    c = Vertex(ocp_vertex).center()
    mgr.add_vertex(_push_point((c.X, c.Y, c.Z), faces), color)


