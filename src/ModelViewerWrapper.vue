<script setup lang="ts">
import {settings} from "./settings";
import {onMounted, ref} from "vue";
import {ModelViewerElement} from '@google/model-viewer';
import {OrientationGizmo} from "./orientation";
import {$scene} from "@google/model-viewer/lib/model-viewer-base";
import {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";

let _ = ModelViewerElement  // HACK: Keep the import from being removed by the bundler
const viewer = ref(null);
onMounted(() => {
  // TODO: Custom gizmo component inside Tools window
  // Gizmo installation
  let scene: ModelScene = viewer.value[$scene];
  console.log('Mounted ModelViewerWrapper', viewer, scene);
  let gizmo = new OrientationGizmo(scene);
  gizmo.install();

  function updateGizmo() {
    gizmo.update();
    requestAnimationFrame(updateGizmo);
  }

  updateGizmo();
  console.log('Mounted ModelViewerWrapper');
});
</script>

<template>
  <model-viewer
      ref="viewer" style="width: 100%; height: 100%" :src="settings.preloadModel" alt="The 3D model(s)" camera-controls
      camera-orbit="30deg 75deg auto" max-camera-orbit="Infinity 180deg auto" min-camera-orbit="-Infinity 0deg auto"
      :exposure="settings.exposure" :shadow-intensity="settings.shadowIntensity" interaction-prompt="none"
      :autoplay="settings.autoplay" :ar="settings.arModes.length > 0" :ar-modes="settings.arModes"
      :skybox-image="settings.background" :environment-image="settings.background"></model-viewer>
</template>