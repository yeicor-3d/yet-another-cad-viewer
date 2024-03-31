<script lang="ts" setup>
import {VCol, VContainer, VProgressCircular, VRow} from "vuetify/lib/components/index.mjs";
</script>

<template>
  <v-container>
    <v-row justify="center" style="height: 100%">
      <v-col align-self="center">
        <v-progress-circular indeterminate style="display: block; margin: 0 auto;"></v-progress-circular>
        <slot/>
      </v-col>
    </v-row>
  </v-container>
</template>