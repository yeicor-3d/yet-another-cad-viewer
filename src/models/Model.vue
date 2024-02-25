<script setup lang="ts">
import {
  VBtn,
  VBtnToggle,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSlider,
  VSpacer,
  VTooltip
} from "vuetify/lib/components";
import {extrasNameKey} from "../misc/gltf";
import {Document, Mesh} from "@gltf-transform/core";
import {watch} from "vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {mdiCircleOpacity, mdiDelete, mdiRectangle, mdiRectangleOutline, mdiVectorRectangle} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';

const props = defineProps<{
  meshes: Array<Mesh>,
  viewer: InstanceType<typeof ModelViewerWrapper> | null,
  document: Document
}>();
const emit = defineEmits<{ remove: [] }>()

let modelName = props.meshes[0].getExtras()[extrasNameKey] // + " blah blah blah blah blag blah blah blah"

// Reactive properties
const enabledFeatures = defineModel<Array<number>>("enabledFeatures", {default: [0, 1, 2]});
const opacity = defineModel<number>("opacity", {default: 1});
// TODO: Clipping planes (+ stencil!)

// Count the number of faces, edges and vertices
let faceCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.TRIANGLES).length).reduce((a, b) => a + b, 0)
let edgeCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() in [WebGL2RenderingContext.LINE_STRIP, WebGL2RenderingContext.LINES]).length).reduce((a, b) => a + b, 0)
let vertexCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.POINTS).length).reduce((a, b) => a + b, 0)

// Set initial defaults for the enabled features
if (faceCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 0)
if (edgeCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 1)
if (vertexCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 2)

// Listeners for changes in the properties (or viewer reloads)
function onEnabledFeaturesChange(newEnabledFeatures: Array<number>) {
  //console.log('Enabled features may have changed', newEnabledFeatures)
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their visibility based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      let childIsFace = child.type == 'Mesh' || child.type == 'SkinnedMesh'
      let childIsEdge = child.type == 'Line' || child.type == 'LineSegments'
      let childIsVertex = child.type == 'Points'
      if (childIsFace || childIsEdge || childIsVertex) {
        let visible = newEnabledFeatures.includes(childIsFace ? 0 : childIsEdge ? 1 : childIsVertex ? 2 : -1);
        if (child.visible !== visible) {
          child.visible = visible;
        }
      }
    }
  });
  scene.queueRender()
}

watch(enabledFeatures, onEnabledFeaturesChange);

function onOpacityChange(newOpacity: number) {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their opacity based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  // console.log('Opacity may have changed', newOpacity)
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.material && child.material.opacity !== newOpacity) {
        child.material.transparent = newOpacity < 1;
        child.material.opacity = newOpacity;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender()
}

watch(opacity, onOpacityChange);

function onModelLoad() {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their visibility based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      // if (child.type == 'Line' || child.type == 'LineSegments') {
      // child.material.linewidth = 3; // Not supported in WebGL2
      // If wide lines are really needed, we need https://threejs.org/examples/?q=line#webgl_lines_fat
      // }
      if (child.type == 'Points') {
        child.material.size = 5;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender()

  // Furthermore...
  // Enabled features may have been reset after a reload
  onEnabledFeaturesChange(enabledFeatures.value)
  // Opacity may have been reset after a reload
  onOpacityChange(opacity.value)
}

// props.viewer.elem may not yet be available, so we need to wait for it
if (props.viewer.elem) {
  props.viewer.elem.addEventListener('load', onModelLoad);
} else {
  watch(() => props.viewer?.elem, (elem) => {
    if (elem) elem.addEventListener('load', onModelLoad);
  });
}
</script>

<template>
  <v-expansion-panel :value="modelName">
    <v-expansion-panel-title expand-icon="hide-this-icon" collapse-icon="hide-this-icon">
      <v-btn-toggle v-model="enabledFeatures" multiple @click.stop color="surface-light">
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Faces ({{ faceCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiRectangle"></svg-icon>
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Edges ({{ edgeCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiRectangleOutline"></svg-icon>
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Vertices ({{ vertexCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiVectorRectangle"></svg-icon>
        </v-btn>
      </v-btn-toggle>
      <div class="model-name">{{ modelName }}</div>
      <v-spacer></v-spacer>
      <v-btn icon @click.stop="emit('remove')">
        <v-tooltip activator="parent">Remove</v-tooltip>
        <svg-icon type="mdi" :path="mdiDelete"></svg-icon>
      </v-btn>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-slider v-model="opacity" hide-details min="0" max="1" :step="0.1">
        <template v-slot:prepend>
          <svg-icon type="mdi" :path="mdiCircleOpacity"></svg-icon>
        </template>
      </v-slider>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}

/* More compact accordions */
.v-expansion-panel {
  margin-top: 0 !important;
}

.v-expansion-panel-title {
  padding: 0;
}

.v-expansion-panel-title > .v-btn-toggle {
  margin: 0;
  margin-right: 8px;
}

.v-btn {
  --v-btn-height: 16px;
}

.model-name {
  width: 130px;
  min-height: 1.15em; /* HACK: Avoid eating the bottom of the text when using 1 line */
  max-height: 2em;
  text-overflow: ellipsis;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* https://caniuse.com/?search=line-clamp */
  -webkit-box-orient: vertical;
}
</style>

<style>
.v-expansion-panel-text__wrapper {
  padding: 0 !important;
}

.hide-this-icon {
  display: none !important;
}
</style>