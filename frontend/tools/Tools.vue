<script lang="ts" setup>
import {
  VBtn,
  VCard,
  VCardText,
  VDialog,
  VDivider,
  VSpacer,
  VToolbar,
  VToolbarTitle,
  VTooltip,
} from "vuetify/lib/components/index.mjs";
import OrientationGizmo from "./OrientationGizmo.vue";
import type {PerspectiveCamera} from "three/src/cameras/PerspectiveCamera.js";
import {OrthographicCamera} from "three/src/cameras/OrthographicCamera.js";
import {mdiClose, mdiCrosshairsGps, mdiDownload, mdiGithub, mdiLicense, mdiProjector} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';
import type {ModelViewerElement} from '@google/model-viewer';
import Loading from "../misc/Loading.vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {defineAsyncComponent, ref, type Ref} from "vue";
import type {SelectionInfo} from "./selection";

const SelectionComponent = defineAsyncComponent({
  loader: () => import("./Selection.vue"),
  loadingComponent: () => "Loading...",
  delay: 0,
});
let selectionComp = ref<InstanceType<typeof SelectionComponent> | null>(null);

const LicensesDialogContent = defineAsyncComponent({
  loader: () => import("./LicensesDialogContent.vue"),
  loadingComponent: Loading,
  delay: 0,
});


let props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();
const emit = defineEmits<{ findModel: [string] }>()

let selection: Ref<Array<SelectionInfo>> = ref([]);
let selectionFaceCount = () => selection.value.filter((s) => s.kind == 'face').length
let selectionEdgeCount = () => selection.value.filter((s) => s.kind == 'edge').length
let selectionVertexCount = () => selection.value.filter((s) => s.kind == "vertex").length

function syncOrthoCamera(force: boolean) {
  let scene = props.viewer?.scene;
  if (!scene) return;
  let perspectiveCam: PerspectiveCamera = (scene as any).__perspectiveCamera;
  if (force || perspectiveCam && scene.camera != perspectiveCam) {
    // Get zoom level from perspective camera
    let lookAtCenter = scene.getTarget().clone().add(scene.target.position);
    let perspectiveWidthAtCenter =
        2 * Math.tan(perspectiveCam.fov * Math.PI / 180 / 2) * perspectiveCam.position.distanceTo(lookAtCenter);
    let w = perspectiveWidthAtCenter;
    let h = perspectiveWidthAtCenter / scene.aspect;
    (scene as any).camera = new OrthographicCamera(-w, w, h, -h, perspectiveCam.near, perspectiveCam.far);
    scene.camera.position.copy(perspectiveCam.position);
    scene.camera.rotation.copy(perspectiveCam.rotation);
    if (force) scene.queueRender() // Force rerender of model-viewer
    requestAnimationFrame(() => syncOrthoCamera(false));
  }
}

let toggleProjectionText = ref('PERSP'); // Default to perspective camera
async function toggleProjection() {
  let scene = props.viewer?.scene;
  if (!scene) return;
  let prevCam = scene.camera;
  let wasPerspectiveCamera = prevCam.isPerspectiveCamera;
  if (wasPerspectiveCamera) {
    (scene as any).__perspectiveCamera = prevCam; // Save the default perspective camera
    // This hack also needs to sync the camera position and target
    syncOrthoCamera(true);
  } else {
    // Restore the default perspective camera
    scene.camera = (scene as any).__perspectiveCamera;
    scene.queueRender() // Force rerender of model-viewer
  }
  toggleProjectionText.value = wasPerspectiveCamera ? 'ORTHO' : 'PERSP';
  // The camera change may take a frame to take effect, dispatch the event after a delay
  await new Promise((resolve) => requestAnimationFrame(resolve));
  props.viewer?.elem?.dispatchEvent(new CustomEvent('camera-change', {detail: {source: 'none'}}));
}

async function centerCamera() {
  let viewerEl: ModelViewerElement | null | undefined = props.viewer?.elem;
  if (!viewerEl) return;
  props.viewer?.scene?.setTarget(0, 0, 0); // Center the target
  viewerEl.zoom(-1000000); // Max zoom out
}


