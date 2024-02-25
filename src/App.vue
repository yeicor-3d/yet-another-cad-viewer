<!--suppress SillyAssignmentJS -->
<script setup lang="ts">
import {defineAsyncComponent, ref, Ref, shallowRef} from "vue";
import Sidebar from "./misc/Sidebar.vue";
import Loading from "./misc/Loading.vue";
import Tools from "./tools/Tools.vue";
import Models from "./models/Models.vue";
import {VBtn, VLayout, VMain, VToolbarTitle} from "vuetify/lib/components";
import {settings} from "./misc/settings";
import {NetworkManager, NetworkUpdateEvent} from "./misc/network";
import {SceneMgr} from "./misc/scene";
import {Document} from "@gltf-transform/core";
import type ModelViewerWrapperT from "./viewer/ModelViewerWrapper.vue";
import {mdiPlus} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';

// NOTE: The ModelViewer library is big (THREE.js), so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./viewer/ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});

let openSidebarsByDefault: Ref<boolean> = ref(window.innerWidth > 1200);

let sceneUrl = ref("")
let viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null> = ref(null);
let document = shallowRef(new Document());
let models: Ref<InstanceType<typeof Models> | null> = ref(null)

async function onModelLoadRequest(model: NetworkUpdateEvent) {
  await SceneMgr.loadModel(sceneUrl, document, model.name, model.url);
  document.value = document.value.clone(); // Force update from this component!
}

function onModelRemoveRequest(name: string) {
  SceneMgr.removeModel(sceneUrl, document, name);
  document.value = document.value.clone(); // Force update from this component!
}

function onFindModel(name: string) {
  Models.value.findModel(name);
}

// Set up the load model event listener
let networkMgr = new NetworkManager();
networkMgr.addEventListener('update', onModelLoadRequest);
// Start loading all configured models ASAP
for (let model of settings.preloadModels) {
  networkMgr.load(model);
}

async function loadModelManual() {
  const modelUrl = prompt("For an improved experience in viewing CAD/GLTF models with automatic updates, it's recommended to use the official yacv_server Python package. This ensures seamless serving of models and automatic updates.\n\nOtherwise, enter the URL of the model to load:");
  if (modelUrl) await networkMgr.load(modelUrl);
}
</script>

<template>
  <v-layout full-height>

    <!-- The main content of the app is the model-viewer with the SVG "2D" overlay -->
    <v-main id="main">
      <model-viewer-wrapper ref="viewer" :src="sceneUrl"/>
    </v-main>

    <!-- The left collapsible sidebar has the list of models -->
    <sidebar :opened-init="openSidebarsByDefault" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <template #toolbar-items>
        <v-btn icon="" @click="loadModelManual">
          <svg-icon type="mdi" :path="mdiPlus"/>
        </v-btn>
      </template>
      <models ref="models" :viewer="viewer" :document="document" @remove="onModelRemoveRequest"/>
    </sidebar>

    <!-- The right collapsible sidebar has the list of tools -->
    <sidebar :opened-init="openSidebarsByDefault" side="right" :width="48 * 3 /* buttons */ + 1 /* border? */">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <tools :viewer="viewer" @findModel="(name) => models.findModel(name)"/>
    </sidebar>

  </v-layout>
</template>

<!--suppress CssUnusedSymbol -->
<style>
html, body {
  height: 100%;
  overflow: hidden;
}
</style>