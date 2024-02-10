<script setup lang="ts">
import {VBtn, VIcon} from "vuetify/lib/components";
import OrientationGizmo from "./OrientationGizmo.vue";

const props = defineProps({
  modelViewerInfo: Object
});

function toggleProjection() {
  if (!props.modelViewerInfo) return;
  console.log('Toggling projection', props.modelViewerInfo);
}

</script>

<template>
  <orientation-gizmo v-if="props.modelViewerInfo" :scene="props.modelViewerInfo.scene"/>
  <v-btn icon="mdi-projector" @click="toggleProjection"><span class="icon-detail">PERSP</span>
    <v-icon icon="mdi-projector"></v-icon>
  </v-btn>
</template>

<style>
.icon-detail {
  position: absolute;
  top: 10px;
  left: 0;
  font-size: xx-small;
  width: 100%;
  margin: auto;
}

.icon-detail + .v-icon {
  position: relative;
  top: 5px;
}
</style>