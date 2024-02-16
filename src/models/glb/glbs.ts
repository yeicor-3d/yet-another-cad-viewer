export type SplitGlbsResult = {
    numChunks: number;
    glbReader: ReadableStream<Uint8Array>;
}

/**
 * Given a stream of binary data (e.g. from a fetch response), splits a GLBS file into its component GLB files and
 * returns them as a stream of Uint8Arrays with known lengths. It also supports simple GLB files by returning itself.
 */
export async function splitGlbs(reader: ReadableStream<Uint8Array>): Promise<SplitGlbsResult> {
    // Create a transform stream that splits the GLBS file into its component GLB files by reading the length of each
    // chunk and then reading that many bytes from the input stream.
    let buffer4Bytes = new Uint8Array(4);
    let readerImpl = reader.getReader({mode: 'byob'});
    await readerImpl.read(buffer4Bytes);
    if (buffer4Bytes[0] === '{'.charCodeAt(0) || Array.from(buffer4Bytes) === "glTF".split('').map(c => c.charCodeAt(0))) {
        return {numChunks: 1, glbReader: await singleBlob(reader)}
    }
    let isGlbs = Array.from(buffer4Bytes) === "GLBS".split('').map(c => c.charCodeAt(0));
    if (!isGlbs) throw new Error('Invalid magic numbers for expected GLBS file: ' + buffer4Bytes);
    // Create a new readable stream that splits the GLBS file into its component GLB files by reading the length of each
    // chunk and then reading that many bytes from the input stream.
    // - But first, we read the number of chunks (can be 0xFFFFFFFF if the number of chunks is unknown).
    await readerImpl.read(buffer4Bytes);
    let numChunks = new DataView(buffer4Bytes.buffer).getUint32(0, true);
    return {
        numChunks,
        // - Then, we read the length of each chunk followed by the chunk itself.
        glbReader: new ReadableStream<Uint8Array>({
            async start(controller) {
                for (let i = 0; i < numChunks; i++) {
                    // - Read length
                    let {done} = await readerImpl.read(buffer4Bytes);
                    if (done) {
                        if (numChunks != 0xFFFFFFFF) throw new Error('Unexpected end of stream while reading chunk length');
                        else break // We reached the end of the stream of unknown length, so we stop reading chunks.
                    }
                    let length = new DataView(buffer4Bytes.buffer).getUint32(0, true);
                    // - Read chunk
                    let chunkReader = await singleBlob(reader, length);
                    let {value: fullChunk} = await chunkReader.getReader().read();
                    controller.enqueue(fullChunk);
                }
                controller.close();
            }
        })
    };
}

async function singleBlob(reader: ReadableStream<Uint8Array>, stopAfter: number | null = null): Promise<ReadableStream<Uint8Array>> {
    // Make sure the reader reads the entire stream at once.
    const readerImpl = reader.getReader();
    let bufferedChunks: Uint8Array = new Uint8Array();
    let done = false;
    let length = 0;
    while (!done) {
        let {value, done: d} = await readerImpl.read();
        if (value) {
            // TODO: This is inefficient. We should be able to avoid copying the buffer each time. byob?
            let oldBuffer = bufferedChunks;
            let newLength = bufferedChunks.length + value.length;
            if (stopAfter !== null && newLength > stopAfter) {
                newLength = stopAfter;
                value = value.slice(0, stopAfter - bufferedChunks.length);
            }
            bufferedChunks = new Uint8Array(newLength);
            bufferedChunks.set(oldBuffer);
            bufferedChunks.set(value, length);
            length += value.length;
        }
        done = d;
    }
    return new ReadableStream<Uint8Array>({
        start(controller) {
            controller.enqueue(bufferedChunks);
            controller.close();
        }
    });
}
