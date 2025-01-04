<!--suppress SillyAssignmentJS -->
<script lang="ts" setup>
import {defineAsyncComponent, provide, type Ref, ref, shallowRef, triggerRef, watch} from "vue";
import Sidebar from "./misc/Sidebar.vue";
import Loading from "./misc/Loading.vue";
import Tools from "./tools/Tools.vue";
import Models from "./models/Models.vue";
import {VBtn, VLayout, VMain, VToolbarTitle} from "vuetify/lib/components/index.mjs";
import {settings} from "./misc/settings";
import {NetworkManager, NetworkUpdateEvent, NetworkUpdateEventModel} from "./misc/network";
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

const sceneUrl = ref("")
const viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null> = ref(null);
const sceneDocument = shallowRef(new Document());
provide('sceneDocument', {sceneDocument});
const models: Ref<InstanceType<typeof Models> | null> = ref(null)
const tools: Ref<InstanceType<typeof Tools> | null> = ref(null)
const disableTap = ref(false);
const setDisableTap = (val: boolean) => disableTap.value = val;
provide('disableTap', {disableTap, setDisableTap});

async function onModelUpdateRequest(event: NetworkUpdateEvent) {
  // Trigger progress bar as soon as possible (also triggered earlier for each raw notification)
  if (viewer.value && event.models.length > 0) {
    viewer.value.onProgress(0.10);
  }
  // Load/unload a new batch of models to optimize rendering time
  console.log("Received model update request", event.models);
  let shutdownRequestIndex = event.models.findIndex((model) => model.isRemove == null);
  let shutdownRequest = null;
  if (shutdownRequestIndex !== -1) {
    console.log("Will shut down the connection after this load, as requested by the server");
    shutdownRequest = event.models.splice(shutdownRequestIndex, 1)[0];
  }
  let doc = sceneDocument.value;
  for (let modelIndex in event.models) {
    let isLast = parseInt(modelIndex) === event.models.length - 1;
    let model = event.models[modelIndex];
    tools.value?.removeObjectSelections(model.name);
    try {
      let loadHelpers = (await settings()).loadHelpers;
      if (!model.isRemove) {
        doc = await SceneMgr.loadModel(sceneUrl, doc, model.name, model.url, isLast && loadHelpers, isLast);
      } else {
        doc = await SceneMgr.removeModel(sceneUrl, doc, model.name, isLast && loadHelpers, isLast);
      }
    } catch (e) {
      console.error("Error loading model", model, e);
    }
  }
  if (shutdownRequest !== null) {
    console.log("Shutting down the connection as requested by the server");
    event.disconnect();
  }
  sceneDocument.value = doc
  triggerRef(sceneDocument); // Why not triggered automatically?
}

async function onModelRemoveRequest(name: string) {
  await onModelUpdateRequest(new NetworkUpdateEvent([new NetworkUpdateEventModel(name, "", null, true)], () => {
  }));
}

// Set up the load model event listener
let networkMgr = new NetworkManager();
networkMgr.addEventListener('update-early',
    (e) => viewer.value?.onProgress((e as CustomEvent<Array<any>>).detail.length * 0.01));
networkMgr.addEventListener('update', (e) => onModelUpdateRequest(e as NetworkUpdateEvent));
(async () => { // Start loading all configured models ASAP
  let sett = await settings();
  watch(viewer, (newViewer) => {
    if (newViewer) {
      newViewer.setPosterText('<tspan x="50%" dy="1.2em">Trying to load' +
          ' models from:</tspan>' + sett.preload.map((url: string) => '<tspan x="50%" dy="1.2em">- ' + url + '</tspan>').join(""));
    }
  });
  for (let model of sett.preload) {
    await networkMgr.load(model);
  }
})();

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
    <sidebar :opened-init="openSidebarsByDefault" :width="300" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <template #toolbar-items>
        <v-btn icon="" @click="loadModelManual">
          <svg-icon :path="mdiPlus" type="mdi"/>
        </v-btn>
      </template>
      <models ref="models" :viewer="viewer" @remove="onModelRemoveRequest"/>
    </sidebar>

    <!-- The right collapsible sidebar has the list of tools -->
    <sidebar :opened-init="openSidebarsByDefault" :width="48 * 3 /* buttons */ + 1 /* border? */" side="right">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <tools ref="tools" :viewer="viewer" @findModel="(name) => models?.findModel(name)"/>
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