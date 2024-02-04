import numpy as np
from pygltflib import *


def create_gltf(vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray, mode: int = TRIANGLES,
                material: Optional[Material] = None, add_checkerboard_image: bool = False) -> GLTF2:
    """Create a glTF object from vertices and optionally indices.

    If indices are not set, vertices are interpreted as line_strip."""

    assert vertices.ndim == 2
    assert vertices.shape[1] == 3
    vertices = vertices.astype(np.float32)
    vertices_blob = vertices.tobytes()
    # print(vertices)

    indices = indices.astype(np.uint8)
    indices_blob = indices.flatten().tobytes()
    # print(indices)

    tex_coord = tex_coord.astype(np.float32)
    tex_coord_blob = tex_coord.tobytes()
    # print(tex_coord)

    image_blob = b''
    if add_checkerboard_image:
        image_blob = base64.decodebytes(
            b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQAQMAAAAlPW0iAAAABlBMVEX'
            b'////MzMw46qqDAAAAEElEQVQImWNg+M+AFeEQBgB+vw/xfUUZkgAAAABJRU5ErkJggg==')

    gltf = GLTF2(
        scene=0,
        scenes=[Scene(nodes=[0])],
        nodes=[Node(mesh=0)],
        meshes=[
            Mesh(
                primitives=[
                    Primitive(
                        attributes=Attributes(POSITION=1, TEXCOORD_0=2) if len(tex_coord) > 0 else Attributes(
                            POSITION=1),
                        indices=0,
                        mode=mode,
                        material=0 if material is not None else None,
                    )
                ]
            )
        ],
        materials=[material] if material is not None else [],
        accessors=[
                      Accessor(
                          bufferView=0,
                          componentType=UNSIGNED_BYTE,
                          count=indices.size,
                          type=SCALAR,
                          max=[int(indices.max())],
                          min=[int(indices.min())],
                      ),
                      Accessor(
                          bufferView=1,
                          componentType=FLOAT,
                          count=len(vertices),
                          type=VEC3,
                          max=vertices.max(axis=0).tolist(),
                          min=vertices.min(axis=0).tolist(),
                      ),
                  ] + ([
                           Accessor(
                               bufferView=2,
                               componentType=FLOAT,
                               count=len(tex_coord),
                               type=VEC2,
                               max=tex_coord.max(axis=0).tolist(),
                               min=tex_coord.min(axis=0).tolist(),
                           )] if len(tex_coord) > 0 else [])
        ,
        bufferViews=[
                        BufferView(
                            buffer=0,
                            byteLength=len(indices_blob),
                            target=ELEMENT_ARRAY_BUFFER,
                        ),
                        BufferView(
                            buffer=0,
                            byteOffset=len(indices_blob),
                            byteLength=len(vertices_blob),
                            target=ARRAY_BUFFER,
                        ),
                    ] + (
                        [
                            BufferView(
                                buffer=0,
                                byteOffset=len(indices_blob) + len(vertices_blob),
                                byteLength=len(tex_coord_blob),
                                target=ARRAY_BUFFER,
                            ),
                        ] if len(tex_coord) > 0 else []) + (
                        [
                            BufferView(
                                buffer=0,
                                byteOffset=len(indices_blob) + len(
                                    vertices_blob) + len(tex_coord_blob),
                                byteLength=len(image_blob),
                            ),
                        ] if add_checkerboard_image else []),
        buffers=[
            Buffer(
                byteLength=len(indices_blob) + len(vertices_blob) + len(tex_coord_blob) + len(image_blob),
            )
        ],
        textures=[Texture(source=0)] if add_checkerboard_image else [],
        images=[Image(bufferView=3, mimeType=IMAGEPNG, )] if add_checkerboard_image else [],
    )

    gltf.set_binary_blob(indices_blob + vertices_blob + tex_coord_blob + image_blob)

    return gltf
