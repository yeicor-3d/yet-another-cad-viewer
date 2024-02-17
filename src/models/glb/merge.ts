import {Document, Scene, Transform, WebIO} from "@gltf-transform/core";
import {unpartition} from "@gltf-transform/functions";

let io = new WebIO();

/**
 * Given the bytes of a GLB file and a parsed GLTF document, it parses and merges the GLB into the document.
 *
 * It can replace previous models in the document if the provided name matches the name of a previous model.
 */
export async function merge(glb: Uint8Array, name: string, document: Document): Promise<Document> {

    let newDoc = await io.readBinary(glb);

    // noinspection TypeScriptValidateJSTypes
    // await newDoc.transform(dropByName(name), setNames(name));

    let merged = document.merge(newDoc);

    // noinspection TypeScriptValidateJSTypes
    return await merged.transform(mergeScenes(), unpartition()); // Single scene & buffer required!

}

export async function toBuffer(doc: Document): Promise<Uint8Array> {

    return io.writeBinary(doc);
}

/** Given a parsed GLTF document and a name, it forces the names of all elements to be identified by the name (or derivatives) */
function setNames(name: string): Transform {
    return (doc: Document, _: any) => {
        // Do this automatically for all elements changing any name
        for (let elem of doc.getGraph().listEdges().map(e => e.getChild())) {
            // If setName is available, use it (preserving original names)
            elem.setName(name + "/" + elem.getName());
        }

        // Special cases, specify the kind and number ID of primitives
        let i = 0;
        for (let mesh of doc.getRoot().listMeshes()) {
            for (let prim of mesh.listPrimitives()) {
                let kind = (prim.getMode() === WebGL2RenderingContext.POINTS ? "vertex" :
                    (prim.getMode() === WebGL2RenderingContext.LINES ? "edge" : "face"));
                prim.setName(name + "/" + kind + "/" + (i++));
            }
        }
    }
}

/** Ensures that all elements with the given name are removed from the document */
function dropByName(name: string): Transform {
    return (doc: Document, _: any) => {
        for (let elem of doc.getGraph().listEdges().map(e => e.getChild())) {
            if (elem.getName().startsWith(name + "/") && !(elem instanceof Scene)) {
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
        let scene = root.getDefaultScene();
        for (let dropScene of root.listScenes()) {
            if (dropScene === scene) continue;
            for (let node of dropScene.listChildren()) {
                scene.addChild(node);
            }
            dropScene.dispose();
        }
    }
}
