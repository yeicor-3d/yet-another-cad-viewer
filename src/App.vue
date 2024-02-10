<script setup lang="ts">
import ModelViewer from './ModelViewer.vue'

import {ref} from "vue";
import Loading from "./Loading.vue";

// Open models by default on wide screens
let modelsOpened = ref(window.innerWidth > 600);
</script>

<template>
  <v-layout full-height>
    <v-btn icon="$menu" @click="modelsOpened = !modelsOpened" style="position: absolute; z-index: 1"/>
    <v-navigation-drawer v-model="modelsOpened" permanent>
      <v-toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
        <v-toolbar-items>
          <v-btn icon="$close" @click="modelsOpened = !modelsOpened"/>
        </v-toolbar-items>
      </v-toolbar>
      <v-list density="compact" nav> <!-- TODO: Accordion -->
        <v-list-item><Loading/></v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-main >
      <ModelViewer/>
    </v-main>
  </v-layout>
</template>

<style>
html, body {
  height: 100%;
}
</style>