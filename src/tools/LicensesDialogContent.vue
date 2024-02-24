<script setup lang="ts">
// License text for all dependencies, only downloaded when/if needed
// @ts-ignore
const licenseText = await import("bundle-text:../../assets/licenses.txt");
</script>

<template>
  <pre class="license-text" v-html="licenseText"/>
</template>

<style scoped>
.license-text {
  white-space: pre-wrap;
}
</style>