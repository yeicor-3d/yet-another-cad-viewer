import importlib.metadata

import numpy as np
from pygltflib import *

_checkerboard_image_bytes = base64.decodebytes(
    b'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVQI12N49OjR////Gf'
    b'/////48WMATwULS8tcyj8AAAAASUVORK5CYII=')


class GLTFMgr:
    """A utility class to build our GLTF2 objects easily and incrementally"""

    gltf: GLTF2 = GLTF2(
        asset=Asset(generator=f"yacv_server@{importlib.metadata.version('yacv_server')}"),
        scene=0,
        scenes=[Scene(nodes=[0])],
        nodes=[Node(mesh=0)],
        meshes=[Mesh(primitives=[])],
        accessors=[],
        bufferViews=[BufferView(buffer=0, byteLength=len(_checkerboard_image_bytes), byteOffset=0)],
        buffers=[Buffer(byteLength=len(_checkerboard_image_bytes))],
        samplers=[Sampler(magFilter=NEAREST)],
        textures=[Texture(source=0, sampler=0)],
        images=[Image(bufferView=0, mimeType='image/png')],
    )

    def __init__(self):
        self.gltf.set_binary_blob(_checkerboard_image_bytes)

    def add_face(self, vertices_raw: List[Tuple[float, float, float]], indices_raw: List[Tuple[int, int, int]],
                 tex_coord_raw: List[Tuple[float, float]]):
        """Add a face to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[v[0], v[1], v[2]] for v in vertices_raw], dtype=np.float32)
        indices = np.array([[i[0], i[1], i[2]] for i in indices_raw], dtype=np.uint32)
        tex_coord = np.array([[t[0], t[1]] for t in tex_coord_raw], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=TRIANGLES, material="face")

    def add_edge(self, vertices_raw: List[Tuple[float, float, float]]):
        """Add an edge to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[v[0], v[1], v[2]] for v in vertices_raw], dtype=np.float32)
        indices = np.array(list(map(lambda i: [i, i + 1], range(len(vertices) - 1))), dtype=np.uint32)
        tex_coord = np.array([])
        self._add_any(vertices, indices, tex_coord, mode=LINE_STRIP, material="edge")

    def add_vertex(self, vertex: Tuple[float, float, float]):
        """Add a vertex to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[vertex[0], vertex[1], vertex[2]]])
        indices = np.array([[0]], dtype=np.uint32)
        tex_coord = np.array([], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=POINTS, material="vertex")

    def add_material(self, kind: str) -> int:
        """It is important to use a different material for each primitive to be able to change them at runtime"""
        new_material: Material
        if kind == "face":
            new_material = Material(name="face", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorTexture=TextureInfo(index=0), baseColorFactor=[1, 1, 0.5, 1]))
        elif kind == "edge":
            new_material = Material(name="edge", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0, 0, 0.5, 1]))
        elif kind == "vertex":
            new_material = Material(name="vertex", alphaCutoff=None, pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=[0, 0.2, 0, 1]))
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
        assert indices.max() == len(vertices) - 1, f"{indices.max()} != {len(vertices) - 1}"
        assert indices.min() == 0
        assert np.unique(indices.flatten()).size == len(vertices)

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

        binary_blob = self.gltf.binary_blob()
        byte_offset_base = len(binary_blob)
        self.gltf.bufferViews.extend([it for it in [
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
            ) if len(tex_coord) > 0 else None
        ] if it is not None])

        self.gltf.set_binary_blob(binary_blob + indices_blob + vertices_blob + tex_coord_blob)


#
#
# def create_gltf(vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray, mode: int = TRIANGLES,
#                 material: Optional[Material] = None, images: Optional[List[Image]] = None) -> GLTF2:
#     """Create a glTF object from vertices and optionally indices.
#
#     If indices are not set, vertices are interpreted as line_strip."""
#
#     assert vertices.ndim == 2
#     assert vertices.shape[1] == 3
#     vertices = vertices.astype(np.float32)
#     vertices_blob = vertices.tobytes()
#     # print(vertices)
#
#     indices = indices.astype(np.uint8)
#     indices_blob = indices.flatten().tobytes()
#     # print(indices)
#
#     tex_coord = tex_coord.astype(np.float32)
#     tex_coord_blob = tex_coord.tobytes()
#     # print(tex_coord)
#
#     if images is None:
#         images = []
#     image_blob = b''
#     image_blob_pointers = []
#     for i, img in enumerate(images):
#         image_blob = img_to_blob(i, image_blob, image_blob_pointers, images, img)
#
#     gltf = GLTF2(
#         scene=0,
#         scenes=[Scene(nodes=[0])],
#         nodes=[Node(mesh=0)],
#         meshes=[
#             Mesh(
#                 primitives=[
#                     Primitive(
#                         attributes=Attributes(POSITION=1, TEXCOORD_0=2) if len(tex_coord) > 0 else Attributes(
#                             POSITION=1),
#                         indices=0,
#                         mode=mode,
#                         material=0 if material is not None else None,
#                     )
#                 ]
#             )
#         ],
#         materials=[material] if material is not None else [],
#         accessors=[
#                       Accessor(
#                           bufferView=0,
#                           componentType=UNSIGNED_BYTE,
#                           count=indices.size,
#                           type=SCALAR,
#                           max=[int(indices.max())],
#                           min=[int(indices.min())],
#                       ),
#                       Accessor(
#                           bufferView=1,
#                           componentType=FLOAT,
#                           count=len(vertices),
#                           type=VEC3,
#                           max=vertices.max(axis=0).tolist(),
#                           min=vertices.min(axis=0).tolist(),
#                       ),
#                   ] + ([
#                            Accessor(
#                                bufferView=2,
#                                componentType=FLOAT,
#                                count=len(tex_coord),
#                                type=VEC2,
#                                max=tex_coord.max(axis=0).tolist(),
#                                min=tex_coord.min(axis=0).tolist(),
#                            )] if len(tex_coord) > 0 else [])
#         ,
#         bufferViews=[
#                         BufferView(
#                             buffer=0,
#                             byteLength=len(indices_blob),
#                             target=ELEMENT_ARRAY_BUFFER,
#                         ),
#                         BufferView(
#                             buffer=0,
#                             byteOffset=len(indices_blob),
#                             byteLength=len(vertices_blob),
#                             target=ARRAY_BUFFER,
#                         ),
#                     ] + (
#                         [
#                             BufferView(
#                                 buffer=0,
#                                 byteOffset=len(indices_blob) + len(vertices_blob),
#                                 byteLength=len(tex_coord_blob),
#                                 target=ARRAY_BUFFER,
#                             ),
#                         ] if len(tex_coord) > 0 else []) + (
#                         [
#                             BufferView(
#                                 buffer=0,
#                                 byteOffset=len(indices_blob) + len(
#                                     vertices_blob) + len(tex_coord_blob) + image_blob_pointers[i],
#                                 byteLength=image_blob_pointers[i + 1] - image_blob_pointers[i] if i + 1 < len(
#                                     image_blob_pointers) else len(image_blob) - image_blob_pointers[i],
#                             )
#                             for i, img in enumerate(images)
#                         ] if len(images) > 0 else []),
#         buffers=[
#             Buffer(
#                 byteLength=len(indices_blob) + len(vertices_blob) + len(tex_coord_blob) + len(image_blob),
#             )
#         ],
#         samplers=[Sampler(magFilter=NEAREST)] if len(images) > 0 else [],
#         textures=[Texture(source=i, sampler=0) for i, _ in enumerate(images)],
#         images=images,
#     )
#
#     gltf.set_binary_blob(indices_blob + vertices_blob + tex_coord_blob + image_blob)
#
#     return gltf


def img_blob(img: Image) -> bytes:
    return base64.decodebytes(img.uri.split('base64,', maxsplit=1)[1].encode('ascii'))
