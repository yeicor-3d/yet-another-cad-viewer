<script setup lang="ts">
import {defineAsyncComponent, ref, Ref} from "vue";
import Sidebar from "./Sidebar.vue";
import Loading from "./Loading.vue";
import ModelViewerOverlay from "./ModelViewerOverlay.vue";
import Tools from "./Tools.vue";
import {
  VExpansionPanel,
  VExpansionPanels,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VLayout,
  VMain,
  VToolbarTitle
} from "vuetify/lib/components";
import type {ModelViewerInfo} from "./ModelViewerWrapper.vue";

// NOTE: The ModelViewer library is big, so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});

// Open models by default on wide screens
let openSidebarsDefault: Ref<boolean> = ref(window.innerWidth > 1200);
let modelViewerInfo: Ref<typeof ModelViewerInfo | null> = ref(null);
</script>

<template>
  <v-layout full-height>
    <!-- The main content of the app is the model-viewer with the SVG "2D" overlay -->
    <v-main id="main">
      <model-viewer-wrapper @load-viewer="(args) => {
        console.log('Model-Viewer finished loading:', args)
        modelViewerInfo = args
      }"/>
      <model-viewer-overlay v-if="modelViewerInfo"/>
    </v-main>
    <!-- The left collapsible sidebar has the list of models -->
    <sidebar :opened-init="openSidebarsDefault" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <v-expansion-panels>
        <v-expansion-panel key="model-id">
          <v-expansion-panel-title>? F ? E ? V | Model Name</v-expansion-panel-title>
          <v-expansion-panel-text>
            Content
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </sidebar>
    <!-- The right collapsible sidebar has the list of tools -->
    <sidebar :opened-init="openSidebarsDefault" side="right" :width="120">
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

<!--suppress CssUnusedSymbol -->
<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}
</style>