<script setup lang="ts">
import {defineModel, ref} from "vue";
import {VBtn, VSelect, VTooltip} from "vuetify/lib/components";
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';
import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {mdiCubeOutline, mdiCursorDefaultClick, mdiFeatureSearch, mdiRuler} from '@mdi/js';
import type {Intersection, Material, Object3D} from "three";
import {Raycaster} from "three";
import type ModelViewerWrapperT from "./ModelViewerWrapper.vue";
import {extrasNameKey} from "../misc/gltf";

export type MObject3D = Object3D & {
  userData: { noHit?: boolean },
  material: Material & { color: { r: number, g: number, b: number }, __prevBaseColorFactor?: [number, number, number] }
};

let props = defineProps<{ viewer: typeof ModelViewerWrapperT | null }>();
let emit = defineEmits<{ findModel: [string] }>();
let selectionEnabled = ref(false);
let selected = defineModel<Array<Intersection<MObject3D>>>({default: []});
let highlightNextSelection = ref([false, false]); // Second is whether selection was enabled before
let showBoundingBox = ref<Boolean>(false);

let hasListener = false;
let mouseDownAt: [number, number] | null = null;
let selectFilter = ref('Any');
const raycaster = new Raycaster();

let selectionMoveListener = (event: MouseEvent) => {
  if (!selectionEnabled.value) return;
  mouseDownAt = [event.clientX, event.clientY];
};

let selectionListener = (event: MouseEvent) => {
  if (!selectionEnabled.value) {
    mouseDownAt = undefined;
    return;
  }
  if (mouseDownAt) {
    let [x, y] = mouseDownAt;
    if (Math.abs(event.clientX - x) > 5 || Math.abs(event.clientY - y) > 5) {
      mouseDownAt = undefined;
      return;
    }
    mouseDownAt = undefined;
  }
  let scene: ModelScene = props.viewer?.scene;
  // NOTE: Need to access internal as the API has issues with small faces surrounded by edges
  const ndcCoords = scene.getNDC(event.clientX, event.clientY);
  //const hit = scene.hitFromPoint(ndcCoords) as Intersection<MObject3D> | undefined;
  raycaster.setFromCamera(ndcCoords, (scene as any).camera);
  if ((scene as any).camera.isOrthographicCamera) {
    // Need to fix the ray direction for ortho camera
    // FIXME: Still buggy (but less so :)
    raycaster.ray.direction.copy(
        scene.getTarget().clone().add(scene.target.position).sub((scene as any).camera.position).normalize());
  }
  // console.log('NDC', ndcCoords, 'Camera', (scene as any).camera, 'Ray', ray_caster.ray);
  const hits = raycaster.intersectObject(scene, true);
  let hit = hits.find((hit) => {
    const kind = hit.object.type
    const kindOk = (selectFilter.value === 'Any') ||
        ((kind === 'Mesh' || kind === 'SkinnedMesh') && selectFilter.value === 'Faces') ||
        (kind === 'Line' && selectFilter.value === 'Edges') ||
        (kind === 'Points' && selectFilter.value === 'Vertices');
    return hit.object.visible && !hit.object.userData.noHit && kindOk;
  }) as Intersection<MObject3D> | undefined;
  console.log('Hit', hit)
  if (!highlightNextSelection.value[0]) {
    if (!hit) {
      deselectAll();
    } else {
      // Toggle selection
      const wasSelected = selected.value.find((m) => m.object.name === hit.object.name) !== undefined;
      if (wasSelected) {
        deselect(hit)
      } else {
        select(hit)
      }
    }
  } else {
    // Otherwise, highlight the model that owns the hit
    emit('findModel', hit.object.userData[extrasNameKey])
    // And reset the selection mode
    toggleHighlightNextSelection()
  }
  scene.queueRender() // Force rerender of model-viewer
}

function select(hit: Intersection<MObject3D>) {
  console.log('Selecting', hit.object.name)
  if (selected.value.find((m) => m.object.name === hit.object.name) === undefined) {
    selected.value.push(hit);
  }
  hit.object.material.__prevBaseColorFactor = [
    hit.object.material.color.r,
    hit.object.material.color.g,
    hit.object.material.color.b,
  ];
  hit.object.material.color.r = 1;
  hit.object.material.color.g = 0;
  hit.object.material.color.b = 0;
}

