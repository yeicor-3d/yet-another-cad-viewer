import {Camera} from "three";
import * as OrientationGizmoRaw from "three-orientation-gizmo/src/OrientationGizmo";
import THREE = require("three");
import {OrbitControls} from "three/examples/jsm/controls/OrbitControls";

window.THREE = THREE // HACK: Required for the gizmo to work

export class OrientationGizmo {
    element: OrientationGizmoRaw

    constructor(camera: Camera, controls: OrbitControls) {
        this.element = new OrientationGizmoRaw(camera, {
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
        this.element.onAxisSelected = (axis) => {
            let magnitude = camera.position.clone().sub(controls.target).length()
            let direction = new THREE.Vector3(axis.direction.x, axis.direction.y, axis.direction.z);
            direction.normalize();
            console.log(controls.target, direction, magnitude)
            camera.position.copy(controls.target.clone().add(direction.multiplyScalar(magnitude)));
        }
    }

    install() {
        document.body.appendChild(this.element);
    }

    update() {
        this.element.update();
    }
}