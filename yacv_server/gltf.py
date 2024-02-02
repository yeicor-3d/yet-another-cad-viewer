import numpy as np
from pygltflib import *

from tessellate import TessellationUpdate


def create_gltf_from_update(update: TessellationUpdate) -> GLTF2:
    """Create a glTF object from a tessellation update."""
    return create_gltf(
        np.array(list(map(lambda v: [v.X, v.Y, v.Z], update.vertices))),
        np.array(update.indices) if update.indices else None
    )


def create_gltf(vertices: np.ndarray, indices_in: Optional[np.ndarray]) -> GLTF2:
    """Create a glTF object from vertices and optionally indices.

    If indices are not set, vertices are interpreted as line_strip."""

    assert vertices.ndim == 2
    assert vertices.shape[1] == 3
    vertices = vertices  # .astype(np.float16)
    vertices_blob = vertices.tobytes()
    # print(vertices)

    if indices_in is not None:
        assert indices_in.ndim == 2
        assert indices_in.shape[1] == 3
        indices = indices_in  # .astype(np.uint8)
    else:
        indices = np.array(list(map(lambda i: [i, i + 1], range(len(vertices) - 1))), dtype=np.uint8)
    indices_blob = indices.flatten().tobytes()
    # print(indices)

    gltf = GLTF2(
        scene=0,
        scenes=[Scene(nodes=[0])],
        nodes=[Node(mesh=0)],
        meshes=[
            Mesh(
                primitives=[
                    Primitive(
                        attributes=Attributes(POSITION=1),
                        indices=0,
                        mode=TRIANGLES if indices_in is not None else LINE_STRIP
                        # TODO: Also support POINTS mode
                    )
                ]
            )
        ],
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
        ],
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
        ],
        buffers=[
            Buffer(
                byteLength=len(indices_blob) + len(vertices_blob)
            )
        ],
    )

    gltf.set_binary_blob(indices_blob + vertices_blob)
    return gltf
