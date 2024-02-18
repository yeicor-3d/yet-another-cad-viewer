import numpy as np
from build123d import Vector
from pygltflib import *

_checkerboard_image_bytes = base64.decodebytes(
    b'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVQI12N49OjR////Gf'
    b'/////48WMATwULS8tcyj8AAAAASUVORK5CYII=')


class GLTFMgr:
    """A utility class to build our GLTF2 objects easily and incrementally"""

    gltf: GLTF2 = GLTF2(
        scenes=[Scene(nodes=[0])],
        nodes=[Node(mesh=0)],
        meshes=[Mesh(primitives=[])],
        accessors=[],
        bufferViews=[
            BufferView(buffer=0, byteLength=len(_checkerboard_image_bytes), byteOffset=0, target=ELEMENT_ARRAY_BUFFER)],
        buffers=[Buffer(byteLength=len(_checkerboard_image_bytes))],
        samplers=[Sampler(magFilter=NEAREST)],
        textures=[Texture(source=0, sampler=0)],
        images=[Image(bufferView=0, mimeType='image/png')],
        materials=[Material(pbrMetallicRoughness=PbrMetallicRoughness(baseColorTexture=TextureInfo(index=0)))],
    )

    def __init__(self):
        self.gltf.set_binary_blob(_checkerboard_image_bytes)

    def add_face(self, vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray):
        """Add a face to the GLTF as a new primitive of the unique mesh"""
        self._add_any(vertices, indices, tex_coord, mode=TRIANGLES)

    def add_edge(self, vertices: np.ndarray):
        """Add an edge to the GLTF as a new primitive of the unique mesh"""
        indices = np.array(list(map(lambda i: [i, i + 1], range(len(vertices) - 1))), dtype=np.uint8)
        tex_coord = np.array([[i / (len(vertices) - 1), 0] for i in range(len(vertices))], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=LINE_STRIP)

    def add_vertex(self, vertex: Vector):
        """Add a vertex to the GLTF as a new primitive of the unique mesh"""
        vertices = np.array([[vertex.X, vertex.Y, vertex.Z]])
        indices = np.array([0], dtype=np.uint8)
        tex_coord = np.array([[0, 0]], dtype=np.float32)
        self._add_any(vertices, indices, tex_coord, mode=POINTS)

    def _add_any(self, vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray, mode: int = TRIANGLES):
        assert vertices.ndim == 2
        assert vertices.shape[1] == 3
        vertices = vertices.astype(np.float32)
        vertices_blob = vertices.tobytes()

        indices = indices.astype(np.uint8)
        indices_blob = indices.flatten().tobytes()

        tex_coord = tex_coord.astype(np.float32)
        tex_coord_blob = tex_coord.tobytes()

        accessor_base = len(self.gltf.accessors)
        self.gltf.meshes[0].primitives.append(
            Primitive(
                attributes=Attributes(POSITION=accessor_base + 1, TEXCOORD_0=accessor_base + 2),
                indices=accessor_base,
                mode=mode,
                material=0,  # TODO special selected material and face/edge/vertex default materials
            )
        )

        buffer_view_base = len(self.gltf.bufferViews)
        self.gltf.accessors.extend([
            Accessor(
                bufferView=buffer_view_base,
                componentType=UNSIGNED_BYTE,
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
            )
        ])

        binary_blob = self.gltf.binary_blob()
        binary_blob_base = len(binary_blob)
        self.gltf.bufferViews.extend([
            BufferView(
                buffer=0,
                byteOffset=binary_blob_base,
                byteLength=len(indices_blob),
                target=ELEMENT_ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=binary_blob_base + len(indices_blob),
                byteLength=len(vertices_blob),
                target=ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=binary_blob_base + len(indices_blob) + len(vertices_blob),
                byteLength=len(tex_coord_blob),
                target=ARRAY_BUFFER,
            )
        ])

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
