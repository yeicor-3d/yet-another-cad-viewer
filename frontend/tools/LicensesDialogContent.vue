<script lang="ts" setup>
// License text for all dependencies, only downloaded when/if needed
// @ts-ignore
import licenseText from "../../assets/licenses.txt?raw";
</script>

<template>
  <pre class="license-text" v-html="licenseText"/>
</template>

<style scoped>
.license-text {
  white-space: pre-wrap;
}
</style>