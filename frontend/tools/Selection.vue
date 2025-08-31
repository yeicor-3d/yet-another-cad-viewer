<script lang="ts" setup>
import {inject, ref, type ShallowRef, watch} from "vue";
import {VBtn, VSelect, VTooltip} from "vuetify/lib/components/index.mjs";
// @ts-expect-error
import SvgIcon from '@jamescoyle/vue-icon';
import type {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {mdiCubeOutline, mdiCursorDefaultClick, mdiFeatureSearch, mdiRuler} from '@mdi/js';
import type {Intersection, Material, Mesh, Object3D} from "three";
import {Box3, Color, Raycaster, Vector3} from "three";
import type ModelViewerWrapperT from "../viewer/ModelViewerWrapper.vue";
import {extrasNameKey} from "../misc/gltf";
import {SceneMgr} from "../misc/scene";
import {Document} from "@gltf-transform/core";
import {AxesColors} from "../misc/helpers";
import {distances} from "../misc/distances";
import {highlight, highlightUndo, hitToSelectionInfo, type SelectionInfo} from "./selection";

export type MObject3D = Mesh & {
  userData: { noHit?: boolean },
  material: Material & {
    color: Color,
    wireframe?: boolean
  }
};

let props = defineProps<{ viewer: typeof ModelViewerWrapperT | null }>();
let emit = defineEmits<{ findModel: [string] }>();
let {setDisableTap} = inject<{ setDisableTap: (arg0: boolean) => void }>('disableTap')!!;
let selectionEnabled = ref(false);
let selected = defineModel<Array<SelectionInfo>>({default: []});
let openNextSelection = ref([false, false]); // Second is whether selection was enabled before
let showBoundingBox = ref<Boolean>(false); // Enabled automatically on start
let showDistances = ref<Boolean>(true);

let mouseDownAt: [number, number] | null = null;
let mouseDownTime = 0;
let selectFilter = ref('Any (S)');
const raycaster = new Raycaster();


let mouseDownListener = (event: MouseEvent) => {
  mouseDownAt = [event.clientX, event.clientY];
  mouseDownTime = performance.now();
  if (!selectionEnabled.value) return;
};

let mouseUpListener = (event: MouseEvent) => {
  // If the mouse moved while clicked (dragging), avoid selection logic
  if (mouseDownAt) {
    let [x, y] = mouseDownAt;
    mouseDownAt = null;
    if (Math.abs(event.clientX - x) > 5 || Math.abs(event.clientY - y) > 5 || performance.now() - mouseDownTime > 500) {
      return;
    }
  }

  // If disabled, avoid selection logic
  if (!selectionEnabled.value) {
    return;
  }

  // Set raycaster parameters
  let paramScale = 1; // Make it easier to select vertices/edges based on camera distance
  if (props.viewer?.scene) {
    let scene = props.viewer.scene;
    let lookAtCenter = scene.getTarget().clone().add(scene.target.position);
    paramScale = scene.camera.position.distanceTo(lookAtCenter) / 150;
    // console.log('paramScale', paramScale)
  }
  if (selectFilter.value === 'Any (S)') {
    raycaster.params.Line.threshold = paramScale;
    raycaster.params.Points.threshold = paramScale * 2;  // Make vertices easier to select than edges
  } else if (selectFilter.value === '(E)dges') {
    raycaster.params.Line.threshold = paramScale;
    raycaster.params.Points.threshold = 0.0;
  } else if (selectFilter.value === '(V)ertices') {
    raycaster.params.Line.threshold = 0.0;
    raycaster.params.Points.threshold = paramScale;
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
    // Need to fix the ray direction for ortho camera FIXME: Still buggy for off-center clicks
    raycaster.ray.direction.copy(scene.camera.getWorldDirection(new Vector3()));
  }
  //console.log('Ray', raycaster.ray);

  // DEBUG: Draw the ray
  // let actualFrom = scene.getTarget().clone().add(raycaster.ray.origin);
  // let actualTo = actualFrom.clone().add(raycaster.ray.direction.clone().multiplyScalar(50));
  // let lineHandle = props.viewer?.addLine3D(actualFrom, actualTo, "Ray")
  // setTimeout(() => props.viewer?.removeLine3D(lineHandle), 30000)

  // Find all hit objects and raycast the wanted ones based on the filter
  let objects: Array<any> = [];
  scene.traverse((obj) => {
    const kind = obj.type
    let isFace = kind === 'Mesh' || kind === 'SkinnedMesh';
    let isEdge = kind === 'Line' || kind === 'LineSegments';
    let isVertex = kind === 'Points';
    if (obj.userData.noHit !== true &&
        ((selectFilter.value === 'Any (S)' && (isFace || isEdge || isVertex)) ||
            (selectFilter.value === '(F)aces' && isFace) ||
            (selectFilter.value === '(E)dges' && isEdge) ||
            (selectFilter.value === '(V)ertices' && isVertex))) {
      objects.push(obj);
    }
  });
  //console.log("Raycasting objects", objects)

  // Run the raycaster on the selected objects only searching for the first hit
  // @ts-ignore
  raycaster.firstHitOnly = true;
  const hits = raycaster.intersectObjects(objects, false);
  let hit = hits
      // Check feasibility
      .filter((hit: Intersection<Object3D>) => {
        if (!hit.object) return false;
        const kind = hit.object.type
        let isFace = kind === 'Mesh' || kind === 'SkinnedMesh';
        let isEdge = kind === 'Line' || kind === 'LineSegments';
        let isVertex = kind === 'Points';
        const kindOk = (selectFilter.value === 'Any (S)') ||
            (isFace && selectFilter.value === '(F)aces') ||
            (isEdge && selectFilter.value === '(E)dges') ||
            (isVertex && selectFilter.value === '(V)ertices');
        return (!isFace || hit.object.visible) && kindOk;
      })
      // Sort for highlighting partially hidden edges/vertices
      .sort((a, b) => {
        function lowerIsBetter(hit: Intersection<Object3D>) {
          let score = hit.distance;
          // Faces are easier to hit than 0-width edges/vertices, so we need to adjust scores
          if (hit.object.type === 'Mesh' || hit.object.type === 'SkinnedMesh') score += paramScale;
          // Edges are easier to hit than vertices, so we need to adjust scores
          if (hit.object.type === 'Line' || hit.object.type === 'LineSegments') score += paramScale / 2;
          return score;
        }

        return lowerIsBetter(a) - lowerIsBetter(b);
      })
      // Return the best hit
      [0] as Intersection<MObject3D> | undefined;

  if (!openNextSelection.value[0]) {
    // If we are selecting, toggle the selection or deselect all if no hit
    let selInfo: SelectionInfo | null = null;
    if (hit) selInfo = hitToSelectionInfo(hit);
    //console.log('Hit', hit, 'SelInfo', selInfo);
    if (hit && selInfo !== null) {
      // Toggle selection
      const wasSelected = selected.value.find((m) => m.getKey() === selInfo.getKey()) !== undefined;
      if (wasSelected) {
        deselect(selInfo)
      } else {
        select(selInfo)
      }
    } else {
      deselectAll();
    }
    updateBoundingBox();
    updateDistances();
  } else if (hit) {
    // Otherwise, highlight the model that owns the hit
    emit('findModel', hit.object.userData[extrasNameKey])
    // And reset the selection mode
    toggleOpenNextSelection()
  }
  scene.queueRender() // Force rerender of model-viewer
}

function select(selInfo: SelectionInfo) {
  // console.log('Selecting', selInfo.object.name)
  if (selected.value.find((m) => m.getKey() === selInfo.getKey()) === undefined) {
    selected.value.push(selInfo);
  }
  highlight(selInfo);
}

function deselect(selInfo: SelectionInfo, alsoRemove = true) {
  // console.log('Deselecting', selInfo.object.name)
  if (alsoRemove) {
    // Remove the matching object from the selection
    let toRemove = selected.value.findIndex((m) => m.getKey() === selInfo.getKey());
    selected.value.splice(toRemove, 1);
  }
  highlightUndo(selInfo);
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

function toggleOpenNextSelection() {
  openNextSelection.value = [
    !openNextSelection.value[0],
    openNextSelection.value[0] ? (openNextSelection.value[1] ?? false) : selectionEnabled.value
  ];
  if (openNextSelection.value[0]) {
    // Reuse selection code to identify the model
    if (!selectionEnabled.value) toggleSelection()
  } else {
    if (selectionEnabled.value !== openNextSelection.value[1]) toggleSelection()
    openNextSelection.value = [false, false];
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
let onViewerReady = (viewer: typeof ModelViewerWrapperT) => {
  if (!viewer) return;
  // props.viewer.elem may not yet be available, so we need to wait for it
  viewer.onElemReady((elem: ModelViewerElement) => {
    if (hasListeners) return;
    hasListeners = true;
    elem.addEventListener('mousedown', mouseDownListener); // Avoid clicking when dragging
    elem.addEventListener('mouseup', mouseUpListener);
    elem.addEventListener('before-render', () => {
      // After a reload of the scene, we need to recover object references and highlight them again
      for (let sel of selected.value) {
        let scene = props.viewer?.scene;
        if (!scene) continue;
        let foundObject = null;
        scene.traverse((obj: MObject3D) => {
          if (sel.matches(obj)) {
            foundObject = obj as MObject3D;
          }
        });
        if (foundObject) {
          sel.object = foundObject;
          highlight(sel);
        } else {
          selected.value = selected.value.filter((m) => m.getKey() !== sel.getKey());
        }
      }
      if (firstLoad) {
        toggleShowBoundingBox();
        firstLoad = false;
      }
    });
    elem.addEventListener('camera-change', onCameraChange);
  });
};
if (props.viewer) onViewerReady(props.viewer);
else watch(() => props.viewer, () => onViewerReady(props.viewer as any));

let {sceneDocument} = inject<{ sceneDocument: ShallowRef<Document> }>('sceneDocument')!!;
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
      bb.union(hit.getBox())
    }
  } else {
    let boundingBox = SceneMgr.getBoundingBox(sceneDocument.value);
    if (!boundingBox) return; // No models. Should not happen.
    bb = boundingBox
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
    if (!axisEdges || axisEdges.length === 0) continue;
    let edge: Array<number> = axisEdges[0] ?? [];
    for (let i = 0; i < 2; i++) { // Find the 2nd closest one by running twice dropping the first
      if (!axisEdges || axisEdges.length === 0) break;
      edge = axisEdges[0] ?? [];
      let edgeDist = Infinity;
      let cameraPos: Vector3 = props.viewer?.scene?.camera?.position ?? new Vector3();
      for (let testEdge of axisEdges) {
        if (!testEdge || testEdge.length < 2) continue;
        let cornerA = corners[testEdge[0] ?? 0];
        let cornerB = corners[testEdge[1] ?? 0];
        if (!cornerA || !cornerB) continue;
        let from = new Vector3(...cornerA);
        let to = new Vector3(...cornerB);
        let mid = from.clone().add(to).multiplyScalar(0.5);
        let newDist = cameraPos.distanceTo(mid);
        if (newDist < edgeDist) {
          edge = testEdge;
          edgeDist = newDist;
        }
      }
      axisEdges = axisEdges.filter((e) => e !== edge);
    }
    if (!edge || edge.length < 2) continue;
    let cornerA = corners[edge[0] ?? 0];
    let cornerB = corners[edge[1] ?? 0];
    if (!cornerA || !cornerB) continue;
    let from = new Vector3(...cornerA);
    let to = new Vector3(...cornerB);
    let length = to.clone().sub(from).length();
    if (length < 0.05) continue; // Skip very small edges (e.g. a single point)
    let colorArray = [AxesColors.x, AxesColors.y, AxesColors.z][parseInt(edgeI)];
    let color = colorArray ? colorArray[1] : [255, 255, 255]; // Secondary colors
    let lineCacheKey = JSON.stringify([from, to]);
    let matchingLine = boundingBoxLines[lineCacheKey];
    if (matchingLine) {
      boundingBoxLinesToRemove = boundingBoxLinesToRemove.filter((l) => l !== lineCacheKey);
    } else {
      let newLineId = props.viewer?.addLine3D(from, to,
          length.toFixed(1) + "mm", {
            "stroke": "rgb(" + (color ?? [255, 255, 255]).join(',') + ")",
            "stroke-width": "2"
          });
      if (newLineId) {
        boundingBoxLines[lineCacheKey] = newLineId;
      }
    }
  }
  // Remove the lines that are no longer needed
  for (let lineLocator of boundingBoxLinesToRemove) {
    if (props.viewer?.removeLine3D(boundingBoxLines[lineLocator])) {
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
    // console.log('ensureLine', from, to, text, color)
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
  if (!selected.value[0] || !selected.value[1] || !props.viewer?.scene) return;
  let {min, center, max} = distances(selected.value[0], selected.value[1], props.viewer.scene);
  if (max[0] && max[1]) {
    ensureLine(max[0], max[1], max[1].distanceTo(max[0]).toFixed(1) + "mm", "orange");
  }
  if (center[0] && center[1]) {
    ensureLine(center[0], center[1], center[1].distanceTo(center[0]).toFixed(1) + "mm", "green");
  }
  if (min[0] && min[1]) {
    ensureLine(min[0], min[1], min[1].distanceTo(min[0]).toFixed(1) + "mm", "cyan");
  }

  // Remove the lines that are no longer needed
  for (let lineLocator of distanceLinesToRemove) {
    props.viewer?.removeLine3D(distanceLines[lineLocator]);
    delete distanceLines[lineLocator];
  }

  return;
}

defineExpose({deselect, updateBoundingBox, updateDistances});

// Add keyboard shortcuts
window.addEventListener('keydown', (event) => {
  if ((event.target as any)?.tagName && ((event.target as any).tagName === 'INPUT' || (event.target as any).tagName === 'TEXTAREA')) {
    // Ignore key events when an input is focused, except for text inputs
    return;
  }
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
  } else if (event.key === 'o') {
    toggleOpenNextSelection();
  }
});
</script>

<template>
  <v-btn :color="selectionEnabled ? 'surface-light' : ''" icon @click="toggleSelection">
    <v-tooltip activator="parent">{{ selectionEnabled ? 'Disable (s)election mode' : 'Enable (s)election mode' }}
    </v-tooltip>
    <svg-icon :path="mdiCursorDefaultClick" type="mdi"/>
  </v-btn>
  <v-tooltip :open-on-click="false" :text="'Select only '  + selectFilter.toString().toLocaleLowerCase()">
    <template v-slot:activator="{ props }">
      <v-select v-model="selectFilter" :items="['Any (S)', '(F)aces', '(E)dges', '(V)ertices']" class="select-only"
                v-bind="props"
                variant="underlined"/>
    </template>
  </v-tooltip>
  <v-btn :color="openNextSelection[0] ? 'surface-light' : ''" icon @click="toggleOpenNextSelection">
    <v-tooltip activator="parent">(O)pen the next clicked element in the models list</v-tooltip>
    <svg-icon :path="mdiFeatureSearch" type="mdi"/>
  </v-btn>
  <v-btn :color="showBoundingBox ? 'surface-light' : ''" icon @click="toggleShowBoundingBox">
    <v-tooltip activator="parent">{{ showBoundingBox ? 'Hide selection (b)ounds' : 'Show selection (b)ounds' }}
    </v-tooltip>
    <svg-icon :path="mdiCubeOutline" type="mdi"/>
  </v-btn>
  <v-btn :color="showDistances ? 'surface-light' : ''" icon @click="toggleShowDistances">
    <v-tooltip activator="parent">
      {{ showDistances ? 'Hide selection (d)istances' : 'Show (d)istances (when a pair of features is selected)' }}
    </v-tooltip>
    <svg-icon :path="mdiRuler" type="mdi"/>
  </v-btn>
</template>

<style scoped>
.select-only {
  float: right;
  height: 36px;
  position: relative;
  top: -12px;
  width: calc(100% - 48px);
}
</style>
