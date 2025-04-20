import importlib.metadata

import numpy as np
from build123d import Location, Plane, Vector
from pygltflib import *

_checkerboard_image_bytes = base64.decodebytes(
    b'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVQI12N49OjR////Gf'
    b'/////48WMATwULS8tcyj8AAAAASUVORK5CYII=')

def get_version() -> str:
    try:
        return importlib.metadata.version("yacv_server")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


class GLTFMgr:
    """A utility class to build our GLTF2 objects easily and incrementally"""

    gltf: GLTF2

    # Intermediate data to be filled by the add_* methods and merged into the GLTF object
    # - Face data
    face_indices: List[int]  # 3 indices per triangle
    face_positions: List[float]  # x, y, z
    face_tex_coords: List[float]  # u, v
    face_colors: List[float]  # r, g, b, a
    image: Optional[Tuple[bytes, str]]  # image/png
    # - Edge data
    edge_indices: List[int]  # 2 indices per edge
    edge_positions: List[float]  # x, y, z
    edge_colors: List[float]  # r, g, b, a
    # - Vertex data
    vertex_indices: List[int]  # 1 index per vertex
    vertex_positions: List[float]  # x, y, z
    vertex_colors: List[float]  # r, g, b, a

    def __init__(self, image: Optional[Tuple[bytes, str]] = (_checkerboard_image_bytes, 'image/png')):
        self.gltf = GLTF2(
            asset=Asset(generator=f"yacv_server@{get_version()}"),
            scene=0,
            scenes=[Scene(nodes=[0])],
            nodes=[Node(mesh=0)],  # TODO: Server-side detection of shallow copies --> nodes
            meshes=[Mesh(primitives=[
                Primitive(indices=-1, attributes=Attributes(), mode=TRIANGLES, material=0,
                          extras={"face_triangles_end": []}),
                Primitive(indices=-1, attributes=Attributes(), mode=LINES, material=0,
                          extras={"edge_points_end": []}),
                Primitive(indices=-1, attributes=Attributes(), mode=POINTS, material=0),
            ])],
            materials=[Material(pbrMetallicRoughness=PbrMetallicRoughness(metallicFactor=0.1, roughnessFactor=1.0),
                                alphaCutoff=None)],
        )
        self.face_indices = []
        self.face_positions = []
        self.face_tex_coords = []
        self.face_colors = []
        self.image = image
        self.edge_indices = []
        self.edge_positions = []
        self.edge_colors = []
        self.vertex_indices = []
        self.vertex_positions = []
        self.vertex_colors = []

    @property
    def _faces_primitive(self) -> Primitive:
        return [p for p in self.gltf.meshes[0].primitives if p.mode == TRIANGLES][0]

    @property
    def _edges_primitive(self) -> Primitive:
        return [p for p in self.gltf.meshes[0].primitives if p.mode == LINES][0]

    @property
    def _vertices_primitive(self) -> Primitive:
        return [p for p in self.gltf.meshes[0].primitives if p.mode == POINTS][0]

    def add_face(self, vertices_raw: List[Vector], indices_raw: List[Tuple[int, int, int]],
                 tex_coord_raw: List[Tuple[float, float]], color: Optional[Tuple[float, float, float, float]] = None):
        """Add a face to the GLTF mesh"""
        if color is None: color = (1.0, 0.75, 0.0, 1.0)
        # assert len(vertices_raw) == len(tex_coord_raw), f"Vertices and texture coordinates have different lengths"
        # assert min([i for t in indices_raw for i in t]) == 0, f"Face indices start at {min(indices_raw)}"
        # assert max([e for t in indices_raw for e in t]) < len(vertices_raw), f"Indices have non-existing vertices"
        base_index = len(self.face_positions) // 3  # All the new indices reference the new vertices
        self.face_indices.extend([base_index + i for t in indices_raw for i in t])
        self.face_positions.extend([v for t in vertices_raw for v in t])
        self.face_tex_coords.extend([c for t in tex_coord_raw for c in t])
        self.face_colors.extend([col for _ in range(len(vertices_raw)) for col in color])
        self._faces_primitive.extras["face_triangles_end"].append(len(self.face_indices))

    def add_edge(self, vertices_raw: List[Tuple[Tuple[float, float, float], Tuple[float, float, float]]],
                 color: Optional[Tuple[float, float, float, float]] = None):
        """Add an edge to the GLTF mesh"""
        if color is None: color = (0.1, 0.1, 1.0, 1.0)
        vertices_flat = [v for t in vertices_raw for v in t]  # Line from 0 to 1, 2 to 3, 4 to 5, etc.
        base_index = len(self.edge_positions) // 3
        self.edge_indices.extend([base_index + i for i in range(len(vertices_flat))])
        self.edge_positions.extend([v for t in vertices_flat for v in t])
        self.edge_colors.extend([col for _ in range(len(vertices_flat)) for col in color])
        self._edges_primitive.extras["edge_points_end"].append(len(self.edge_indices))

    def add_vertex(self, vertex: Tuple[float, float, float], color: Optional[Tuple[float, float, float, float]] = None):
        """Add a vertex to the GLTF mesh"""
        if color is None: color = (0.1, 0.1, 0.1, 1.0)
        base_index = len(self.vertex_positions) // 3
        self.vertex_indices.append(base_index)
        self.vertex_positions.extend(vertex)
        self.vertex_colors.extend(color)

    def add_location(self, loc: Location):
        """Add a location to the GLTF as a new primitive of the unique mesh"""
        pl = Plane(loc)

        def vert(v: Vector) -> Tuple[float, float, float]:
            return v.X, v.Y, v.Z

        # Add 1 origin vertex and 3 edges with custom colors to identify the X, Y and Z axis
        self.add_vertex(vert(pl.origin))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.x_dir))], color=(0.97, 0.24, 0.24, 1))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.y_dir))], color=(0.42, 0.8, 0.15, 1))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.z_dir))], color=(0.09, 0.55, 0.94, 1))

    def build(self) -> GLTF2:
        """Merge the intermediate data into the GLTF object and return it"""
        buffers_list: List[Tuple[Accessor, BufferView, bytes]] = []

        if len(self.face_indices) > 0:
            self._faces_primitive.indices = len(buffers_list)
            buffers_list.append(_gen_buffer_metadata(self.face_indices, 1))
            self._faces_primitive.attributes.POSITION = len(buffers_list)
            buffers_list.append(_gen_buffer_metadata(self.face_positions, 3))
            self._faces_primitive.attributes.TEXCOORD_0 = len(buffers_list)
            buffers_list.append(_gen_buffer_metadata(self.face_tex_coords, 2))
            self._faces_primitive.attributes.COLOR_0 = len(buffers_list)
            buffers_list.append(_gen_buffer_metadata(self.face_colors, 4))
        else:
            self.image = None  # Unused image
            self.gltf.meshes[0].primitives = list(  # Remove unused faces primitive
                filter(lambda p: p.mode != TRIANGLES, self.gltf.meshes[0].primitives))

        edges_and_vertices_mat = 0
        if self.image is not None and (len(self.edge_indices) > 0 or len(self.vertex_indices) > 0):
            # Create a material without texture for edges and vertices
            edges_and_vertices_mat = len(self.gltf.materials)
            new_mat = copy.deepcopy(self.gltf.materials[0])
            new_mat.pbrMetallicRoughness.baseColorTexture = None
            self.gltf.materials.append(new_mat)

        # Treat edges and vertices the same way
        for (indices, positions, colors, primitive, kind) in [
            (self.edge_indices, self.edge_positions, self.edge_colors, self._edges_primitive, LINES),
            (self.vertex_indices, self.vertex_positions, self.vertex_colors, self._vertices_primitive, POINTS)
        ]:
            if len(indices) > 0:
                primitive.material = edges_and_vertices_mat
                primitive.indices = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(indices, 1))
                primitive.attributes.POSITION = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(positions, 3))
                primitive.attributes.COLOR_0 = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(colors, 4))
            else:
                self.gltf.meshes[0].primitives = list(  # Remove unused edges primitive
                    filter(lambda p: p.mode != kind, self.gltf.meshes[0].primitives))

        if self.image is not None:  # Add texture last as it creates a fake accessor that is not added!
            self.gltf.images = [Image(bufferView=len(buffers_list), mimeType=self.image[1])]
            self.gltf.textures = [Texture(source=0, sampler=0)]
            self.gltf.samplers = [Sampler(magFilter=NEAREST)]
            # noinspection PyPep8Naming
            self.gltf.materials[0].pbrMetallicRoughness.baseColorTexture = TextureInfo(index=0)
            buffers_list.append((Accessor(), BufferView(), self.image[0]))

        # Once all the data is ready, we can concatenate the buffers updating the accessors and views
        prev_binary_blob = self.gltf.binary_blob() or b''
        byte_offset_base = len(prev_binary_blob)
        for accessor, bufferView, blob in buffers_list:

            if accessor.componentType is not None:  # Remove accessor of texture
                buffer_view_base = len(self.gltf.bufferViews)
                accessor.bufferView = buffer_view_base
                self.gltf.accessors.append(accessor)

            bufferView.buffer = 0
            bufferView.byteOffset = byte_offset_base
            bufferView.byteLength = len(blob)
            self.gltf.bufferViews.append(bufferView)

            byte_offset_base += len(blob)
            prev_binary_blob += blob

        self.gltf.buffers.append(Buffer(byteLength=byte_offset_base))
        self.gltf.set_binary_blob(prev_binary_blob)

        return self.gltf


def _gen_buffer_metadata(data: List[any], chunk: int) -> Tuple[Accessor, BufferView, bytes]:
    return Accessor(
        componentType={1: UNSIGNED_INT, 2: FLOAT, 3: FLOAT, 4: FLOAT}[chunk],
        count=len(data) // chunk,
        type={1: SCALAR, 2: VEC2, 3: VEC3, 4: VEC4}[chunk],
        max=[max(data[i::chunk]) for i in range(chunk)],
        min=[min(data[i::chunk]) for i in range(chunk)],
    ), BufferView(
        target={1: ELEMENT_ARRAY_BUFFER, 2: ARRAY_BUFFER, 3: ARRAY_BUFFER, 4: ARRAY_BUFFER}[chunk],
    ), np.array(data, dtype={1: np.uint32, 2: np.float32, 3: np.float32, 4: np.float32}[chunk]).tobytes()
