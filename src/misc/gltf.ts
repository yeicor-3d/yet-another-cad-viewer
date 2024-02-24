import {Document, Scene, Transform, WebIO, Buffer} from "@gltf-transform/core";
import {unpartition} from "@gltf-transform/functions";

let io = new WebIO();
export let extrasNameKey = "__yacv_name";

/**
 * Loads a GLB model from a URL and adds it to the document or replaces it if the names match.
 *
 * It can replace previous models in the document if the provided name matches the name of a previous model.
 *
 * Remember to call mergeFinalize after all models have been merged (slower required operations).
 */
export async function mergePartial(url: string, name: string, document: Document): Promise<Document> {
    // Load the new document
    let newDoc = await io.read(url);

    // Remove any previous model with the same name and ensure consistent names
    // noinspection TypeScriptValidateJSTypes
    await newDoc.transform(dropByName(name), setNames(name));

    // Merge the new document into the current one
    return document.merge(newDoc);
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
    return (doc: Document, _: any) => {
        // Do this automatically for all elements changing any name
        for (let elem of doc.getGraph().listEdges().map(e => e.getChild())) {
            if (!elem.getExtras()) elem.setExtras({});
            elem.getExtras()[extrasNameKey] = name;
        }
    }
}

/** Ensures that all elements with the given name are removed from the document */
export function dropByName(name: string): Transform {
    return (doc: Document, _: any) => {
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
