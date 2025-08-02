import {type Ref} from 'vue';
import {Buffer, Document, Scene} from '@gltf-transform/core';
import {extrasNameKey, extrasNameValueHelpers, mergeFinalize, mergePartial, removeModel, toBuffer} from "./gltf";
import {newAxes, newGridBox} from "./helpers";
import {Vector3} from "three/src/math/Vector3.js"
import {Box3} from "three/src/math/Box3.js"
import {Matrix4} from "three/src/math/Matrix4.js"

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    /** Loads a GLB model from a URL and adds it to the viewer or replaces it if the names match */
    static async loadModel(sceneUrl: Ref<string>, document: Document, name: string, url: string | Blob, updateHelpers: boolean = true, reloadScene: boolean = true): Promise<Document> {
        let loadStart = performance.now();
        let loadNetworkEnd: number;

        try {
            // Start merging into the current document, replacing or adding as needed
            document = await mergePartial(url, name, document, () => loadNetworkEnd = performance.now());

            console.log("Model", name, "loaded in", performance.now() - loadNetworkEnd!, "ms after",
                loadNetworkEnd! - loadStart, "ms of transferring data (maybe building the object on the server)");
        } finally {
            if (updateHelpers) {
                // Reload the helpers to fit the new model
                await this.reloadHelpers(sceneUrl, document, reloadScene);
                reloadScene = false;
            }

            if (reloadScene) {
                // Display the final fully loaded model
                let displayStart = performance.now();
                document = await this.showCurrentDoc(sceneUrl, document);
                console.log("Scene displayed in", performance.now() - displayStart, "ms");
            }
        }

        return document;
    }

    static getBoundingBox(document: Document): Box3 | null {
        if (document.getRoot().listNodes().length === 0) return null;
        // Get bounding box of the model and use it to set the size of the helpers
        let bbMin: number[] = [1e6, 1e6, 1e6];
        let bbMax: number[] = [-1e6, -1e6, -1e6];
        document.getRoot().listNodes().forEach(node => {
            if ((node.getExtras()[extrasNameKey] ?? extrasNameValueHelpers) === extrasNameValueHelpers) return;
            let transform = new Matrix4(...node.getWorldMatrix());
            for (let prim of node.getMesh()?.listPrimitives() ?? []) {
                let accessor = prim.getAttribute('POSITION');
                if (!accessor) continue;
                let objMin = new Vector3(...accessor.getMin([0, 0, 0]))
                    .applyMatrix4(transform);
                let objMax = new Vector3(...accessor.getMax([0, 0, 0]))
                    .applyMatrix4(transform);
                bbMin = bbMin.map((v, i) => Math.min(v, objMin.getComponent(i)));
                bbMax = bbMax.map((v, i) => Math.max(v, objMax.getComponent(i)));
            }
        });
        let bbSize = new Vector3().fromArray(bbMax).sub(new Vector3().fromArray(bbMin));
        let bbCenter = new Vector3().fromArray(bbMin).add(bbSize.clone().multiplyScalar(0.5));
        return new Box3().setFromCenterAndSize(bbCenter, bbSize);
    }

    /** Removes a model from the viewer */
    static async removeModel(sceneUrl: Ref<string>, document: Document, name: string, updateHelpers: boolean = true, reloadScene: boolean = true): Promise<Document> {
        let loadStart = performance.now();

        // Remove the model from the document
        document = await removeModel(name, document)

        console.log("Model", name, "removed in", performance.now() - loadStart, "ms");

        if (updateHelpers) {
            // Reload the helpers to fit the new model (will also show the document)
            document = await this.reloadHelpers(sceneUrl, document, reloadScene);
        }

        return document;
    }

    private static async reloadHelpers(sceneUrl: Ref<string>, document: Document, reloadScene: boolean): Promise<Document> {
        let bb = SceneMgr.getBoundingBox(document);
        if (!bb) return document; // Empty document, no helpers to show

        // If only the helpers remain, go back to the empty scene
        let noOtherModels = true;
        for (let elem of document.getGraph().listEdges().map(e => e.getChild())) {
            if (elem.getExtras() && !(elem instanceof Scene) && !(elem instanceof Buffer) &&
                elem.getExtras()[extrasNameKey] !== extrasNameValueHelpers) {
                // There are other elements in the document, so we can show the helpers
                noOtherModels = false;
                break;
            }
        }
        if (noOtherModels) return await removeModel(extrasNameValueHelpers, document);

        // Create the helper axes and grid box
        let helpersDoc = new Document();
        let transform = (new Matrix4()).makeTranslation(bb.getCenter(new Vector3()));
        newAxes(helpersDoc, bb.getSize(new Vector3()).multiplyScalar(0.5), transform);
        newGridBox(helpersDoc, bb.getSize(new Vector3()), transform);
        let helpersUrl = URL.createObjectURL(new Blob([await toBuffer(helpersDoc) as ArrayBufferView<ArrayBuffer>]));
        let newDocument = await SceneMgr.loadModel(sceneUrl, document, extrasNameValueHelpers, helpersUrl, false, reloadScene);
        URL.revokeObjectURL(helpersUrl);
        return newDocument;
    }

    /** Serializes the current document into a GLB and updates the viewerSrc */
    private static async showCurrentDoc(sceneUrl: Ref<string>, document: Document): Promise<Document> {
        // Make sure the document is fully loaded and ready to be shown
        document = await mergeFinalize(document);

        // Serialize the document into a GLB and update the viewerSrc
        let buffer = await toBuffer(document);
        let blob = new Blob([buffer as ArrayBufferView<ArrayBuffer>], {type: 'model/gltf-binary'});
        console.debug("Showing current doc", document, "with", buffer.length, "total bytes");
        if (sceneUrl.value.startsWith("blob:")) URL.revokeObjectURL(sceneUrl.value);
        sceneUrl.value = URL.createObjectURL(blob);

        return document;
    }
}