function deselect(hit: Intersection<MObject3D>, alsoRemove = true) {
  console.log('Deselecting', hit.object.name)
  if (alsoRemove) {
    // Remove the matching object from the selection
    let toRemove = selected.value.findIndex((m) => m.object.name === hit.object.name);
    selected.value.splice(toRemove, 1);
  }
  hit.object.material.color.r = hit.object.material.__prevBaseColorFactor[0]
  hit.object.material.color.g = hit.object.material.__prevBaseColorFactor[1]
  hit.object.material.color.b = hit.object.material.__prevBaseColorFactor[2]
  delete hit.object.material.__prevBaseColorFactor;
}

function deselectAll(alsoRemove = true) {
  // Clear selection (shallow copy to avoid modifying the array while iterating)
  let toClear = selected.value.slice();
  for (let material of toClear) {
    deselect(material, alsoRemove);
  }
}

function toggleSelection() {
  let viewer: ModelViewerElement = props.viewer?.elem;
  if (!viewer) return;
  selectionEnabled.value = !selectionEnabled.value;
  if (selectionEnabled.value) {
    if (!hasListener) {
      viewer.addEventListener('mouseup', selectionListener);
      viewer.addEventListener('mousedown', selectionMoveListener); // Avoid clicking when dragging
      hasListener = true;
    }
    for (let material of selected.value) {
      select(material);
    }
  } else {
    deselectAll(false);
  }
  props.viewer.scene.queueRender() // Force rerender of model-viewer
}

function toggleHighlightNextSelection() {
  highlightNextSelection.value = [
    !highlightNextSelection.value[0],
    highlightNextSelection.value[0] ? highlightNextSelection.value[1] : selectionEnabled.value
  ];
  if (highlightNextSelection.value[0]) {
    // Reuse selection code to identify the model
    if (!selectionEnabled.value) toggleSelection()
  } else {
    if (selectionEnabled.value !== highlightNextSelection.value[1]) toggleSelection()
    highlightNextSelection.value = [false, false];
  }
}

function toggleShowBoundingBox() {
  // let scene: ModelScene = props.viewer?.scene;
  // if (!scene) return;
  showBoundingBox.value = !showBoundingBox.value;
  // scene.model?.traverse((child) => {
  //   if (child.userData[extrasNameKey] === modelName) {
  //     if (child.type === 'BoxHelper') {
  //       child.visible = showBoundingBox.value;
  //     }
  //   }
  // });
  // scene.queueRender() // Force rerender of model-viewer

}
</script>

<template>
  <div class="select-parent">
    <v-btn icon @click="toggleSelection" :color="selectionEnabled ? 'surface-light' : ''">
      <v-tooltip activator="parent">{{ selectionEnabled ? 'Disable selection mode' : 'Enable selection mode' }}
      </v-tooltip>
      <svg-icon type="mdi" :path="mdiCursorDefaultClick"/>
    </v-btn>
    <v-tooltip :text="'Select only '  + selectFilter.toString().toLocaleLowerCase()" :open-on-click="false">
      <template v-slot:activator="{ props }">
        <!-- TODO: Keyboard shortcuts for fast selection (& other tools) -->
        <v-select v-bind="props" class="select-only" variant="underlined"
                  :items="['Any', 'Faces', 'Edges', 'Vertices']"
                  v-model="selectFilter"/>
      </template>
    </v-tooltip>
  </div>
  <v-btn icon @click="toggleHighlightNextSelection" :color="highlightNextSelection[0] ? 'surface-light' : ''">
    <v-tooltip activator="parent">Highlight the next clicked element in the models list</v-tooltip>
    <svg-icon type="mdi" :path="mdiFeatureSearch"/>
  </v-btn>
  <!-- TODO: Show BB -->
  <v-btn icon disabled @click="toggleShowBoundingBox" :color="showBoundingBox ? 'surface-light' : ''">
    <v-tooltip activator="parent">{{ showBoundingBox ? 'Hide selection bounds' : 'Show selection bounds' }}
    </v-tooltip>
    <svg-icon type="mdi" :path="mdiCubeOutline"/>
  </v-btn>
  <!-- TODO: Show distances of selections (min/center/max distance) -->
  <v-btn icon disabled @click="toggleShowBoundingBox" :color="showBoundingBox ? 'surface-light' : ''">
    <v-tooltip activator="parent">{{ showBoundingBox ? 'Hide selection dimensions' : 'Show selection dimensions' }}
    </v-tooltip>
    <svg-icon type="mdi" :path="mdiRuler"/>
  </v-btn>
</template>

<style scoped>
/* Very hacky styling... */
.select-parent {
  height: 48px;
}

.select-parent .v-btn {
  position: relative;
  top: -42px;
}

.select-only {
  display: inline-block;
  width: calc(100% - 48px);
  position: relative;
  top: -12px;
}
</style>