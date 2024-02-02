from build123d import *

from gltf import create_gltf_from_update
from tessellate import tessellate, TessellationUpdate


def logo() -> Compound:
    """Builds the CAD part of the logo"""
    with BuildPart() as logo_obj:
        Box(1, 2, 3)
    return logo_obj.part


if __name__ == "__main__":
    obj = logo()


    def progress(update: TessellationUpdate):
        gltf = create_gltf_from_update(update)
        print(gltf)
        if update.is_face:
            gltf.save("logo_face.glb")
        else:
            gltf.save("logo_edge.glb")


    tessellate(obj.wrapped, progress)
