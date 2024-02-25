<script lang="ts">
</script>

<script setup lang="ts">
import {settings} from "../misc/settings";
import {onMounted} from "vue";
import {$scene, $renderer} from "@google/model-viewer/lib/model-viewer-base";
import Loading from "../misc/Loading.vue";
import {ref} from "vue";
import {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import type {Renderer} from "@google/model-viewer/lib/three-components/Renderer";

ModelViewerElement.modelCacheSize = 0; // Also needed to avoid tree shaking

const emit = defineEmits<{ load: [] }>()

const props = defineProps({
  src: String
});

const elem = ref<ModelViewerElement | null>(null);
const scene = ref<ModelScene | null>(null);
const renderer = ref<Renderer | null>(null);
defineExpose({elem, scene, renderer});

onMounted(() => {
  elem.value.addEventListener('load', () => {
    if (elem.value) {
      // Delete the initial load banner
      // TODO: Replace with an actual poster?
      let banner = elem.value.querySelector('.initial-load-banner');
      if (banner) banner.remove();
      // Set the scene
      scene.value = elem.value[$scene] as ModelScene;
      renderer.value = elem.value[$renderer] as Renderer;
      // Emit the load event
      emit('load')
    }
  });
});

</script>

<template>
  <model-viewer ref="elem" style="width: 100%; height: 100%" :src="props.src" alt="The 3D model(s)" camera-controls
                camera-orbit="30deg 75deg auto" max-camera-orbit="Infinity 180deg auto"
                min-camera-orbit="-Infinity 0deg 5%" disable-tap :exposure="settings.exposure"
                :shadow-intensity="settings.shadowIntensity" interaction-prompt="none" :autoplay="settings.autoplay"
                :ar="settings.arModes.length > 0" :ar-modes="settings.arModes" :skybox-image="settings.background"
                :environment-image="settings.background">
    <slot></slot> <!-- Controls, annotations, etc. -->
    <loading class="annotation initial-load-banner"></loading>
  </model-viewer>
  <!-- TODO: Transparent SVG overlay that can draw 2D lines attached to the 3D model(s) -->
  <!-- https://modelviewer.dev/examples/annotations/index.html -->
  <div class="overlay-svg-wrapper">
    <svg class="overlay-svg" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
      <!--<line x1="0" y1="0" x2="100%" y2="100%" stroke="black" stroke-width="2"/>-->
    </svg>
  </div>
</template>

<style scoped>
/* This keeps child nodes hidden while the element loads */
:not(:defined) > * {
  display: none;
}

/* This is the SVG overlay that will be used for line annotations */
.overlay-svg-wrapper {
  position: relative;
  top: -100%;
  left: 0;
  width: 100%;
  height: 0;
  pointer-events: none;
  z-index: 1;
}

.overlay-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100dvh;
  pointer-events: none;
}
</style>