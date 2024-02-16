<script setup lang="ts">
// TODO: transparent SVG overlay that redirects and grabs some events
//  https://modelviewer.dev/examples/annotations/index.html
</script>

<template>
  <div class="overlay-svg-wrapper">
    <svg class="overlay-svg" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
      <!--  <rect x="0" y="0" width="100%" height="100%" fill="transparent"/>-->
    </svg>
  </div>
</template>

<style scoped>
.overlay-svg-wrapper {
  position: relative;
  top: -100%;
  left: 0;
  width: 100%;
  height: 0;
  pointer-events: none;
  z-index: 1;
}
.overlay-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100dvh;
  pointer-events: none;
}
</style>
