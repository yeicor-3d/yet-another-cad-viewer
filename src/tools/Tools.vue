<script setup lang="ts">
import {VBtn} from "vuetify/lib/components";
import {ref} from "vue";
import OrientationGizmo from "./OrientationGizmo.vue";
import {OrthographicCamera} from "three/src/cameras/OrthographicCamera";
import {mdiCrosshairsGps, mdiCursorDefaultClick, mdiDownload, mdiProjector} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';
import type {ModelViewerElement, RGBA} from '@google/model-viewer';
import type {Material} from '@google/model-viewer/lib/features/scene-graph/material.js';
import {SceneMgrRefData} from "../misc/scene";

let props = defineProps<{ refSData: SceneMgrRefData }>();

function syncOrthoCamera(force: boolean) {
  let scene = props.refSData.viewerScene;
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
  let scene = props.refSData.viewerScene;
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
  let viewer: ModelViewerElement = props.refSData.viewer;
  if (!viewer) return;
  viewer.updateFraming();
}

let selectionEnabled = ref(false);
let prevHighlightedMaterial: Material | null = null;
let hasListener = false;
let selectionListener = (event: MouseEvent) => {
  if (!selectionEnabled.value) return;
  let viewer: ModelViewerElement = props.refSData.viewer;
  const material = viewer.materialFromPoint(event.clientX, event.clientY);
  if (material !== null && prevHighlightedMaterial?.index === material.index) return
  if (prevHighlightedMaterial) {
    prevHighlightedMaterial.pbrMetallicRoughness.setBaseColorFactor(
        (prevHighlightedMaterial as any).__prevBaseColorFactor);
  }
  if (!material) {
    prevHighlightedMaterial = null;
    return;
  }
  (material as any).__prevBaseColorFactor = [...material.pbrMetallicRoughness.baseColorFactor];
  material.pbrMetallicRoughness.setBaseColorFactor([1, 0, 0, 1] as RGBA);
  prevHighlightedMaterial = material;
};

function toggleSelection() {
  let viewer: ModelViewerElement = props.refSData.viewer;
  if (!viewer) return;
  selectionEnabled.value = !selectionEnabled.value;
  if (selectionEnabled.value) {
    if (!hasListener) {
      viewer.addEventListener('mousemove', selectionListener);
      hasListener = true;
    }
  } else {
    if (prevHighlightedMaterial) {
      prevHighlightedMaterial.pbrMetallicRoughness.setBaseColorFactor(
          (prevHighlightedMaterial as any).__prevBaseColorFactor);
      prevHighlightedMaterial = null;
    }
  }
}

async function downloadSceneGlb() {
  let viewer = props.refSData.viewer;
  if (!viewer) return;
  const glTF = await viewer.exportScene();
  const file = new File([glTF], "export.glb");
  const link = document.createElement("a");
  link.download = file.name;
  link.href = URL.createObjectURL(file);
  link.click();
}

</script>

<template>
  <orientation-gizmo :scene="props.refSData.viewerScene" v-if="props.refSData.viewerScene !== null"/>
  <v-btn icon="" @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <svg-icon type="mdi" :path="mdiProjector"></svg-icon>
  </v-btn>
  <v-btn icon="" @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-btn icon="" @click="toggleSelection" :variant="selectionEnabled ? 'tonal' : 'elevated'">
    <svg-icon type="mdi" :path="mdiCursorDefaultClick"/>
  </v-btn>
  <v-btn icon="" @click="downloadSceneGlb">
    <svg-icon type="mdi" :path="mdiDownload"/>
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