<script setup lang="ts">
import ModelViewerOverlay from "./ModelViewerOverlay.vue";
import Loading from "./Loading.vue";
import {defineAsyncComponent} from "vue";

// NOTE: The ModelViewer library is big, so we split it and import it asynchronously
const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import('./ModelViewerWrapper.vue'),
  loadingComponent: Loading,
  delay: 0,
});
</script>

<template>
</template>

<style scoped>
</style>