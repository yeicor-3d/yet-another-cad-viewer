import {Buffer, Document, Scene, type Transform, WebIO} from "@gltf-transform/core";
import {unpartition, mergeDocuments} from "@gltf-transform/functions";

let io = new WebIO();
export let extrasNameKey = "__yacv_name";
export let extrasNameValueHelpers = "__helpers";

/**
 * Loads a GLB model from a URL and adds it to the document or replaces it if the names match.
 *
 * It can replace previous models in the document if the provided name matches the name of a previous model.
 *
 * Remember to call mergeFinalize after all models have been merged (slower required operations).
 */
export async function mergePartial(url: string, name: string, document: Document, networkFinished: () => void = () => {
}): Promise<Document> {
    // Fetch the complete document from the network
    // This could be done at the same time as the document is being processed, but I wanted better metrics
    let response = await fetch(url);
    let buffer = await response.arrayBuffer();
    networkFinished();

    // Load the new document
    let newDoc = null;
    let alreadyTried: { [name: string]: boolean } = {}
    while (newDoc == null) { // Retry adding extensions as required until the document is loaded
        try { // Try to load fast if no extensions are used
            newDoc = await io.readBinary(new Uint8Array(buffer));
        } catch (e) { // Fallback to wait for download and register big extensions
            if (e instanceof Error && e.message.toLowerCase().includes("khr_draco_mesh_compression")) {
                if (alreadyTried["draco"]) throw e; else alreadyTried["draco"] = true;
                // WARNING: Draco decompression on web is really slow for non-trivial models! (it should work?)
                let {KHRDracoMeshCompression} = await import("@gltf-transform/extensions")
                let dracoDecoderWeb = await import("three/examples/jsm/libs/draco/draco_decoder.js");
                let dracoEncoderWeb = await import("three/examples/jsm/libs/draco/draco_encoder.js");
                io.registerExtensions([KHRDracoMeshCompression])
                    .registerDependencies({
                        'draco3d.decoder': await dracoDecoderWeb.default({}),
                        'draco3d.encoder': await dracoEncoderWeb.default({})
                    });
            } else if (e instanceof Error && e.message.toLowerCase().includes("ext_texture_webp")) {
                if (alreadyTried["webp"]) throw e; else alreadyTried["webp"] = true;
                let {EXTTextureWebP} = await import("@gltf-transform/extensions")
                io.registerExtensions([EXTTextureWebP]);
            } else { // TODO: Add more extensions as required
                throw e;
            }
        }
    }

    // Remove any previous model with the same name
    await document.transform(dropByName(name));

    // Ensure consistent names
    // noinspection TypeScriptValidateJSTypes
    await newDoc.transform(setNames(name));

    // Merge the new document into the current one
    mergeDocuments(document, newDoc);
    return document;
}

export async function mergeFinalize(document: Document): Promise<Document> {
    // Single scene & buffer required before loading & rendering
    return await document.transform(mergeScenes(), unpartition());
}

export async function toBuffer(doc: Document): Promise<Uint8Array> {
    return io.writeBinary(doc);
}

export async function removeModel(name: string, document: Document): Promise<Document> {
    return await document.transform(dropByName(name));
}

/** Given a parsed GLTF document and a name, it forces the names of all elements to be identified by the name (or derivatives) */
function setNames(name: string): Transform {
    return (doc: Document) => {
        // Do this automatically for all elements changing any name
        for (let elem of doc.getGraph().listEdges().map(e => e.getChild())) {
            if (!elem.getExtras()) elem.setExtras({});
            elem.getExtras()[extrasNameKey] = name;
        }
        return doc;
    }
}

/** Ensures that all elements with the given name are removed from the document */
function dropByName(name: string): Transform {
    return (doc: Document) => {
        for (let elem of doc.getGraph().listEdges().map(e => e.getChild())) {
            if (elem.getExtras() == null || elem instanceof Scene || elem instanceof Buffer) continue;
            if ((elem.getExtras()[extrasNameKey]?.toString() ?? "") == name) {
                elem.dispose();
            }
        }
        return doc;
    };
}


/** Merges all scenes in the document into a single default scene */
function mergeScenes(): Transform {
    return (doc: Document) => {
        let root = doc.getRoot();
        let scene = root.getDefaultScene() ?? root.listScenes()[0];
        for (let dropScene of root.listScenes()) {
            if (dropScene === scene) continue;
            for (let node of dropScene.listChildren()) {
                scene.addChild(node);
            }
            dropScene.dispose();
        }
    }
}
