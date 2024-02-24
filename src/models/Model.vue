<script setup lang="ts">
import {
  VBtn,
  VBtnToggle,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSpacer,
  VTooltip
} from "vuetify/lib/components";
import {extrasNameKey} from "../misc/gltf";
import {Document, Mesh} from "@gltf-transform/core";
import {watch} from "vue";

import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {mdiDelete, mdiRectangle, mdiRectangleOutline, mdiVectorRectangle} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';

const props = defineProps<{ mesh: Mesh, viewer: InstanceType<typeof ModelViewerWrapper> | null, document: Document }>();
const emit = defineEmits<{ remove: [] }>()

let modelName = props.mesh.getExtras()[extrasNameKey] // + " blah blah blah blah blag blah blah blah"

let faceCount = props.mesh.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.TRIANGLES).length
let edgeCount = props.mesh.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.LINE_STRIP).length
let vertexCount = props.mesh.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.POINTS).length

const enabledFeatures = defineModel<Array<number>>("enabledFeatures", {default: [0, 1, 2]});

let hasListener = false;

function onEnabledFeaturesChange(newEnabledFeatures: Array<number>) {
  //console.log('Enabled features may have changed', newEnabledFeatures)
  let scene = props.viewer?.scene;
  if (!scene || !scene._model) return;
  if (!hasListener) { // Make sure we listen for reloads and re-apply enabled features
    props.viewer.elem.addEventListener('load', () => onEnabledFeaturesChange(enabledFeatures.value));
    hasListener = true;
  }
  // Iterate all primitives of the mesh and set their visibility based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  scene._model.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      let childIsFace = child.type == 'Mesh' || child.type == 'SkinnedMesh'
      let childIsEdge = child.type == 'Line'
      let childIsVertex = child.type == 'Point'
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
</script>

<template>
  <v-expansion-panel>
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
      TODO: Settings...
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}

/* More compact accordions */
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
.hide-this-icon {
  display: none !important;
}
</style>