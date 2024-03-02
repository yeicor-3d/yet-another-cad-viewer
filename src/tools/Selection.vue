<script setup lang="ts">
import {defineModel, inject, ref, ShallowRef, watch} from "vue";
import {VBtn, VSelect, VTooltip} from "vuetify/lib/components";
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';
import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {mdiCubeOutline, mdiCursorDefaultClick, mdiFeatureSearch, mdiRuler} from '@mdi/js';
import type {Intersection, Material, Object3D} from "three";
import {Box3, Matrix4, Raycaster, Vector3} from "three";
import type ModelViewerWrapperT from "./ModelViewerWrapper.vue";
import {extrasNameKey} from "../misc/gltf";
import {SceneMgr} from "../misc/scene";
import {Document} from "@gltf-transform/core";
import {AxesColors} from "../misc/helpers";
import {distances} from "../misc/distances";

export type MObject3D = Object3D & {
  userData: { noHit?: boolean },
  material: Material & { color: { r: number, g: number, b: number }, __prevBaseColorFactor?: [number, number, number] }
};

let props = defineProps<{ viewer: typeof ModelViewerWrapperT | null }>();
let emit = defineEmits<{ findModel: [string] }>();
let {setDisableTap} = inject<{ setDisableTap: (boolean) => void }>('disableTap');
let selectionEnabled = ref(false);
let selected = defineModel<Array<Intersection<MObject3D>>>({default: []});
let highlightNextSelection = ref([false, false]); // Second is whether selection was enabled before
let showBoundingBox = ref<Boolean>(false); // Enabled automatically on start
let showDistances = ref<Boolean>(true);

let mouseDownAt: [number, number] | null = null;
let selectFilter = ref('Any (S)');
const raycaster = new Raycaster();


let selectionMoveListener = (event: MouseEvent) => {
  mouseDownAt = [event.clientX, event.clientY];
  if (!selectionEnabled.value) return;
};

