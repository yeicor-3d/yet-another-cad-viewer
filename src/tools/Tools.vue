<script setup lang="ts">
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
} from "vuetify/lib/components";
import OrientationGizmo from "./OrientationGizmo.vue";
import type {PerspectiveCamera} from "three/src/cameras/PerspectiveCamera";
import {OrthographicCamera} from "three/src/cameras/OrthographicCamera";
import {mdiClose, mdiCrosshairsGps, mdiDownload, mdiGithub, mdiLicense, mdiProjector} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';
import type {ModelViewerElement} from '@google/model-viewer';
import type {Intersection} from "three";
import type {MObject3D} from "./Selection.vue";
import Loading from "../misc/Loading.vue";
import type ModelViewerWrapper from "./viewer/ModelViewerWrapper.vue";
import {defineAsyncComponent, Ref, ref} from "vue";

const SelectionComponent = defineAsyncComponent({
  loader: () => import("./Selection.vue"),
  loadingComponent: () => "Loading...",
  delay: 0,
});

const LicensesDialogContent = defineAsyncComponent({
  loader: () => import("./LicensesDialogContent.vue"),
  loadingComponent: Loading,
  delay: 0,
});


let props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();
const emit = defineEmits<{ findModel: [string] }>()

let selection: Ref<Array<Intersection<typeof MObject3D>>> = ref([]);
let selectionFaceCount = () => selection.value.filter((s) => s.object.type == "Mesh" || s.object.type == "SkinnedMesh").length
let selectionEdgeCount = () => selection.value.filter((s) => s.object.type == "Line").length
let selectionVertexCount = () => selection.value.filter((s) => s.object.type == "Points").length

function syncOrthoCamera(force: boolean) {
  let scene = props.viewer?.scene;
  if (!scene) return;
  let perspectiveCam: PerspectiveCamera = (scene as any).__perspectiveCamera;
  if (force || perspectiveCam && scene.camera != perspectiveCam) {
    // Get zoom level from perspective camera
    let dist = scene.getTarget().distanceToSquared(perspectiveCam.position);
    let w = scene.aspect * dist ** 1.1 / 4000;
    let h = dist ** 1.1 / 4000;
    (scene as any).camera = new OrthographicCamera(-w, w, h, -h, perspectiveCam.near, perspectiveCam.far);
    scene.camera.position.copy(perspectiveCam.position);
    scene.camera.lookAt(scene.getTarget().clone().add(scene.target.position));
    if (force) props.viewer.scene.queueRender() // Force rerender of model-viewer
    requestAnimationFrame(() => syncOrthoCamera(false));
  }
}

let toggleProjectionText = ref('PERSP'); // Default to perspective camera
function toggleProjection() {
  let scene = props.viewer?.scene;
  if (!scene) return;
  let prevCam = scene.camera;
  let wasPerspectiveCamera = prevCam.isPerspectiveCamera;
  if (wasPerspectiveCamera) {
    (scene as any).__perspectiveCamera = prevCam; // Save the default perspective camera
    // This hack also needs to sync the camera position and target
    requestAnimationFrame(() => syncOrthoCamera(true));
  } else {
    // Restore the default perspective camera
    scene.camera = (scene as any).__perspectiveCamera;
    props.viewer.scene.queueRender() // Force rerender of model-viewer
  }
  toggleProjectionText.value = wasPerspectiveCamera ? 'ORTHO' : 'PERSP';
}

async function centerCamera() {
  let viewerEl: ModelViewerElement = props.viewer.elem;
  await viewerEl.updateFraming();
  viewerEl.zoom(3);
}


async function downloadSceneGlb() {
  let viewerEl: ModelViewerElement = props.viewer.elem;
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
</script>

<template>
  <orientation-gizmo :scene="props.viewer.scene" v-if="props.viewer?.scene"/>
  <v-divider/>
  <h5>Camera</h5>
  <v-btn icon @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <v-tooltip activator="parent">Toggle Projection<br/>(currently
      {{ toggleProjectionText === 'PERSP' ? 'perspective' : 'orthographic' }})
    </v-tooltip>
    <svg-icon type="mdi" :path="mdiProjector"></svg-icon>
  </v-btn>
  <v-btn icon @click="centerCamera">
    <v-tooltip activator="parent">Recenter Camera</v-tooltip>
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-divider/>
  <h5>Selection ({{ selectionFaceCount() }}F {{ selectionEdgeCount() }}E {{ selectionVertexCount() }}V)</h5>
  <selection-component :viewer="props.viewer" v-model="selection" @findModel="(name) => emit('findModel', name)"/>
  <v-divider/>
  <v-spacer></v-spacer>
  <h5>Extras</h5>
  <v-btn icon @click="downloadSceneGlb">
    <v-tooltip activator="parent">Download Scene</v-tooltip>
    <svg-icon type="mdi" :path="mdiDownload"/>
  </v-btn>
  <v-dialog id="licenses-dialog" fullscreen>
    <template v-slot:activator="{ props }">
      <v-btn icon v-bind="props">
        <v-tooltip activator="parent">Show Licenses</v-tooltip>
        <svg-icon type="mdi" :path="mdiLicense"/>
      </v-btn>
    </template>
    <template v-slot:default="{ isActive }">
      <v-card>
        <v-toolbar>
          <v-toolbar-title>Licenses</v-toolbar-title>
          <v-spacer>
          </v-spacer>
          <v-btn icon @click="isActive.value = false">
            <svg-icon type="mdi" :path="mdiClose"/>
          </v-btn>
        </v-toolbar>
        <v-card-text>
          <licenses-dialog-content/>
        </v-card-text>
      </v-card>
    </template>
  </v-dialog>
  <v-btn icon @click="openGithub">
    <v-tooltip activator="parent">Open GitHub</v-tooltip>
    <svg-icon type="mdi" :path="mdiGithub"/>
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
</style>