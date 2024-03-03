<script lang="ts">
</script>

<script setup lang="ts">
import {settings} from "../misc/settings";
import {onMounted, inject, type Ref} from "vue";
import {$scene, $renderer} from "@google/model-viewer/lib/model-viewer-base";
import Loading from "../misc/Loading.vue";
import {ref, watch} from "vue";
import {ModelViewerElement} from '@google/model-viewer';
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {Hotspot} from "@google/model-viewer/lib/three-components/Hotspot";
import type {Renderer} from "@google/model-viewer/lib/three-components/Renderer";
import type {Vector3} from "three";

ModelViewerElement.modelCacheSize = 0; // Also needed to avoid tree shaking

const emit = defineEmits<{ load: [] }>()

const props = defineProps<{ src: string }>();

const elem = ref<ModelViewerElement | null>(null);
const scene = ref<ModelScene | null>(null);
const renderer = ref<Renderer | null>(null);

onMounted(() => {
  if (!elem.value) return;
  elem.value.addEventListener('load', async () => {
    if (!elem.value) return;
    // Delete the initial load banner
    let banner = elem.value.querySelector('.initial-load-banner');
    if (banner) banner.remove();
    // Set the scene and renderer
    scene.value = elem.value[$scene] as ModelScene;
    renderer.value = elem.value[$renderer] as Renderer;
    // Emit the load event
    emit('load')
  });
  elem.value.addEventListener('camera-change', onCameraChange);
});

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
  requestIdleCallback(() => onCameraChangeLine(id));
  return id;
}

function removeLine3D(id: number): boolean {
  if (!scene.value || !(id in lines.value)) return false;
  scene.value.removeHotspot(new Hotspot({name: 'line' + id + '_start'}));
  lines.value[id].startHotspot.parentElement?.remove()
  scene.value.removeHotspot(new Hotspot({name: 'line' + id + '_end'}));
  lines.value[id].endHotspot.parentElement?.remove()
  delete lines.value[id];
  scene.value.queueRender() // Needed to update the hotspots
  return true;
}

function onCameraChange() {
  // Need to update the SVG overlay
  for (let lineId in lines.value) {
    onCameraChangeLine(lineId as any);
  }
}

let svg = ref<SVGElement | null>(null);

function onCameraChangeLine(lineId: number) {
  if (!(lineId in lines.value) || !(elem.value)) return // Silently ignore (not updated yet)
  // Update start and end 2D positions
  let {x: xB, y: yB} = elem.value.getBoundingClientRect();
  let {x, y} = lines.value[lineId].startHotspot.getBoundingClientRect();
  lines.value[lineId].start2D = [x - xB, y - yB];
  let {x: x2, y: y2} = lines.value[lineId].endHotspot.getBoundingClientRect();
  lines.value[lineId].end2D = [x2 - xB, y2 - yB];

  // Update the center text size if needed
  if (svg.value && lines.value[lineId].centerText && lines.value[lineId].centerTextSize[0] === 0) {
    let text = svg.value.getElementsByClassName('line' + lineId + '_text')[0] as SVGTextElement | undefined;
    if (text) {
      let bbox = text.getBBox();
      lines.value[lineId].centerTextSize = [bbox.width, bbox.height];
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

defineExpose({elem, onElemReady, scene, renderer, addLine3D, removeLine3D});

let {disableTap} = inject<{ disableTap: Ref<boolean> }>('disableTap')!!;
watch(disableTap, (value) => {
  // Rerender not auto triggered? This works anyway...
  if (value) elem.value?.setAttribute('disable-tap', '');
  else elem.value?.removeAttribute('disable-tap');
});
</script>

<template>
  <!-- The main 3D model viewer -->
  <model-viewer ref="elem" style="width: 100%; height: 100%" :src="props.src" alt="The 3D model(s)" camera-controls
                camera-orbit="30deg 75deg auto" max-camera-orbit="Infinity 180deg auto"
                min-camera-orbit="-Infinity 0deg 5%" :disable-tap="disableTap" :exposure="settings.exposure"
                :shadow-intensity="settings.shadowIntensity" interaction-prompt="none" :autoplay="settings.autoplay"
                :ar="settings.arModes.length > 0" :ar-modes="settings.arModes" :skybox-image="settings.background"
                :environment-image="settings.background">
    <slot></slot> <!-- Controls, annotations, etc. -->
    <loading class="annotation initial-load-banner"></loading>
  </model-viewer>

  <!-- The SVG overlay for fake 3D lines attached to the model -->
  <div class="overlay-svg-wrapper">
    <svg ref="svg" class="overlay-svg" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
      <g v-for="[lineId, line] in entries(lines)" :key="lineId">
        <line :x1="line.start2D[0]" :y1="line.start2D[1]" :x2="line.end2D[0]"
              :y2="line.end2D[1]" v-bind="line.lineAttrs"/>
        <g v-if="line.centerText !== undefined">
          <rect :x="(line.start2D[0] + line.end2D[0]) / 2 - line.centerTextSize[0]/2 - 4"
                :y="(line.start2D[1] + line.end2D[1]) / 2 - line.centerTextSize[1]/2 - 2"
                :width="line.centerTextSize[0] + 8" :height="line.centerTextSize[1] + 4"
                fill="gray" fill-opacity="0.75" rx="4" ry="4" stroke="black" v-if="line.centerText"/>
          <text :x="(line.start2D[0] + line.end2D[0]) / 2" :y="(line.start2D[1] + line.end2D[1]) / 2"
                text-anchor="middle" dominant-baseline="middle" font-size="16" fill="black"
                :class="'line' + lineId + '_text'" v-if="line.centerText">
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
</style>