<!--suppress SillyAssignmentJS -->
<script setup lang="ts">
import {defineAsyncComponent, ref, Ref} from "vue";
import Sidebar from "./misc/Sidebar.vue";
import Loading from "./misc/Loading.vue";
import ModelViewerOverlay from "./viewer/ModelViewerOverlay.vue";
import Tools from "./tools/Tools.vue";
import Models from "./models/Models.vue";
import {VLayout, VMain, VToolbarTitle} from "vuetify/lib/components";
import {settings} from "./misc/settings";
import {NetworkManager, NetworkUpdateEvent} from "./misc/network";
import {SceneManagerData, SceneMgr} from "./misc/scene";

// NOTE: The ModelViewer library is big (THREE.js), so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./viewer/ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});

let openSidebarsByDefault: Ref<boolean> = ref(window.innerWidth > 1200);

let [refSData, sData] = SceneMgr.newData();

// Set up the load model event listener
let networkMgr = new NetworkManager();
networkMgr.addEventListener('update', (model: NetworkUpdateEvent) => {
  SceneMgr.loadModel(refSData, sData, model.name, model.url);
});
// Start loading all configured models ASAP
for (let model of settings.preloadModels) {
  networkMgr.load(model);
}
</script>

<template>
  <v-layout full-height>

    <!-- The main content of the app is the model-viewer with the SVG "2D" overlay -->
    <v-main id="main">
      <model-viewer-wrapper :src="refSData.viewerSrc" @load="(i) => SceneMgr.onload(refSData, i)"/>
      <model-viewer-overlay v-if="refSData.viewer !== null"/>
    </v-main>

    <!-- The left collapsible sidebar has the list of models -->
    <sidebar :opened-init="openSidebarsByDefault" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <models/>
    </sidebar>

    <!-- The right collapsible sidebar has the list of tools -->
    <sidebar :opened-init="openSidebarsByDefault" side="right" :width="48 * 3 /* buttons */ + 1">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <tools :ref-s-data="refSData"/>
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