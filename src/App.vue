<script setup lang="ts">
import ModelViewer from './ModelViewer.vue'

import {ref} from "vue";

let modelsOpened = ref(false)
let toolsOpened = ref(true)
</script>
<
<template>
  <v-card>
    <v-layout>
      <v-btn @click="modelsOpened = !modelsOpened" max-width="22px" style="position:absolute; z-index: 1">&gt;</v-btn>
      <v-navigation-drawer v-model="modelsOpened">
        <v-list density="compact" nav > <!-- TODO: Accordion -->
          <v-list-item-title>Models <v-btn @click="modelsOpened = !modelsOpened" style="float: right" height="22px"><</v-btn></v-list-item-title>
          <v-list-item prepend-icon="mdi-view-dashboard" title="Home" value="home"></v-list-item>
          <v-list-item prepend-icon="mdi-forum" title="About" value="about"></v-list-item>
        </v-list>
      </v-navigation-drawer>
      <v-main style="height: 100vh">
        <ModelViewer/>
      </v-main>
      <v-navigation-drawer location="right" v-model="toolsOpened" opa>
        <v-list density="compact" nav >
          <v-list-item-title>Tools</v-list-item-title>
          <v-list-item prepend-icon="mdi-view-dashboard" title="Home" value="home"></v-list-item>
          <v-list-item prepend-icon="mdi-forum" title="About" value="about"></v-list-item>
        </v-list>
      </v-navigation-drawer>
    </v-layout>
  </v-card>
</template>

<style scoped>
</style>