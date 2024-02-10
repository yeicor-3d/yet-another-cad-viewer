<script setup lang="ts">
import {defineAsyncComponent, ref} from "vue";
import Sidebar from "./Sidebar.vue";
import Loading from "./Loading.vue";
import ModelViewerOverlay from "./ModelViewerOverlay.vue";

// NOTE: The ModelViewer library is big, so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});

// Open models by default on wide screens
let openSidebars = ref(window.innerWidth > 1200);
</script>

<template>
  <v-layout full-height>
    <!-- The main content of the app is the model-viewer with the SVG "2D" overlay -->
    <v-main id="main">
      <model-viewer-wrapper/>
      <model-viewer-overlay/>
    </v-main>
    <!-- The left collapsible sidebar has the list of models -->
    <sidebar :opened-init="openSidebars" side="left">
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
    <sidebar :opened-init="openSidebars" side="right" width="150">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <v-btn>Camera</v-btn>
    </sidebar>
  </v-layout>
</template>

<!--suppress CssUnusedSymbol -->
<style>
html, body, #app, #main {
  height: 100%;
}
</style>

<!--suppress CssUnusedSymbol -->
<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}
</style>