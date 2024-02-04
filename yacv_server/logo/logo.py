from build123d import *
from tqdm import tqdm

from tessellate import tessellate, tessellate_count


def logo() -> Compound:
    """Builds the CAD part of the logo"""
    with BuildPart() as logo_obj:
        Box(1, 2, 3)
    return logo_obj.part


if __name__ == "__main__":
    obj = logo()

    for update in tqdm(tessellate(obj.wrapped), total=tessellate_count(obj.wrapped)):
        # print(update.gltf)
        update.gltf.save(f'logo_{update.kind}.glb')  # Will overwrite the file for each update
