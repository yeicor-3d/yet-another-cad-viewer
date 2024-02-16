import { WebIO } from "@gltf-transform/core";

// /**
//  * Given a stream of binary data (e.g. from a fetch response), load a GLBS file (or simply a GLB file) and automatically
//  * merge them into a single GLB file. progress is a callback that is called with the document after each step of the
//  * loading process.
//  */
// export async function loadAndMerge(blob: Uint8Array, document: Document, progress: (doc: Document, pct: number) => Promise<void>): Promise<Document> {
//     // Identify the type of file by loading the first 4 bytes.
//     let magicNumbers = []
//     const [headerReader, mainReader] = reader.tee()
//     let headerReaderImpl = headerReader.getReader({mode: 'byob'});
//     try {
//         const header = new Uint8Array(4);
//         await headerReaderImpl.read(header)
//         magicNumbers = Array.from(header)
//     } catch (e) {
//         console.error(e);
//     } finally {
//         await headerReaderImpl.cancel()
//     }
//     // Depending on the file type, merge the GLB or GLBS files.
//     let finalDocument: Document;
//     if (magicNumbers[0] === '{'.charCodeAt(0)) { // GLTF
//         finalDocument = await mergeGltf(mainReader, document);
//     } else if (magicNumbers === "glTF".split('').map(c => c.charCodeAt(0))) { // GLB
//         finalDocument = await mergeGlb(mainReader, document);
//     } else if (magicNumbers === "glTF".split('').map(c => c.charCodeAt(0))) { // GLBS
//         finalDocument = await mergeGlbs(mainReader, document);
//     } else {
//         throw new Error('Unknown file type (not GLTF, GLB, or GLBS, magic numbers: ' + magicNumbers + ')');
//     }
//     return finalDocument
// }
//
// function mergeGlb(blob: Uint8Array, document: Document): Promise<Document> {
//     new WebIO().readAsJSON()
// }