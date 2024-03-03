<script setup lang="ts">
import {onMounted, onUpdated, ref} from "vue";
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import * as OrientationGizmoRaw from "three-orientation-gizmo/src/OrientationGizmo";
import type {ModelViewerElement} from '@google/model-viewer';

// Optimized minimal dependencies from three
import {Vector3} from "three/src/math/Vector3.js";
import {Matrix4} from "three/src/math/Matrix4.js";

globalThis.THREE = {Vector3, Matrix4} as any // HACK: Required for the gizmo to work

const OrientationGizmo = OrientationGizmoRaw.default;

const props = defineProps<{ elem: ModelViewerElement | null, scene: ModelScene }>();

function createGizmo(expectedParent: HTMLElement, scene: ModelScene): HTMLElement {
  // noinspection SpellCheckingInspection
  let gizmo = new OrientationGizmoRaw.default(scene.camera, {
    size: expectedParent.clientWidth,
    bubbleSizePrimary: expectedParent.clientWidth / 12,
    bubbleSizeSeconday: expectedParent.clientWidth / 14,
    fontSize: (expectedParent.clientWidth / 10) + "px"
  });
  // HACK: Swap axes to fake the CAD orientation
  for (let swap of [["y", "-z"], ["z", "-y"], ["z", "-z"]]) {
    let indexA = gizmo.bubbles.findIndex((bubble: any) => bubble.axis == swap[0])
    let indexB = gizmo.bubbles.findIndex((bubble: any) => bubble.axis == swap[1])
    let dirA = gizmo.bubbles[indexA].direction.clone();
    let dirB = gizmo.bubbles[indexB].direction.clone();
    gizmo.bubbles[indexA].direction.copy(dirB);
    gizmo.bubbles[indexB].direction.copy(dirA);
  }
  // Append and listen for events
  gizmo.onAxisSelected = (axis: { direction: { x: any; y: any; z: any; }; }) => {
    let lookFrom = scene.getCamera().position.clone();
    let lookAt = scene.getTarget().clone().add(scene.target.position);
    let magnitude = lookFrom.clone().sub(lookAt).length()
    let direction = new Vector3(axis.direction.x, axis.direction.y, axis.direction.z);
    let newLookFrom = lookAt.clone().add(direction.clone().multiplyScalar(magnitude));
    //console.log("New camera position", newLookFrom)
    scene.getCamera().position.copy(newLookFrom);
    scene.getCamera().lookAt(lookAt);
    if ((scene as any).__perspectiveCamera) { // HACK: Make the hacky ortho also work
      (scene as any).__perspectiveCamera.position.copy(newLookFrom);
      (scene as any).__perspectiveCamera.lookAt(lookAt);
    }
    scene.queueRender();
    requestIdleCallback(() => props.elem?.dispatchEvent(
        new CustomEvent('camera-change', {detail: {source: 'none'}})))
  }
  return gizmo;
}

// Mount, unmount and listen for scene changes
let container = ref<HTMLElement | null>(null);

let gizmo: HTMLElement & { update: () => void }

function updateGizmo() {
  if (gizmo.isConnected) {
    gizmo.update();
    requestIdleCallback(updateGizmo);
  }
}

let reinstall = () => {
  if(!container.value) return;
  if (gizmo) container.value.removeChild(gizmo);
  gizmo = createGizmo(container.value, props.scene as ModelScene) as typeof gizmo;
  container.value.appendChild(gizmo);
  requestIdleCallback(updateGizmo); // Low priority updates
}
onMounted(reinstall)
onUpdated(reinstall);
// onUnmounted is not needed because the gizmo is removed when the container is removed
</script>

<template>
  <div ref="container" class="orientation-gizmo"/>
</template>