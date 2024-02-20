<script setup lang="ts">
import {defineModel, ref} from "vue";
import {VBtn} from "vuetify/lib/components";
import SvgIcon from '@jamescoyle/vue-icon';
import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {mdiCursorDefaultClick} from '@mdi/js';
import type {Intersection, Material, Object3D} from "three";

let props = defineProps<{ viewer: ModelViewerElement, scene: ModelScene }>();
let selectionEnabled = ref(false);
type MObject3D = Object3D & {
  material: Material & { color: { r: number, g: number, b: number }, __prevBaseColorFactor?: [number, number, number] }
};
let selectedMaterials = defineModel<Array<Intersection<MObject3D>>>({default: []});
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
  let scene: ModelScene = props.scene;
  // NOTE: Need to access internal as the API has issues with small faces surrounded by edges
  const ndcCoords = scene.getNDC(event.clientX, event.clientY);
  const hit = scene.hitFromPoint(ndcCoords) as Intersection<MObject3D> | undefined;
  console.log(hit)
  // TODO: Multiple hits to differentiate edges and faces
  // TODO: Edge collisions too big?
  // FIXME: Clicking with ORTHO camera does not work...
  if (!hit) return;
  const wasSelected = selectedMaterials.value.find((m) => m.object.name === hit.object.name) !== undefined;
  if (wasSelected) {
    deselect(hit)
  } else {
    select(hit)
  }
};

function select(hit: Intersection<MObject3D>) {
  if (selectedMaterials.value.find((m) => m.object.name === hit.object.name) === undefined) {
    selectedMaterials.value.push(hit);
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
  if (alsoRemove) selectedMaterials.value = selectedMaterials.value.filter((m) => m.object.name !== hit.object.name);
  hit.object.material.color.r = hit.object.material.__prevBaseColorFactor[0]
  hit.object.material.color.g = hit.object.material.__prevBaseColorFactor[1]
  hit.object.material.color.b = hit.object.material.__prevBaseColorFactor[2]
  delete hit.object.material.__prevBaseColorFactor;
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