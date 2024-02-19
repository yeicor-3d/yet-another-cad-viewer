import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {Ref, ref} from 'vue';
import {Document} from '@gltf-transform/core';
import {ModelViewerInfo} from "./viewer/ModelViewerWrapper.vue";
import {mergeFinalize, mergePartial, toBuffer} from "../models/glb/merge";

export type SceneMgrRefData = {
    /** When updated, forces the viewer to load a new model replacing the current one */
    viewerSrc: string | null

    /** The model viewer HTML element with all APIs */
    viewer: ModelViewerElement | null
    /** The (hidden) scene of the model viewer */
    viewerScene: ModelScene | null
}

export type SceneMgrData = {
    /** The currently shown document, which must match the viewerSrc. */
    document: Document
}

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    private constructor() {
    }

    /** Creates a new SceneManagerData object */
    static newData(): [Ref<SceneMgrRefData>, SceneMgrData] {
        let refData: any = ref({
            viewerSrc: null,
            viewer: null,
            viewerScene: null,
        });
        let data = {
            document: new Document()
        };
        // newVar.value.document.createScene("scene");
        // this.showCurrentDoc(newVar.value).then(r => console.log("Initial empty model loaded"));
        return [refData, data];
    }

    /** Loads a GLB/GLBS model from a URL and adds it to the viewer or replaces it if the names match */
    static async loadModel(refData: Ref<SceneMgrRefData>, data: SceneMgrData, name: string, url: string) {
        let loadStart = performance.now();

        // Connect to the URL of the model
        let response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch model: " + response.statusText);

        // Start merging into the current document, replacing or adding as needed
        let glb = new Uint8Array(await response.arrayBuffer());
        data.document = await mergePartial(glb, name, data.document);

        // Display the final fully loaded model
        await this.showCurrentDoc(refData, data);

        console.log("Model", name, "loaded in", performance.now() - loadStart, "ms");
    }

    /** Serializes the current document into a GLB and updates the viewerSrc */
    private static async showCurrentDoc(refData: Ref<SceneMgrRefData>, data: SceneMgrData) {
        data.document = await mergeFinalize(data.document);
        let buffer = await toBuffer(data.document);
        let blob = new Blob([buffer], {type: 'model/gltf-binary'});
        console.log("Showing current doc", data.document, "as", Array.from(buffer));
        refData.value.viewerSrc = URL.createObjectURL(blob);
    }

    /** Should be called any model finishes loading successfully (after a viewerSrc update) */
    static onload(data: SceneMgrRefData, info: typeof ModelViewerInfo) {
        console.log("ModelViewer loaded", info);
        data.viewer = info.viewer;
        data.viewerScene = info.scene;
    }
}