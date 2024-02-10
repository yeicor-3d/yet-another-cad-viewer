<script setup lang="ts">
import {VBtn, VIcon} from "vuetify/lib/components";
import {ref} from "vue";
import OrientationGizmo from "./OrientationGizmo.vue";
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {OrthographicCamera} from "three";

const props = defineProps({
  modelViewerInfo: Object
});


function syncOrthoCamera(force: boolean) {
  if (!props.modelViewerInfo) return;
  let scene: ModelScene = props.modelViewerInfo.scene
  let perspectiveCam = (scene as any).__perspectiveCamera;
  if (force || perspectiveCam && scene.camera != perspectiveCam) {
    // Get zoom level from perspective camera
    let dist = scene.getTarget().distanceToSquared(perspectiveCam.position);
    let w = scene.aspect * dist ** 1.1 / 4000;
    let h = dist ** 1.1 / 4000;
    (scene as any).camera = new OrthographicCamera(-w, w, h, -h, perspectiveCam.near, perspectiveCam.far);
    scene.camera.position.copy(perspectiveCam.position);
    scene.camera.lookAt(scene.getTarget().clone().add(scene.target.position));
    requestAnimationFrame(() => syncOrthoCamera(false));
  }
}

let toggleProjectionText = ref('PERSP'); // Default to perspective camera
function toggleProjection() {
  if (!props.modelViewerInfo) return;
  let scene: ModelScene = props.modelViewerInfo.scene
  let prevCam = scene.camera;
  let wasPerspectiveCamera = prevCam.isPerspectiveCamera;
  if (wasPerspectiveCamera) {
    (scene as any).__perspectiveCamera = prevCam; // Save the default perspective camera
    // This hack also needs to sync the camera position and target
    requestAnimationFrame(() => syncOrthoCamera(true));
  } else {
    // Restore the default perspective camera
    scene.camera = (scene as any).__perspectiveCamera;
  }
  toggleProjectionText.value = wasPerspectiveCamera ? 'ORTHO' : 'PERSP';
}

</script>

<template>
  <orientation-gizmo v-if="props.modelViewerInfo" :scene="props.modelViewerInfo.scene"/>
  <v-btn icon="mdi-projector" @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <v-icon icon="mdi-projector"></v-icon>
  </v-btn>
</template>

<style>
.icon-detail {
  position: absolute;
  top: 10px;
  left: 0;
  font-size: xx-small;
  width: 100%;
  margin: auto;
}

.icon-detail + .v-icon {
  position: relative;
  top: 5px;
}
</style>