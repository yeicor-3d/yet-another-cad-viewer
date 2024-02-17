<script setup lang="ts">
import {VBtn} from "vuetify/lib/components";
import {ref} from "vue";
import OrientationGizmo from "./OrientationGizmo.vue";
import {OrthographicCamera} from "three/src/cameras/OrthographicCamera";
import {mdiCrosshairsGps, mdiProjector} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';
import {SceneManagerData} from "../misc/scene";
import type {ModelViewerElement} from '@google/model-viewer';

let props = defineProps<{ sceneMgrData: SceneManagerData }>();

function syncOrthoCamera(force: boolean) {
  let scene = props.sceneMgrData.viewerScene;
  if (!scene) return;
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
  let scene = props.sceneMgrData.viewerScene;
  if (!scene) return;
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

function centerCamera() {
  let viewer: ModelViewerElement = props.sceneMgrData.viewer;
  if (!viewer) return;
  viewer.updateFraming();
}

</script>

<template>
  <orientation-gizmo :scene="props.sceneMgrData.viewerScene" v-if="props.sceneMgrData.viewerScene !== null"/>
  <v-btn icon="" @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <svg-icon type="mdi" :path="mdiProjector"></svg-icon>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
</template>

<!--suppress CssUnusedSymbol -->
<style>
.icon-detail {
  position: absolute;
  top: 10px;
  left: 0;
  font-size: xx-small;
  width: 100%;
  margin: auto;
}

.icon-detail + svg {
  position: relative;
  top: 5px;
}
</style>