async function downloadSceneGlb() {
  let viewerEl: ModelViewerElement | null | undefined = props.viewer?.elem;
  if (!viewerEl) return;
  const glTF = await viewerEl.exportScene({onlyVisible: true, binary: true});
  const file = new File([glTF], "export.glb");
  const link = document.createElement("a");
  link.download = file.name;
  link.href = URL.createObjectURL(file);
  link.click();
}

async function openGithub() {
  window.open('https://github.com/yeicor-3d/yet-another-cad-viewer', '_blank')
}

function removeObjectSelections(objName: string) {
  for (let selInfo of selection.value.filter((s) => s.getObjectName() === objName)) {
    selectionComp.value?.deselect(selInfo);
  }
  selectionComp.value?.updateBoundingBox();
  selectionComp.value?.updateDistances();
}

defineExpose({removeObjectSelections});

// Add keyboard shortcuts
window.addEventListener('keydown', (event) => {
  if (event.key === 'p') toggleProjection();
  else if (event.key === 'c') centerCamera();
  else if (event.key === 'd') downloadSceneGlb();
  else if (event.key === 'g') openGithub();
});
</script>

<template>
  <orientation-gizmo v-if="props.viewer?.scene" :viewer="props.viewer"/>
  <v-divider/>
  <h5>Camera</h5>
  <v-btn icon @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <v-tooltip activator="parent">Toggle (P)rojection<br/>(currently
      {{ toggleProjectionText === 'PERSP' ? 'perspective' : 'orthographic' }})
    </v-tooltip>
    <svg-icon :path="mdiProjector" type="mdi"></svg-icon>
  </v-btn>
  <v-btn icon @click="centerCamera">
    <v-tooltip activator="parent">Re(c)enter Camera</v-tooltip>
    <svg-icon :path="mdiCrosshairsGps" type="mdi"/>
  </v-btn>
  <v-divider/>
  <h5>Selection ({{ selectionFaceCount() }}F {{ selectionEdgeCount() }}E {{ selectionVertexCount() }}V)</h5>
  <selection-component ref="selectionComp" v-model="selection" :viewer="props.viewer as any"
                       @findModel="(name: string) => emit('findModel', name)"/>
  <v-divider/>
  <v-spacer></v-spacer>
  <h5>Extras</h5>
  <v-btn icon @click="downloadSceneGlb">
    <v-tooltip activator="parent">(D)ownload Scene</v-tooltip>
    <svg-icon :path="mdiDownload" type="mdi"/>
  </v-btn>
  <v-dialog id="licenses-dialog" fullscreen>
    <template v-slot:activator="{ props }">
      <v-btn icon v-bind="props">
        <v-tooltip activator="parent">Show Licenses</v-tooltip>
        <svg-icon :path="mdiLicense" type="mdi"/>
      </v-btn>
    </template>
    <template v-slot:default="{ isActive }">
      <v-card>
        <v-toolbar>
          <v-toolbar-title>Licenses</v-toolbar-title>
          <v-spacer>
          </v-spacer>
          <v-btn icon @click="isActive.value = false">
            <svg-icon :path="mdiClose" type="mdi"/>
          </v-btn>
        </v-toolbar>
        <v-card-text>
          <licenses-dialog-content/>
        </v-card-text>
      </v-card>
    </template>
  </v-dialog>
  <v-btn icon @click="openGithub">
    <v-tooltip activator="parent">Open (G)itHub</v-tooltip>
    <svg-icon :path="mdiGithub" type="mdi"/>
  </v-btn>
  <div ref="statsHolder"></div>
</template>

<!--suppress CssUnusedSymbol -->
<style>
.icon-detail {
  position: absolute;
  top: 10px;
  left: 0;
  font-size: xx-small;
  width: 100%;
  margin: auto;
}

.icon-detail + svg {
  position: relative;
  top: 5px;
}

h5 {
  font-size: 14px;
}
</style>
