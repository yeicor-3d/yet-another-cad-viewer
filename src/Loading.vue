<script setup lang="ts">
import {VContainer, VRow, VCol, VProgressCircular} from "vuetify/lib/components";
</script>

<template>
  <v-container>
    <v-row justify="center" style="height: 100%">
      <v-col align-self="center">
        <v-progress-circular indeterminate style="display: block; margin: 0 auto;"/>
      </v-col>
    </v-row>
  </v-container>
</template>