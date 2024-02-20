<script setup lang="ts">
import {defineModel, ref} from "vue";
import {VBtn} from "vuetify/lib/components";
import SvgIcon from '@jamescoyle/vue-icon';
import type {ModelViewerElement} from '@google/model-viewer';
import {mdiCursorDefaultClick} from '@mdi/js';
import {$scene} from "@google/model-viewer/lib/model-viewer-base";
import type {Intersection} from "three";

let props = defineProps<{ viewer: ModelViewerElement }>();
let selectionEnabled = ref(false);
let selectedMaterials = defineModel<Array<Intersection>>({default: []});
let hasListener = false;
let mouseDownAt: [number, number] | null = null;

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
  let viewer: ModelViewerElement = props.viewer;
  // FIXME: Clicking near edges does not work...
  // FIXME: Clicking with ORTHO camera does not work...
  //const material = viewer.materialFromPoint(event.clientX, event.clientY);
  // NOTE: Need to access internal as the API has issues with small faces surrounded by edges
  let scene = viewer[$scene]
  const ndcCoords = scene.getNDC(event.clientX, event.clientY);
  const hit = scene.hitFromPoint(ndcCoords);
  console.log(hit)
  // TODO: Multiple hits to differenciate edges and faces
  if (!hit) return;
  const wasSelected = selectedMaterials.value.find((m) => m.object.name === hit.object.name) !== undefined;
  if (wasSelected) {
    deselect(hit)
  } else {
    select(hit)
  }
};

function select(hit: Intersection) {
  if (selectedMaterials.value.find((m) => m.object.name === hit.object.name) === undefined) {
    selectedMaterials.value.push(hit);
  }
  (hit.object.material as any).__prevBaseColorFactor = [
    hit.object.material.color.r,
    hit.object.material.color.g,
    hit.object.material.color.b,
  ];
  hit.object.material.color.r = 1;
  hit.object.material.color.g = 0;
  hit.object.material.color.b = 0;
}

function deselect(hit: Intersection, alsoRemove = true) {
  if (alsoRemove) selectedMaterials.value = selectedMaterials.value.filter((m) => m.object.name !== hit.object.name);
  hit.object.material.color.r = (hit.object.material as any).__prevBaseColorFactor[0]
  hit.object.material.color.g = (hit.object.material as any).__prevBaseColorFactor[1]
  hit.object.material.color.b = (hit.object.material as any).__prevBaseColorFactor[2]
  delete (hit.object.material as any).__prevBaseColorFactor;
}

function toggleSelection() {
  let viewer: ModelViewerElement = props.viewer;
  if (!viewer) return;
  selectionEnabled.value = !selectionEnabled.value;
  if (selectionEnabled.value) {
    if (!hasListener) {
      viewer.addEventListener('mouseup', selectionListener);
      viewer.addEventListener('mousedown', selectionMoveListener); // Avoid clicking when dragging
      hasListener = true;
    }
    for (let material of selectedMaterials.value) {
      select(material);
    }
  } else {
    for (let material of selectedMaterials.value) {
      deselect(material, false);
    }
  }
}
</script>

<template>
  <v-btn icon="" @click="toggleSelection" :variant="selectionEnabled ? 'tonal' : 'elevated'">
    <svg-icon type="mdi" :path="mdiCursorDefaultClick"/>
  </v-btn>
</template>