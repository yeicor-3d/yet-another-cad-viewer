const textDecoder = new TextDecoder();

/**
 * Given a stream of binary data (e.g. from a fetch response), splits a GLBS file into its component GLB files and
 * returns them as a generator of Uint8Arrays (that starts with the expected length).
 * It also supports simple GLB files (no splitting needed).
 */
export async function* splitGlbs(readerSrc: ReadableStream<Uint8Array>): AsyncGenerator<number | Uint8Array> {
    let reader = readerSrc.getReader();
    let [buffer4Bytes, buffered] = await readN(reader, new Uint8Array(), 4);
    console.assert(buffer4Bytes.length === 4, 'Expected 4 bytes for magic numbers')
    let magic = textDecoder.decode(buffer4Bytes)
    if (magic === 'glTF' /* GLB */ || magic[0] == '{' /* glTF */) {
        yield 1
        let remaining = await readAll(reader, buffered);
        // Add back the header to the beginning of the document
        let finalBuffer = new Uint8Array(buffer4Bytes.length + remaining.length);
        finalBuffer.set(buffer4Bytes);
        finalBuffer.set(remaining, buffer4Bytes.length);
        yield finalBuffer
    } else if (magic === "GLBS") {
        // First, we read the number of chunks (can be 0xFFFFFFFF if the number of chunks is unknown).
        [buffer4Bytes, buffered] = await readN(reader, buffered, 4);
        let numChunks = new DataView(buffer4Bytes.buffer).getUint32(0, true);
        yield numChunks
        // Then, we read the length of each chunk followed by the chunk itself.
        for (let i = 0; i < numChunks; i++) {
            // - Read length
            [buffer4Bytes, buffered] = await readN(reader, buffered, 4);
            if (buffer4Bytes.length === 0) {
                if (numChunks != 0xFFFFFFFF) throw new Error('Unexpected end of stream while reading chunk length:'+
                    ' expected ' + (numChunks - i) + ' more chunks');
                else break // We reached the end of the stream of unknown length, so we stop reading chunks.
            }
            let length = new DataView(buffer4Bytes.buffer).getUint32(0, true);
            // - Read chunk
            let chunk: Uint8Array
            [chunk, buffered] = await readN(reader, buffered, length);
            yield chunk
        }
    } else throw new Error('Invalid magic numbers for expected GLB/GLBS file: ' + magic);
    reader.releaseLock()
}

/**
 * Reads up to `n` bytes from the reader and returns them as a Uint8Array.
 * An over-read is possible, in which case the returned array will still have `n` bytes and the over-read bytes will be
 * returned. They should be provided to the next call to `readN` to avoid losing data.
 */
async function readN(reader: ReadableStreamDefaultReader<Uint8Array>, buffered: Uint8Array, n: number | null = null): Promise<[Uint8Array, Uint8Array]> {
    let buffer = buffered;
    while (n === null || buffer.length < n) {
        let {done, value} = await reader.read();
        if (done) break;
        let newBuffer = new Uint8Array(buffer.length + value.length);
        newBuffer.set(buffer);
        newBuffer.set(value, buffer.length);
        buffer = newBuffer;
    }
    if (n !== null) {
        return [buffer.slice(0, n), buffer.slice(n)]
    } else {
        return [buffer, new Uint8Array()];
    }
}

async function readAll(reader: ReadableStreamDefaultReader<Uint8Array>, buffered: Uint8Array): Promise<Uint8Array> {
    return (await readN(reader, buffered, null))[0];
}
