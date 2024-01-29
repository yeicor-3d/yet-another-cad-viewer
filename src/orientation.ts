import * as OrientationGizmoRaw from "three-orientation-gizmo/src/OrientationGizmo";
import * as THREE from "three";
import {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";

window.THREE = THREE // HACK: Required for the gizmo to work

export class OrientationGizmo {
    element: OrientationGizmoRaw

    constructor(scene: ModelScene) {
        // noinspection SpellCheckingInspection
        this.element = new OrientationGizmoRaw(scene.camera, {
            size: 120,
            bubbleSizePrimary: 12,
            bubbleSizeSeconday: 10,
            fontSize: "14px"
        });
        // Place in the top right corner
        this.element.style.position = "absolute";
        this.element.style.top = "0px";
        this.element.style.right = "0px";
        this.element.style.zIndex = "1000";
        // HACK: Swap axes to match A-Frame
        for (let swap of [["y", "-z"], ["z", "-y"], ["z", "-z"]]) {
            let indexA = this.element.bubbles.findIndex((bubble) => bubble.axis == swap[0])
            let indexB = this.element.bubbles.findIndex((bubble) => bubble.axis == swap[1])
            let dirA = this.element.bubbles[indexA].direction.clone();
            let dirB = this.element.bubbles[indexB].direction.clone();
            this.element.bubbles[indexA].direction.copy(dirB);
            this.element.bubbles[indexB].direction.copy(dirA);
        }
        // Append and listen for events
        this.element.onAxisSelected = (axis: { direction: { x: any; y: any; z: any; }; }) => {
            let lookFrom = scene.getCamera().position.clone();
            let lookAt = scene.getTarget().clone().add(scene.target.position);
            let magnitude = lookFrom.clone().sub(lookAt).length()
            let direction = new THREE.Vector3(axis.direction.x, axis.direction.y, axis.direction.z);
            let newLookFrom = lookAt.clone().add(direction.clone().multiplyScalar(magnitude));
            //console.log("New camera position", newLookFrom)
            scene.getCamera().position.copy(newLookFrom);
            scene.getCamera().lookAt(lookAt);
            scene.queueRender();
        }
    }

    install() {
        document.body.appendChild(this.element);
    }

    update() {
        this.element.update();
    }
}