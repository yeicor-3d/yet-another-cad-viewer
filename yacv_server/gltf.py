import numpy as np
from pygltflib import *

_checkerboard_image = Image(uri='data:image/png;base64,'
                                'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVQI12N49OjR////Gf'
                                '/////48WMATwULS8tcyj8AAAAASUVORK5CYII=')


def create_gltf(vertices: np.ndarray, indices: np.ndarray, tex_coord: np.ndarray, mode: int = TRIANGLES,
                material: Optional[Material] = None, images: Optional[List[Image]] = None) -> GLTF2:
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

    if images is None:
        images = []
    image_blob = b''
    image_blob_pointers = []
    for img in images:
        assert img.bufferView is None
        assert img.uri is not None
        assert img.uri.startswith('data:')
        image_blob_pointers.append(len(image_blob))
        image_blob += base64.decodebytes(img.uri.split('base64,', maxsplit=1)[1].encode('ascii'))
        img.mimeType = img.uri.split(';', maxsplit=1)[0].split(':', maxsplit=1)[1]
        img.uri = None
        img.bufferView = 3 + len(image_blob_pointers) - 1

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
                                    vertices_blob) + len(tex_coord_blob) + image_blob_pointers[i],
                                byteLength=image_blob_pointers[i + 1] - image_blob_pointers[i] if i + 1 < len(
                                    image_blob_pointers) else len(image_blob) - image_blob_pointers[i],
                            )
                            for i, img in enumerate(images)
                        ] if len(images) > 0 else []),
        buffers=[
            Buffer(
                byteLength=len(indices_blob) + len(vertices_blob) + len(tex_coord_blob) + len(image_blob),
            )
        ],
        samplers=[Sampler(magFilter=NEAREST, minFilter=NEAREST_MIPMAP_NEAREST)] if len(images) > 0 else [],
        textures=[Texture(source=i, sampler=0) for i, _ in enumerate(images)],
        images=images,
    )

    gltf.set_binary_blob(indices_blob + vertices_blob + tex_coord_blob + image_blob)

    return gltf
