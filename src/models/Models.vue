<script setup lang="ts">
import {VExpansionPanel, VExpansionPanels, VExpansionPanelText, VExpansionPanelTitle} from "vuetify/lib/components";
</script>

<template>
  <v-expansion-panels>
    <v-expansion-panel key="model-id">
      <v-expansion-panel-title>? F ? E ? V | Model Name</v-expansion-panel-title>
      <v-expansion-panel-text>Content</v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<!--suppress CssUnusedSymbol -->
<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}
</style>

<style>
.mdi-chevron-down, .mdi-menu-down { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 10l5 5 5-5H7z"/></svg>');
}

.v-overlay--active > .v-overlay__content {
  display: block !important; /* HACK: Fix buggy tooltips not showing? */
}
</style>