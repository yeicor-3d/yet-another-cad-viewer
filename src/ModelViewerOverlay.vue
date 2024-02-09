<script setup lang="ts">
// TODO: transparent SVG overlay that redirects and grabs some events
//  https://modelviewer.dev/examples/annotations/index.html
</script>

<template>
<svg class="overlay-svg" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
<!--  <rect x="0" y="0" width="100%" height="100%" fill="transparent"/>-->
</svg>
</template>

<style scoped>
.overlay-svg {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
</style>
