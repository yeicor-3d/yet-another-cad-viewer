import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {Ref} from 'vue';
import {Document} from '@gltf-transform/core';
import {mergeFinalize, mergePartial, toBuffer} from "./gltf";

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    /** Loads a GLB model from a URL and adds it to the viewer or replaces it if the names match */
    static async loadModel(sceneUrl: Ref<string>, document: Document, name: string, url: string): Promise<Document> {
        let loadStart = performance.now();

        // Start merging into the current document, replacing or adding as needed
        document = await mergePartial(url, name, document);

        // Display the final fully loaded model
        document = await this.showCurrentDoc(sceneUrl, document);

        console.log("Model", name, "loaded in", performance.now() - loadStart, "ms");
        return document;
    }

    /** Serializes the current document into a GLB and updates the viewerSrc */
    private static async showCurrentDoc(sceneUrl: Ref<string>, document: Document): Promise<Document> {
        // Make sure the document is fully loaded and ready to be shown
        document = await mergeFinalize(document);

        // Serialize the document into a GLB and update the viewerSrc
        let buffer = await toBuffer(document);
        let blob = new Blob([buffer], {type: 'model/gltf-binary'});
        //console.log("Showing current doc", document, "as", Array.from(buffer));
        sceneUrl.value = URL.createObjectURL(blob);

        // Return the updated document
        return document;
    }
}