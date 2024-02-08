from typing import AsyncGenerator


async def glb_sequence_to_glbs(glb_sequence: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
    """Converts a sequence of GLB files into a single GLBS file.

    This is a streaming response in the custom GLBS format which consists of the "GLBS" magic text followed by
    a sequence of GLB files, each with a 4-byte little-endian length prefix."""

    # Write the magic text
    yield b'GLBS'

    # Write the GLB files
    async for glb in glb_sequence:
        # Write the length prefix
        yield len(glb).to_bytes(4, 'little')
        # Write the GLB file
        yield glb


if __name__ == '__main__':
    import asyncio

    async def test_glb_sequence_to_glbs():
        async def glb_sequence():
            yield b'glb00001'
            yield b'glb2'

        async for chunk in glb_sequence_to_glbs(glb_sequence()):
            print(chunk)

    asyncio.run(test_glb_sequence_to_glbs())