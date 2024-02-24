<script setup lang="ts">
import {defineModel, ref} from "vue";
import {VBtn, VSelect, VTooltip} from "vuetify/lib/components";
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';
import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {mdiCursorDefaultClick} from '@mdi/js';
import type {Intersection, Material, Object3D} from "three";
import {Raycaster} from "three";
import type ModelViewerWrapperT from "./ModelViewerWrapper.vue";

export type MObject3D = Object3D & {
  userData: { noHit?: boolean },
  material: Material & { color: { r: number, g: number, b: number }, __prevBaseColorFactor?: [number, number, number] }
};

let props = defineProps<{ viewer: typeof ModelViewerWrapperT | null }>();
let selectionEnabled = ref(false);
let selectedMaterials = defineModel<Array<Intersection<MObject3D>>>({default: []});
let hasListener = false;
let mouseDownAt: [number, number] | null = null;
let selectFilter = ref('Faces');
const ray_caster = new Raycaster();

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
  ray_caster.setFromCamera(ndcCoords, (scene as any).camera);
  if ((scene as any).camera.isOrthographicCamera) {
    // Need to fix the ray direction for ortho camera
    // FIXME: Still buggy (but less so :)
    ray_caster.ray.direction.copy(
        scene.getTarget().clone().add(scene.target.position).sub((scene as any).camera.position).normalize());
  }
  console.log('NDC', ndcCoords, 'Camera', (scene as any).camera, 'Ray', ray_caster.ray);
  const hits = ray_caster.intersectObject(scene, true);
  console.log(hits)
  let hit = hits.find((hit) => {
    let isFace = hit.faceIndex !== null;
    return hit.object.visible && !hit.object.userData.noHit && isFace == (selectFilter.value === 'Faces');
  }) as Intersection<MObject3D> | undefined;
  if (!hit) {
    deselectAll();
  } else {
    // Toggle selection
    const wasSelected = selectedMaterials.value.find((m) => m.object.name === hit.object.name) !== undefined;
    if (wasSelected) {
      deselect(hit)
    } else {
      select(hit)
    }
  }
  scene.queueRender() // Force rerender of model-viewer
};

function select(hit: Intersection<MObject3D>) {
  console.log('Selecting', hit.object.name)
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
  console.log('Deselecting', hit.object.name)
  if (alsoRemove) {
    // Remove the matching object from the selection
    let toRemove = selectedMaterials.value.findIndex((m) => m.object.name === hit.object.name);
    selectedMaterials.value.splice(toRemove, 1);
  }
  hit.object.material.color.r = hit.object.material.__prevBaseColorFactor[0]
  hit.object.material.color.g = hit.object.material.__prevBaseColorFactor[1]
  hit.object.material.color.b = hit.object.material.__prevBaseColorFactor[2]
  delete hit.object.material.__prevBaseColorFactor;
}

function deselectAll(alsoRemove = true) {
  // Clear selection (shallow copy to avoid modifying the array while iterating)
  let toClear = selectedMaterials.value.slice();
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
    for (let material of selectedMaterials.value) {
      select(material);
    }
  } else {
    deselectAll(false);
  }
  props.viewer.scene.queueRender() // Force rerender of model-viewer
}
</script>

<template>
  <div class="select-parent">
    <v-btn icon @click="toggleSelection" :variant="selectionEnabled ? 'tonal' : 'elevated'">
      <v-tooltip activator="parent">{{ selectionEnabled ? 'Disable Selection Mode' : 'Enable Selection Mode' }}
      </v-tooltip>
      <svg-icon type="mdi" :path="mdiCursorDefaultClick"/>
    </v-btn>
    <v-tooltip :text="'Select Only '  + selectFilter" :open-on-click="false">
      <template v-slot:activator="{ props }">
        <v-select v-bind="props" class="select-only" variant="underlined" :items="['Faces', 'Edges', 'Vertices']"
                  v-model="selectFilter"/>
      </template>
    </v-tooltip>
  </div>
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