let selectionListener = (event: MouseEvent) => {
  // If the mouse moved while clicked (dragging), avoid selection logic
  if (mouseDownAt) {
    let [x, y] = mouseDownAt;
    mouseDownAt = null;
    if (Math.abs(event.clientX - x) > 5 || Math.abs(event.clientY - y) > 5) {
      return;
    }
  }

  // If disabled, avoid selection logic
  if (!selectionEnabled.value) {
    return;
  }

  // Set raycaster parameters
  if (selectFilter.value === 'Any (S)') {
    raycaster.params.Line.threshold = 0.2;
    raycaster.params.Points.threshold = 0.8;
  } else if (selectFilter.value === '(E)dges') {
    raycaster.params.Line.threshold = 0.8;
    raycaster.params.Points.threshold = 0.0;
  } else if (selectFilter.value === '(V)ertices') {
    raycaster.params.Line.threshold = 0.0;
    raycaster.params.Points.threshold = 0.8;
  } else if (selectFilter.value === '(F)aces') {
    raycaster.params.Line.threshold = 0.0;
    raycaster.params.Points.threshold = 0.0;
  }

  // Define the 3D ray from the camera to the mouse
  // NOTE: Need to access internal as the API has issues with small faces surrounded by edges
  let scene: ModelScene = props.viewer?.scene;
  const ndcCoords = scene.getNDC(event.clientX, event.clientY);
  raycaster.setFromCamera(ndcCoords, scene.camera);
  if (!scene.camera.isPerspectiveCamera) {
    // Need to fix the ray direction for ortho camera FIXME: Still buggy...
    raycaster.ray.direction.copy(scene.camera.getWorldDirection(new Vector3()));
  }
  //console.log('Ray', raycaster.ray);

  // DEBUG: Draw the ray
  // let actualFrom = scene.getTarget().clone().add(raycaster.ray.origin);
  // let actualTo = actualFrom.clone().add(raycaster.ray.direction.clone().multiplyScalar(50));
  // let lineHandle = props.viewer?.addLine3D(actualFrom, actualTo, "Ray")
  // setTimeout(() => props.viewer?.removeLine3D(lineHandle), 30000)

  // Find all hit objects and select the wanted one based on the filter
  const hits = raycaster.intersectObject(scene, true);
  let hit = hits.find((hit) => {
    const kind = hit.object.type
    console.log(kind)
    const kindOk = (selectFilter.value === 'Any (S)') ||
        ((kind === 'Mesh' || kind === 'SkinnedMesh') && selectFilter.value === '(F)aces') ||
        ((kind === 'Line' || kind === 'LineSegments') && selectFilter.value === '(E)dges') ||
        (kind === 'Points' && selectFilter.value === '(V)ertices');
    return hit.object.visible && !hit.object.userData.noHit && kindOk;
  }) as Intersection<MObject3D> | undefined;
  //console.log('Hit', hit)

  if (!highlightNextSelection.value[0]) {
    // If we are selecting, toggle the selection or deselect all if no hit
    if (hit) {
      // Toggle selection
      const wasSelected = selected.value.find((m) => m.object.name === hit.object.name) !== undefined;
      if (wasSelected) {
        deselect(hit)
      } else {
        select(hit)
      }
    } else {
      deselectAll();
    }
    updateBoundingBox();
    updateDistances();
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
  setDisableTap(selectionEnabled.value);
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
  showBoundingBox.value = !showBoundingBox.value;
  updateBoundingBox();
}

let firstLoad = true;
let hasListeners = false;
let cameraChangeWaiting = false;
let cameraChangeLast = 0
let onCameraChange = () => {
  // Avoid updates while dragging (slow operation)
  cameraChangeLast = performance.now();
  if (cameraChangeWaiting) return;
  cameraChangeWaiting = true;
  let waitingHandler: () => void;
  waitingHandler = () => {
    // Ignore also inertia
    if (performance.now() - cameraChangeLast > 250) {
      updateBoundingBox();
      cameraChangeWaiting = false;
    } else {
      // If the camera is still moving, wait a bit more
      setTimeout(waitingHandler, 100);
    }
  };
  setTimeout(waitingHandler, 100); // Wait for the camera to stop moving
};
let onViewerReady = (viewer) => {
  if (!viewer) return;
  // props.viewer.elem may not yet be available, so we need to wait for it
  viewer.onElemReady((elem) => {
    if (hasListeners) return;
    hasListeners = true;
    elem.addEventListener('mouseup', selectionListener);
    elem.addEventListener('mousedown', selectionMoveListener); // Avoid clicking when dragging
    elem.addEventListener('load', () => {
      if (firstLoad) {
        toggleShowBoundingBox();
        firstLoad = false;
      } else {
        updateBoundingBox();
      }
    });
    elem.addEventListener('camera-change', onCameraChange);
  });
};
if (props.viewer) onViewerReady(props.viewer);
else watch(() => props.viewer, onViewerReady);

let {sceneDocument}: { sceneDocument: ShallowRef<Document> } = inject('sceneDocument');
let boundingBoxLines: { [points: string]: number } = {}

function updateBoundingBox() {
  if (!showBoundingBox.value) {
    for (let lineId of Object.values(boundingBoxLines)) {
      props.viewer?.removeLine3D(lineId);
    }
    boundingBoxLines = {};
    return;
  }
  let bb: Box3
  let boundingBoxLinesToRemove = Object.keys(boundingBoxLines);
  if (selected.value.length > 0) {
    bb = new Box3();
    for (let hit of selected.value) {
      bb.expandByObject(hit.object);
    }
    bb.applyMatrix4(new Matrix4().makeTranslation(props.viewer?.scene.getTarget()));
  } else {
    bb = SceneMgr.getBoundingBox(sceneDocument.value);
  }
  // Define each edge of the bounding box, to draw a line for each axis
  let corners = [
    [bb.min.x, bb.min.y, bb.min.z],
    [bb.min.x, bb.min.y, bb.max.z],
    [bb.min.x, bb.max.y, bb.min.z],
    [bb.min.x, bb.max.y, bb.max.z],
    [bb.max.x, bb.min.y, bb.min.z],
    [bb.max.x, bb.min.y, bb.max.z],
    [bb.max.x, bb.max.y, bb.min.z],
    [bb.max.x, bb.max.y, bb.max.z],
  ];
  let edgesByAxis = [
    [[0, 4], [1, 5], [2, 6], [3, 7]], // X (CAD)
    [[0, 2], [1, 3], [4, 6], [5, 7]], // Z (CAD)
    [[0, 1], [2, 3], [4, 5], [6, 7]], // Y (CAD)
  ];
  // Only draw one edge per axis, the 2nd closest one to the camera
  for (let edgeI in edgesByAxis) {
    let axisEdges = edgesByAxis[edgeI];
    let edge: Array<number> = axisEdges[0];
    for (let i = 0; i < 2; i++) { // Find the 2nd closest one by running twice dropping the first
      edge = axisEdges[0];
      let edgeDist = Infinity;
      let cameraPos: Vector3 = props.viewer?.scene.camera.position;
      for (let testEdge of axisEdges) {
        let from = new Vector3(...corners[testEdge[0]]);
        let to = new Vector3(...corners[testEdge[1]]);
        let mid = from.clone().add(to).multiplyScalar(0.5);
        let newDist = cameraPos.distanceTo(mid);
        if (newDist < edgeDist) {
          edge = testEdge;
          edgeDist = newDist;
        }
      }
      axisEdges = axisEdges.filter((e) => e !== edge);
    }
    let from = new Vector3(...corners[edge[0]]);
    let to = new Vector3(...corners[edge[1]]);
    let color = [AxesColors.x, AxesColors.y, AxesColors.z][edgeI][1]; // Secondary colors
    let lineCacheKey = JSON.stringify([from, to]);
    let matchingLine = boundingBoxLines[lineCacheKey];
    if (matchingLine) {
      boundingBoxLinesToRemove = boundingBoxLinesToRemove.filter((l) => l !== lineCacheKey);
    } else {
      let newLineId = props.viewer.addLine3D(from, to,
          to.clone().sub(from).length().toFixed(1) + "mm", {
            "stroke": "rgb(" + color.join(',') + ")",
            "stroke-width": "2"
          });
      if (newLineId) {
        boundingBoxLines[lineCacheKey] = newLineId;
      }
    }
  }
  // Remove the lines that are no longer needed
  for (let lineLocator of boundingBoxLinesToRemove) {
    if (props.viewer.removeLine3D(boundingBoxLines[lineLocator])) {
      delete boundingBoxLines[lineLocator];
    }
  }
}

function toggleShowDistances() {
  showDistances.value = !showDistances.value;
  updateDistances();
}

let distanceLines: { [points: string]: number } = {}

function updateDistances() {
  if (!showDistances.value || selected.value.length != 2) {
    for (let lineId of Object.values(distanceLines)) {
      props.viewer?.removeLine3D(lineId);
    }
    distanceLines = {};
    return;
  }

  // Set up the line cache (for delta updates)
  let distanceLinesToRemove = Object.keys(distanceLines);

  function ensureLine(from: Vector3, to: Vector3, text: string, color: string) {
    console.log('ensureLine', from, to, text, color)
    let lineCacheKey = JSON.stringify([from, to]);
    let matchingLine = distanceLines[lineCacheKey];
    if (matchingLine) {
      distanceLinesToRemove = distanceLinesToRemove.filter((l) => l !== lineCacheKey);
    } else {
      distanceLines[lineCacheKey] = props.viewer?.addLine3D(from, to, text, {
        "stroke": color,
        "stroke-width": "2",
        "stroke-dasharray": "5"
      });
    }
  }

  // Add lines (if not already added)
  let objA = selected.value[0].object;
  let objB = selected.value[1].object;
  let {min, center, max} = distances(objA, objB, props.viewer?.scene);
  ensureLine(max[0], max[1], max[1].distanceTo(max[0]).toFixed(1) + "mm", "orange");
  ensureLine(center[0], center[1], center[1].distanceTo(center[0]).toFixed(1) + "mm", "green");
  ensureLine(min[0], min[1], min[1].distanceTo(min[0]).toFixed(1) + "mm", "cyan");

  // Remove the lines that are no longer needed
  for (let lineLocator of distanceLinesToRemove) {
    props.viewer?.removeLine3D(distanceLines[lineLocator]);
    delete distanceLines[lineLocator];
  }

  return;
}

// Add keyboard shortcuts
window.addEventListener('keydown', (event) => {
  if (event.key === 's') {
    if (selectFilter.value == 'Any (S)') toggleSelection();
    else {
      selectFilter.value = 'Any (S)';
      if (!selectionEnabled.value) toggleSelection();
    }
  } else if (event.key === 'f') {
    if (selectFilter.value == '(F)aces') toggleSelection();
    else {
      selectFilter.value = '(F)aces';
      if (!selectionEnabled.value) toggleSelection();
    }
  } else if (event.key === 'e') {
    if (selectFilter.value == '(E)dges') toggleSelection();
    else {
      selectFilter.value = '(E)dges';
      if (!selectionEnabled.value) toggleSelection();
    }
  } else if (event.key === 'v') {
    if (selectFilter.value == '(V)ertices') toggleSelection();
    else {
      selectFilter.value = '(V)ertices';
      if (!selectionEnabled.value) toggleSelection();
    }
  } else if (event.key === 'b') {
    toggleShowBoundingBox();
  } else if (event.key === 'd') {
    toggleShowDistances();
  } else if (event.key === 'h') {
    toggleHighlightNextSelection();
  }
});
</script>

<template>
  <div class="select-parent">
    <v-btn icon @click="toggleSelection" :color="selectionEnabled ? 'surface-light' : ''">
      <v-tooltip activator="parent">{{ selectionEnabled ? 'Disable (s)election mode' : 'Enable (s)election mode' }}
      </v-tooltip>
      <svg-icon type="mdi" :path="mdiCursorDefaultClick"/>
    </v-btn>
    <v-tooltip :text="'Select only '  + selectFilter.toString().toLocaleLowerCase()" :open-on-click="false">
      <template v-slot:activator="{ props }">
        <v-select v-bind="props" class="select-only" variant="underlined"
                  :items="['Any (S)', '(F)aces', '(E)dges', '(V)ertices']"
                  v-model="selectFilter"/>
      </template>
    </v-tooltip>
  </div>
  <v-btn icon @click="toggleHighlightNextSelection" :color="highlightNextSelection[0] ? 'surface-light' : ''">
    <v-tooltip activator="parent">(H)ighlight the next clicked element in the models list</v-tooltip>
    <svg-icon type="mdi" :path="mdiFeatureSearch"/>
  </v-btn>
  <v-btn icon @click="toggleShowBoundingBox" :color="showBoundingBox ? 'surface-light' : ''">
    <v-tooltip activator="parent">{{ showBoundingBox ? 'Hide selection (b)ounds' : 'Show selection (b)ounds' }}
    </v-tooltip>
    <svg-icon type="mdi" :path="mdiCubeOutline"/>
  </v-btn>
  <v-btn icon @click="toggleShowDistances" :color="showDistances ? 'surface-light' : ''">
    <v-tooltip activator="parent">
      {{ showDistances ? 'Hide selection (d)istances' : 'Show (d)istances (when a pair of features is selected)' }}
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