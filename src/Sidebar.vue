<script setup lang="ts">
import {ref} from "vue";
import {VBtn, VNavigationDrawer, VToolbar, VToolbarItems} from "vuetify/lib/components";

const props = defineProps({
  openedInit: Boolean,
  side: String,
  width: Number
});

let opened = ref(props.openedInit);
const openIcon = props.side === 'left' ? '$next' : '$prev';

</script>

<template>
  <v-btn :icon="openIcon" @click="opened = !opened" class="open-button" :class="side"/>
  <v-navigation-drawer v-model="opened" permanent :location="side" :width="props.width">
    <v-toolbar density="compact">
      <v-toolbar-items v-if="side == 'right'">
        <slot name="toolbar-items"></slot>
        <v-btn icon="$close" @click="opened = !opened"/>
      </v-toolbar-items>
      <slot name="toolbar"></slot>
      <v-toolbar-items v-if="side == 'left'">
        <slot name="toolbar-items"></slot>
        <v-btn icon="$close" @click="opened = !opened"/>
      </v-toolbar-items>
    </v-toolbar>
    <slot/>
  </v-navigation-drawer>
</template>

<!--suppress CssUnusedSymbol -->
<style scoped>
.open-button {
  position: absolute;
  bottom: 0;
  /*z-index: 1;*/
  border-radius: 0;
}

.open-button.right {
  right: 0;
}
</style>
