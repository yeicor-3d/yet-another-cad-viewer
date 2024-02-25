import {Ref, ShallowRef} from 'vue';
import {Document} from '@gltf-transform/core';
import {extrasNameKey, mergeFinalize, mergePartial, removeModel, toBuffer} from "./gltf";
import {newAxes, newGridBox} from "./helpers";
import {Matrix4, Vector3} from 'three';

/** This class helps manage SceneManagerData. All methods are static to support reactivity... */
export class SceneMgr {
    /** Loads a GLB model from a URL and adds it to the viewer or replaces it if the names match */
    static async loadModel(sceneUrl: Ref<string>, document: ShallowRef<Document>, name: string, url: string) {
        let loadStart = performance.now();

        // Start merging into the current document, replacing or adding as needed
        document.value = await mergePartial(url, name, document.value);

        if (name !== "__helpers") {
            // Reload the helpers to fit the new model
            await this.reloadHelpers(sceneUrl, document);
        } else {
            // Display the final fully loaded model
            await this.showCurrentDoc(sceneUrl, document);
        }

        console.log("Model", name, "loaded in", performance.now() - loadStart, "ms");

        return document;
    }

    private static async reloadHelpers(sceneUrl: Ref<string>, document: ShallowRef<Document>) {
        // Get bounding box of the model and use it to set the size of the helpers
        let bbMin: number[] = [1e6, 1e6, 1e6];
        let bbMax: number[] = [-1e6, -1e6, -1e6];
        document.value.getRoot().listNodes().forEach(node => {
            if ((node.getExtras()[extrasNameKey] ?? "__helpers") === "__helpers") return;
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
        let bbTransform = new Matrix4().makeTranslation(bbCenter.x, bbCenter.y, bbCenter.z);

        // Create the helper axes and grid box
        let helpersDoc = new Document();
        newAxes(helpersDoc, bbSize.clone().multiplyScalar(0.5), bbTransform);
        newGridBox(helpersDoc, bbSize, bbTransform);
        let helpersUrl = URL.createObjectURL(new Blob([await toBuffer(helpersDoc)]));
        await SceneMgr.loadModel(sceneUrl, document, "__helpers", helpersUrl);
    }

    /** Removes a model from the viewer */
    static async removeModel(sceneUrl: Ref<string>, document: ShallowRef<Document>, name: string) {
        let loadStart = performance.now();

        // Remove the model from the document
        document.value = await removeModel(name, document.value)

        console.log("Model", name, "removed in", performance.now() - loadStart, "ms");

        // Reload the helpers to fit the new model (will also show the document)
        await this.reloadHelpers(sceneUrl, document);

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