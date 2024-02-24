<script setup lang="ts">
import {
  VBtn,
  VCard,
  VCardText,
  VDialog,
  VDivider,
  VSpacer,
  VToolbar,
  VToolbarTitle
} from "vuetify/lib/components";
import {Ref, ref, Suspense} from "vue";
import OrientationGizmo from "./OrientationGizmo.vue";
import type {PerspectiveCamera} from "three/src/cameras/PerspectiveCamera";
import {OrthographicCamera} from "three/src/cameras/OrthographicCamera";
import {mdiClose, mdiCrosshairsGps, mdiDownload, mdiGithub, mdiLicense, mdiProjector} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon/lib/svg-icon.vue';
import {SceneMgrRefData} from "../misc/scene";
import type {ModelViewerElement} from '@google/model-viewer';
import type {Intersection} from "three";
import type {MObject3D} from "./Selection.vue";
import Selection from "./Selection.vue";
import LicensesDialogContent from "./LicensesDialogContent.vue";


let props = defineProps<{ refSData: SceneMgrRefData }>();
let selection: Ref<Array<Intersection<typeof MObject3D>>> = ref([]);

function syncOrthoCamera(force: boolean) {
  let scene = props.refSData.viewerScene;
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
    requestAnimationFrame(() => syncOrthoCamera(false));
  }
}

let toggleProjectionText = ref('PERSP'); // Default to perspective camera
function toggleProjection() {
  let scene = props.refSData.viewerScene;
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
  }
  toggleProjectionText.value = wasPerspectiveCamera ? 'ORTHO' : 'PERSP';
}

function centerCamera() {
  let viewer: ModelViewerElement = props.refSData.viewer;
  if (!viewer) return;
  viewer.updateFraming();
}


async function downloadSceneGlb() {
  let viewer = props.refSData.viewer;
  if (!viewer) return;
  const glTF = await viewer.exportScene();
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
  <orientation-gizmo :scene="props.refSData.viewerScene" v-if="props.refSData.viewerScene !== null"/>
  <v-divider/>
  <h5>Camera</h5>
  <v-btn icon @click="toggleProjection"><span class="icon-detail">{{ toggleProjectionText }}</span>
    <svg-icon type="mdi" :path="mdiProjector"></svg-icon>
  </v-btn>
  <v-btn icon @click="centerCamera">
    <svg-icon type="mdi" :path="mdiCrosshairsGps"/>
  </v-btn>
  <v-divider/>
  <h5>Selection ({{ selection.filter((s) => s.face).length }}F {{ selection.filter((s) => !s.face).length }}E)</h5>
  <Suspense>
    <selection :viewer="props.refSData.viewer" :scene="props.refSData.viewerScene" v-model="selection"/>
    <template #fallback>Loading...</template>
  </Suspense>
  <v-divider/>
  <v-spacer></v-spacer>
  <h5>Extras</h5>
  <v-btn icon @click="downloadSceneGlb">
    <svg-icon type="mdi" :path="mdiDownload"/>
  </v-btn>
  <v-dialog id="licenses-dialog" fullscreen>
    <template v-slot:activator="{ props }">
      <v-btn icon v-bind="props">
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
          <Suspense>
            <licenses-dialog-content/>
            <template #fallback>Loading...</template>
          </Suspense>
        </v-card-text>
      </v-card>
    </template>
  </v-dialog>
  <v-btn icon @click="openGithub">
    <svg-icon type="mdi" :path="mdiGithub"/>
  </v-btn>
  <!-- TODO: Licenses button -->
  <!-- TODO: Tooltips for ALL tools -->
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