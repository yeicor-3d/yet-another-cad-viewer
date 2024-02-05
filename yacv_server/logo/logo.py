from OCP.TopoDS import TopoDS_Shape
from build123d import *
from tqdm import tqdm

from tessellate import tessellate, tessellate_count


def build_logo() -> TopoDS_Shape:
    """Builds the CAD part of the logo"""
    with BuildPart() as logo_obj:
        Box(1, 2, 3)
    return logo_obj.part.wrapped


if __name__ == "__main__":
    obj = build_logo()

    for update in tqdm(tessellate(obj.wrapped), total=tessellate_count(obj.wrapped)):
        # print(update.gltf)
        update.gltf.save(f'logo_{update.kind}.glb')  # Will overwrite the file for each update
