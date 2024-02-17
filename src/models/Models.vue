<script setup lang="ts">
import {VExpansionPanel, VExpansionPanels, VExpansionPanelText, VExpansionPanelTitle} from "vuetify/lib/components";
</script>

<template>
  <v-expansion-panels>
    <v-expansion-panel key="model-id" >
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