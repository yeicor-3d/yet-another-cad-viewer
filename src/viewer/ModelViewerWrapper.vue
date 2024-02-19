<script setup lang="ts">
import {settings} from "../misc/settings";
import {ModelViewerElement} from '@google/model-viewer';
import {onMounted, ref} from "vue";
import {$scene} from "@google/model-viewer/lib/model-viewer-base";
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";

export type ModelViewerInfo = { viewer: ModelViewerElement, scene: ModelScene };

ModelViewerElement.modelCacheSize = 0; // Also needed to avoid tree shaking

const emit = defineEmits<{
  load: [info: ModelViewerInfo]
}>()

const props = defineProps({
  src: String
});

let viewer = ref<ModelViewerElement | null>(null);
onMounted(() => {
  viewer.value.addEventListener('load', () => {
    if (viewer.value) {
      emit('load', {
        viewer: viewer.value,
        scene: viewer.value[$scene] as ModelScene,
      })
    }
  });
});

</script>

<template>
  <model-viewer ref="viewer"
                style="width: 100%; height: 100%" :src="props.src" alt="The 3D model(s)" camera-controls camera-orbit="30deg 75deg auto"
                max-camera-orbit="Infinity 180deg auto" min-camera-orbit="-Infinity 0deg 1%" disable-tap
                :exposure="settings.exposure" :shadow-intensity="settings.shadowIntensity" interaction-prompt="none"
                :autoplay="settings.autoplay" :ar="settings.arModes.length > 0" :ar-modes="settings.arModes"
                :skybox-image="settings.background" :environment-image="settings.background">
    <slot></slot> <!-- Controls, annotations, etc. -->
  </model-viewer>
</template>

<style scoped>
/* This keeps child nodes hidden while the element loads */
:not(:defined) > * {
  display: none;
}
</style>