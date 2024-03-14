import importlib.metadata

import numpy as np
from build123d import Location, Plane, Vector
from pygltflib import *

_checkerboard_image_bytes = base64.decodebytes(
    b'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVQI12N49OjR////Gf'
    b'/////48WMATwULS8tcyj8AAAAASUVORK5CYII=')


class GLTFMgr:
    """A utility class to build our GLTF2 objects easily and incrementally"""

    def __init__(self, image: Tuple[bytes, str] = (_checkerboard_image_bytes, 'image/png')):
        self.gltf = GLTF2(
            asset=Asset(generator=f"yacv_server@{importlib.metadata.version('yacv_server')}"),
            scene=0,
            scenes=[Scene(nodes=[0])],
            nodes=[Node(mesh=0)],
            meshes=[Mesh(primitives=[])],
            accessors=[],
            bufferViews=[BufferView(buffer=0, byteLength=len(image[0]), byteOffset=0)],
            buffers=[Buffer(byteLength=len(image[0]))],
            samplers=[Sampler(magFilter=NEAREST)],
            textures=[Texture(source=0, sampler=0)],
            images=[Image(bufferView=0, mimeType=image[1])],
        )
        # TODO: Reduce the number of draw calls by merging all faces into a single primitive, and using
        #  color attributes + extension? to differentiate them (same for edges and vertices)
        self.gltf.set_binary_blob(image[0])

    def add_face(self, vertices_raw: List[Tuple[float, float, float]], indices_raw: List[Tuple[int, int, int]],
                 tex_coord_raw: List[Tuple[float, float]]):
        """Add a face to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[v[0], v[1], v[2]] for v in vertices_raw], dtype=np.float32)
        indices = np.array([[i[0], i[1], i[2]] for i in indices_raw], dtype=np.uint32)
        tex_coord = np.array([[t[0], t[1]] for t in tex_coord_raw], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=TRIANGLES, material="face")

    def add_edge(self, vertices_raw: List[Tuple[float, float, float]], mat: str = None):
        """Add an edge to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[v[0], v[1], v[2]] for v in vertices_raw], dtype=np.float32)
        indices = np.array(list(map(lambda i: [i, i + 1], range(len(vertices) - 1))), dtype=np.uint32)
        tex_coord = np.array([])
        self._add_any(vertices, indices, tex_coord, mode=LINE_STRIP, material=mat or "edge")

    def add_vertex(self, vertex: Tuple[float, float, float]):
        """Add a vertex to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[vertex[0], vertex[1], vertex[2]]])
        indices = np.array([[0]], dtype=np.uint32)
        tex_coord = np.array([], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=POINTS, material="vertex")

    def add_location(self, loc: Location):
        """Add a location to the GLTF as a new primitive of the unique mesh"""
        pl = Plane(loc)

        def vert(v: Vector) -> Tuple[float, float, float]:
            return v.X, v.Y, v.Z

        # Add 1 origin vertex and 3 edges with custom colors to identify the X, Y and Z axis
        self.add_vertex(vert(pl.origin))
        self.add_edge([vert(pl.origin), vert(pl.origin + pl.x_dir)], mat="locX")
        self.add_edge([vert(pl.origin), vert(pl.origin + pl.y_dir)], mat="locY")
        self.add_edge([vert(pl.origin), vert(pl.origin + pl.z_dir)], mat="locZ")

    def add_material(self, kind: str) -> int:
        """It is important to use a different material for each primitive to be able to change them at runtime"""
        new_material: Material
        if kind == "face":
            new_material = Material(name="face", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorTexture=TextureInfo(index=0), baseColorFactor=[1, 1, 0.5, 1]), doubleSided=True)
        elif kind == "edge":
            new_material = Material(name="edge", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0, 0, 0.5, 1]))
        elif kind == "vertex":
            new_material = Material(name="vertex", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0, 0.3, 0.3, 1]))
        elif kind == "locX":
            new_material = Material(name="locX", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0.97, 0.24, 0.24, 1]))
        elif kind == "locY":
            new_material = Material(name="locY", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0.42, 0.8, 0.15, 1]))
        elif kind == "locZ":
            new_material = Material(name="locZ", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0.09, 0.55, 0.94, 1]))
        else:
            raise ValueError(f"Unknown material kind {kind}")
        self.gltf.materials.append(new_material)
        return len(self.gltf.materials) - 1

    def _add_any(self, vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray, mode: int = TRIANGLES,
                 material: str = "face"):
        assert vertices.ndim == 2
        assert vertices.shape[1] == 3
        vertices = vertices.astype(np.float32)
        vertices_blob = vertices.tobytes()

        assert indices.ndim == 2
        assert indices.shape[1] == 3 and mode == TRIANGLES or indices.shape[1] == 2 and mode == LINE_STRIP or \
               indices.shape[1] == 1 and mode == POINTS
        indices = indices.astype(np.uint32)
        indices_blob = indices.flatten().tobytes()

        # Check that all vertices are referenced by the indices
        # This can happen on broken faces like on some fonts
        # assert indices.max() == len(vertices) - 1, f"{indices.max()} != {len(vertices) - 1}"
        # assert indices.min() == 0, f"min({indices}) != 0"
        # assert np.unique(indices.flatten()).size == len(vertices)

        assert len(tex_coord) == 0 or tex_coord.ndim == 2
        assert len(tex_coord) == 0 or tex_coord.shape[1] == 2
        tex_coord = tex_coord.astype(np.float32)
        tex_coord_blob = tex_coord.tobytes()

        accessor_base = len(self.gltf.accessors)
        self.gltf.meshes[0].primitives.append(
            Primitive(
                attributes=Attributes(POSITION=accessor_base + 1, TEXCOORD_0=accessor_base + 2)
                if len(tex_coord) > 0 else Attributes(POSITION=accessor_base + 1),
                indices=accessor_base,
                mode=mode,
                material=self.add_material(material),
            )
        )

        buffer_view_base = len(self.gltf.bufferViews)
        self.gltf.accessors.extend([it for it in [
            Accessor(
                bufferView=buffer_view_base,
                componentType=UNSIGNED_INT,
                count=indices.size,
                type=SCALAR,
                max=[int(indices.max())],
                min=[int(indices.min())],
            ),
            Accessor(
                bufferView=buffer_view_base + 1,
                componentType=FLOAT,
                count=len(vertices),
                type=VEC3,
                max=vertices.max(axis=0).tolist(),
                min=vertices.min(axis=0).tolist(),
            ),
            Accessor(
                bufferView=buffer_view_base + 2,
                componentType=FLOAT,
                count=len(tex_coord),
                type=VEC2,
                max=tex_coord.max(axis=0).tolist(),
                min=tex_coord.min(axis=0).tolist(),
            ) if len(tex_coord) > 0 else None
        ] if it is not None])

        prev_binary_blob = self.gltf.binary_blob()
        byte_offset_base = len(prev_binary_blob)
        self.gltf.bufferViews.extend([bv for bv in [
            BufferView(
                buffer=0,
                byteOffset=byte_offset_base,
                byteLength=len(indices_blob),
                target=ELEMENT_ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=byte_offset_base + len(indices_blob),
                byteLength=len(vertices_blob),
                target=ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=byte_offset_base + len(indices_blob) + len(vertices_blob),
                byteLength=len(tex_coord_blob),
                target=ARRAY_BUFFER,
            )
        ] if bv.byteLength > 0])

        self.gltf.set_binary_blob(prev_binary_blob + indices_blob + vertices_blob + tex_coord_blob)
