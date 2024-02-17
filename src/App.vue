<script setup lang="ts">
import {defineAsyncComponent, ref, Ref} from "vue";
import Sidebar from "./misc/Sidebar.vue";
import Loading from "./misc/Loading.vue";
import ModelViewerOverlay from "./viewer/ModelViewerOverlay.vue";
import Tools from "./tools/Tools.vue";
import Models from "./models/Models.vue";
import {VLayout, VMain, VToolbarTitle} from "vuetify/lib/components";
import type {ModelViewerInfo} from "./viewer/ModelViewerWrapper.vue";
import {settings} from "./misc/settings";

// NOTE: The ModelViewer library is big (THREE.js), so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./viewer/ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});

let openSidebarsByDefault: Ref<boolean> = ref(window.innerWidth > 1200);
let modelViewerInfo: Ref<typeof ModelViewerInfo | null> = ref(null);
let modelSrc: Ref<string | Uint8Array> = ref(settings.preloadModels[0]);
</script>

<template>
  <v-layout full-height>

    <!-- The main content of the app is the model-viewer with the SVG "2D" overlay -->
    <v-main id="main">
      <model-viewer-wrapper :src="modelSrc" @load-viewer="(args) => modelViewerInfo = args"/>
      <model-viewer-overlay v-if="modelViewerInfo"/>
    </v-main>

    <!-- The left collapsible sidebar has the list of models -->
    <sidebar :opened-init="openSidebarsByDefault" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <models :modelViewerInfo="modelViewerInfo"/>
    </sidebar>

    <!-- The right collapsible sidebar has the list of tools -->
    <sidebar :opened-init="openSidebarsByDefault" side="right" :width="120">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <tools :modelViewerInfo="modelViewerInfo"/>
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