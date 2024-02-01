from build123d import *

from tessellate import tessellate


def logo() -> Compound:
    """Builds the CAD part of the logo"""
    with BuildPart() as logo_obj:
        Box(1, 2, 3)
    return logo_obj.part


if __name__ == "__main__":
    obj = logo()
    tessellate(obj.wrapped, lambda *args: print(args))
