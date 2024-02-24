import {Ref, ShallowRef} from 'vue';
import {Document} from '@gltf-transform/core';
import {mergeFinalize, mergePartial, removeModel, toBuffer} from "./gltf";

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    /** Loads a GLB model from a URL and adds it to the viewer or replaces it if the names match */
    static async loadModel(sceneUrl: Ref<string>, document: ShallowRef<Document>, name: string, url: string) {
        let loadStart = performance.now();

        // Start merging into the current document, replacing or adding as needed
        document.value = await mergePartial(url, name, document.value);

        // Display the final fully loaded model
        await this.showCurrentDoc(sceneUrl, document);

        console.log("Model", name, "loaded in", performance.now() - loadStart, "ms");
        return document;
    }

    /** Removes a model from the viewer */
    static async removeModel(sceneUrl: Ref<string>, document: ShallowRef<Document>, name: string) {
        let loadStart = performance.now();

        // Remove the model from the document
        document.value = await removeModel(name, document.value)

        // Display the final fully loaded model
        await this.showCurrentDoc(sceneUrl, document);

        console.log("Model", name, "removed in", performance.now() - loadStart, "ms");
        return document;
    }

    /** Serializes the current document into a GLB and updates the viewerSrc */
    private static async showCurrentDoc(sceneUrl: Ref<string>, document: ShallowRef<Document>) {
        // Make sure the document is fully loaded and ready to be shown
        document.value = await mergeFinalize(document.value);

        // Serialize the document into a GLB and update the viewerSrc
        let buffer = await toBuffer(document.value);
        let blob = new Blob([buffer], {type: 'model/gltf-binary'});
        console.debug("Showing current doc", document, "as", Array.from(buffer));
        sceneUrl.value = URL.createObjectURL(blob);
    }
}