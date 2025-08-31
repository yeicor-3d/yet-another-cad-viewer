<script lang="ts" setup>
import {settings} from "../misc/settings";
import {inject, onUpdated, type Ref, ref, watch} from "vue";
import {$renderer, $scene} from "@google/model-viewer/lib/model-viewer-base";
import {$controls} from '@google/model-viewer/lib/features/controls.js';
import {type SmoothControls} from '@google/model-viewer/lib/three-components/SmoothControls';
import {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {Hotspot} from "@google/model-viewer/lib/three-components/Hotspot";
import type {Renderer} from "@google/model-viewer/lib/three-components/Renderer";
import type {Vector3} from "three";
import {BufferGeometry, Mesh} from "three";
import {acceleratedRaycast, computeBoundsTree, disposeBoundsTree} from 'three-mesh-bvh';
import {setupLighting} from "./lighting.ts";

ModelViewerElement.modelCacheSize = 0; // Also needed to avoid tree shaking
//@ts-ignore
BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
//@ts-ignore
BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
//@ts-ignore
Mesh.prototype.raycast = acceleratedRaycast;

const props = defineProps<{ src: string }>();

const elem = ref<ModelViewerElement | null>(null);
const scene = ref<ModelScene | null>(null);
const renderer = ref<Renderer | null>(null);
const controls = ref<SmoothControls | null>(null);

const sett = ref<any | null>(null);
(async () => sett.value = await settings)();

let lastCameraTargetPosition: Vector3 | undefined = undefined;
let lastCameraZoom: number | undefined = undefined;
let lastCameraUrl = props.src.toString();
let initialized = false
onUpdated(() => {
  if (!elem.value) return; // Not ready yet
  if (initialized) return; // Already initialized
  initialized = true;
  elem.value.addEventListener('before-render', () => {
    if (!elem.value) return
    // Extract internals of model-viewer in order to hack unsupported features
    scene.value = elem.value[$scene] as ModelScene;
    renderer.value = elem.value[$renderer] as Renderer;
    controls.value = (elem.value as any)[$controls] as SmoothControls;
    // Recover the camera position if it was set before
    if (lastCameraTargetPosition) {
      // console.log("RESTORING camera position?", lastCameraTargetPosition);
      scene.value.setTarget(-lastCameraTargetPosition.x, -lastCameraTargetPosition.y, -lastCameraTargetPosition.z);
      scene.value.jumpToGoal(); // Avoid move animation
    }
    (async () => {
      let tries = 0
      while (tries++ < 25) {
        if (!lastCameraZoom || !elem.value?.getCameraOrbit()?.radius) break;
        let change = lastCameraZoom - elem.value.getCameraOrbit().radius;
        //console.log("Zooming to", lastCameraZoom, "from", elem.value.getCameraOrbit().radius, "change", change);
        if (Math.abs(change) < 0.001) break;
        elem.value.zoom(-Math.sign(change) * (Math.pow(Math.abs(change) + 1, 0.9) - 1)); // Arbitrary, experimental
        elem.value.jumpCameraToGoal();
        await elem.value.updateComplete;
      }
      //console.log("Ready to save!")
      lastCameraUrl = props.src.toString();
    })();
  });
  elem.value.addEventListener('camera-change', onCameraChange);
  elem.value.addEventListener('progress', (ev) => onProgress((ev as any).detail.totalProgress));
  setupLighting(elem.value);
});

function onCameraChange() {
  // Remember the camera position to keep it in case of scene changes
  if (scene.value && props.src.toString() == lastCameraUrl) {  // Don't overwrite with initial unwanted positions
    lastCameraTargetPosition = scene.value.target.position.clone();
    lastCameraZoom = elem.value?.getCameraOrbit()?.radius;
    //console.log("Saving camera?", lastCameraTargetPosition, lastCameraZoom);
  }
  // Also need to update the SVG overlay
  for (let lineId in lines.value) {
    onCameraChangeLine(lineId as any);
  }
}

// Handles loading the events for <model-viewer>'s slotted progress bar
const progressBar = ref<HTMLElement | null>(null);
const updateBar = ref<HTMLElement | null>(null);
let onProgressHideTimeout: number | null = null;
const onProgress = (totalProgress: number) => {
  if (!progressBar.value || !updateBar.value) return;
  // Update the progress bar and ensure it's visible
  progressBar.value.style.display = 'block';
  progressBar.value.style.opacity = '1'; // Fade in
  updateBar.value.style.width = `${totalProgress * 100}%`;
  // Auto-hide smoothly when no progress is made for a while
  if (onProgressHideTimeout) clearTimeout(onProgressHideTimeout);
  onProgressHideTimeout = setTimeout(() => {
    if (!progressBar.value) return;
    progressBar.value.style.opacity = '0'; // Fade out
    setTimeout(() => {
      if (!progressBar.value) return;
      progressBar.value.style.display = 'none'; // Actually hide
    }, 300); // 0.3s fade out
  }, 1000);
};

const poster = ref<string>("")
const setPosterText = (newText: string) => {
  poster.value = "data:image/svg+xml;charset=utf-8;base64," + btoa(
      '<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg" fill="gray">' +
      '<text x="50%" y="0%" dominant-baseline="middle" text-anchor="middle" font-size="48px">' +
      newText +
      '</text>' +
      '</svg>')
}
setPosterText("Loading...")

class Line3DData {
  startHotspot: HTMLElement = document.body
  endHotspot: HTMLElement = document.body
  start2D: [number, number] = [-1000, -1000];
  end2D: [number, number] = [-1000, -1000];
  lineAttrs: { [key: string]: string } = {"stroke-width": "2", "stroke": "red"}
  centerText?: string = undefined;
  centerTextSize: [number, number] = [0, 0];
}

let nextLineId = 1;  // Avoid 0 (falsy!)
let lines = ref<{ [id: number]: Line3DData }>({});

function positionToHotspot(position: Vector3): string {
  return position.x + ' ' + position.y + ' ' + position.z;
}

function addLine3D(p1: Vector3, p2: Vector3, centerText?: string, lineAttrs: { [key: string]: string } = {
  "stroke-width": "2",
  "stroke": "red",
}): number | null {
  if (!scene.value || !elem.value?.shadowRoot) return null
  let id = nextLineId++;
  let hotspotName1 = 'line' + id + '_start';
  let hotspotName2 = 'line' + id + '_end';
  scene.value.addHotspot(new Hotspot({name: hotspotName1, position: positionToHotspot(p1)}));
  scene.value.addHotspot(new Hotspot({name: hotspotName2, position: positionToHotspot(p2)}));
  lines.value[id] = {
    startHotspot: elem.value.shadowRoot.querySelector('slot[name="' + hotspotName1 + '"]')!!.parentElement!!,
    endHotspot: elem.value.shadowRoot.querySelector('slot[name="' + hotspotName2 + '"]')!!.parentElement!!,
    start2D: [-1000, -1000],
    end2D: [-1000, -1000],
    centerText: centerText,
    centerTextSize: [0, 0],
    lineAttrs: lineAttrs
  };
  scene.value.queueRender() // Needed to update the hotspots
  requestIdleCallback(() => onCameraChangeLine(id), {timeout: 100});
  return id;
}

function removeLine3D(id: number): boolean {
  if (!scene.value || !(id in lines.value)) return false;
  scene.value.removeHotspot(new Hotspot({name: 'line' + id + '_start'}));
  lines.value[id]?.startHotspot.parentElement?.remove()
  scene.value.removeHotspot(new Hotspot({name: 'line' + id + '_end'}));
  lines.value[id]?.endHotspot.parentElement?.remove()
  delete lines.value[id];
  scene.value.queueRender() // Needed to update the hotspots
  return true;
}

let svg = ref<SVGElement | null>(null);

function onCameraChangeLine(lineId: number) {
  if (!(lineId in lines.value) || !(elem.value)) return // Silently ignore (not updated yet)
  // Update start and end 2D positions
  let {x: xB, y: yB} = elem.value.getBoundingClientRect();
  let {x, y} = lines.value[lineId]?.startHotspot.getBoundingClientRect() ?? {x: 0, y: 0};
  if (lines.value[lineId]) lines.value[lineId].start2D = [x - xB, y - yB];
  let {x: x2, y: y2} = lines.value[lineId]?.endHotspot.getBoundingClientRect() ?? {x: 0, y: 0};
  if (lines.value[lineId]) lines.value[lineId].end2D = [x2 - xB, y2 - yB];

  // Update the center text size if needed
  if (svg.value && lines.value[lineId]?.centerText && lines.value[lineId]?.centerTextSize[0] === 0) {
    let text = svg.value.getElementsByClassName('line' + lineId + '_text')[0] as SVGTextElement | undefined;
    if (text) {
      let bbox = text.getBBox();
      if (lines.value[lineId]) lines.value[lineId].centerTextSize = [bbox.width, bbox.height];
    }
  }
}

function onElemReady(callback: (elem: ModelViewerElement) => void) {
  if (elem.value) {
    callback(elem.value);
  } else {
    watch(() => elem.value, (elem) => {
      if (elem) callback(elem);
    });
  }
}

function entries(lines: { [id: number]: Line3DData }): [string, Line3DData][] {
  return Object.entries(lines);
}

defineExpose({elem, onElemReady, scene, renderer, controls, addLine3D, removeLine3D, onProgress, setPosterText});

let {disableTap} = inject<{ disableTap: Ref<boolean> }>('disableTap')!!;
watch(disableTap, (newDisableTap) => {
  if (elem.value) elem.value.disableTap = newDisableTap;
});
</script>

<template>
  <!-- The main 3D model viewer -->
  <model-viewer ref="elem" v-if="sett != null" :ar="sett.arModes.length > 0" :ar-modes="sett.arModes"
                :environment-image="sett.environment" :exposure="sett.exposure" :autoplay="sett.autoplay"
                :orbit-sensitivity="sett.orbitSensitivity" :pan-sensitivity="sett.panSensitivity"
                :poster="poster" :shadow-intensity="sett.shadowIntensity" :skybox-image="sett.skybox"
                :src="props.src" :zoom-sensitivity="sett.zoomSensitivity" alt="The 3D model(s)" camera-controls
                camera-orbit="45deg 45deg auto" interaction-prompt="none" max-camera-orbit="Infinity 180deg auto"
                min-camera-orbit="-Infinity 0deg 5%" style="width: 100%; height: 100%">
    <slot></slot>
    <!-- Add a progress bar to the top of the model viewer -->
    <div ref="progressBar" slot="progress-bar" class="progress-bar">
      <div ref="updateBar" class="update-bar"/>
    </div>
  </model-viewer>

  <!-- The SVG overlay for fake 3D lines attached to the model -->
  <div class="overlay-svg-wrapper">
    <svg ref="svg" class="overlay-svg" height="100%" width="100%" xmlns="http://www.w3.org/2000/svg">
      <g v-for="[lineId, line] in entries(lines)" :key="lineId">
        <line :x1="line.start2D[0]" :x2="line.end2D[0]" :y1="line.start2D[1]"
              :y2="line.end2D[1]" v-bind="line.lineAttrs"/>
        <g v-if="line.centerText !== undefined">
          <rect v-if="line.centerText"
                :height="line.centerTextSize[1] + 4"
                :width="line.centerTextSize[0] + 8"
                :x="(line.start2D[0] + line.end2D[0]) / 2 - line.centerTextSize[0]/2 - 4"
                :y="(line.start2D[1] + line.end2D[1]) / 2 - line.centerTextSize[1]/2 - 2" fill="gray"
                fill-opacity="0.75" rx="4" ry="4" stroke="black"/>
          <text v-if="line.centerText" :class="'line' + lineId + '_text'"
                :x="(line.start2D[0] + line.end2D[0]) / 2" :y="(line.start2D[1] + line.end2D[1]) / 2"
                dominant-baseline="middle" fill="black"
                font-size="16" text-anchor="middle">
            {{ line.centerText }}
          </text>
        </g>
      </g>
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

.progress-bar {
  display: block;
  pointer-events: none;
  width: 100%;
  height: 10%;
  max-height: 2%;
  position: absolute;
  left: 50%;
  top: 0;
  transform: translate3d(-50%, 0%, 0);
  border-radius: 25px;
  box-shadow: 0 3px 10px 3px rgba(0, 0, 0, 0.5), 0 0 5px 1px rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.9);
  background-color: rgba(0, 0, 0, 0.5);
  transition: opacity 0.3s;
}

.update-bar {
  background-color: rgba(255, 255, 255, 0.9);
  width: 0;
  height: 100%;
  border-radius: 25px;
  float: left;
  transition: width 0.3s;
}
</style>
