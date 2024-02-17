import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {ref, Ref} from 'vue';
import {Document} from '@gltf-transform/core';
import {ModelViewerInfo} from "./viewer/ModelViewerWrapper.vue";

type SceneManagerData = {
    /** When updated, forces the viewer to load a new model replacing the current one */
    viewerSrc: string | null

    /** The model viewer HTML element with all APIs */
    viewer: ModelViewerElement | null
    /** The (hidden) scene of the model viewer */
    viewerScene: ModelScene | null

    /** The currently shown document, which must match the viewerSrc. */
    document: Document | null
}

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    private constructor() {
    }

    /** Creates a new SceneManagerData object */
    static newData(): Ref<SceneManagerData> {
        return ref({
            viewerSrc: null,
            viewer: null,
            viewerScene: null,
            document: null,
        });
    }

    /** Should be called any model finishes loading successfully (after a viewerSrc update) */
    static onload(data: SceneManagerData, info: typeof ModelViewerInfo) {
        console.log("ModelViewer loaded", info);
        data.viewer = info.viewer;
        data.viewerScene = info.scene;
    }
}