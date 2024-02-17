<script setup lang="ts">
import {ref} from "vue";
import {VBtn, VNavigationDrawer, VToolbar, VToolbarItems} from "vuetify/lib/components";
import {mdiClose, mdiChevronRight, mdiChevronLeft} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';

const props = defineProps({
  openedInit: Boolean,
  side: String,
  width: Number
});

let opened = ref(props.openedInit);
const openIcon = props.side === 'left' ? mdiChevronRight : mdiChevronLeft;

</script>

<template>
  <v-btn icon="" @click="opened = !opened" class="open-button" :class="side">
    <svg-icon type="mdi" :path="openIcon"/>
  </v-btn>
  <v-navigation-drawer v-model="opened" permanent :location="side" :width="props.width">
    <v-toolbar density="compact">
      <v-toolbar-items v-if="side == 'right'">
        <slot name="toolbar-items"></slot>
        <v-btn icon="" @click="opened = !opened">
          <svg-icon type="mdi" :path="mdiClose"/>
        </v-btn>
      </v-toolbar-items>
      <slot name="toolbar"></slot>
      <v-toolbar-items v-if="side == 'left'">
        <slot name="toolbar-items"></slot>
        <v-btn icon="" @click="opened = !opened">
          <svg-icon type="mdi" :path="mdiClose"/>
        </v-btn>
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
