<script setup lang="ts">
import {VExpansionPanels} from "vuetify/lib/components";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import Loading from "../misc/Loading.vue";
import {Document, Mesh} from "@gltf-transform/core";
import {extrasNameKey} from "../misc/gltf";
import Model from "./Model.vue";
import {ref} from "vue";

const props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null, document: Document }>();
const emit = defineEmits<{ remove: [string] }>()

let expandedNames = ref<Array<string>>([]);

function meshesList(document: Document): Array<Array<Mesh>> {
  // Grouped by shared name
  return document.getRoot().listMeshes().reduce((acc, mesh) => {
    let name = mesh.getExtras()[extrasNameKey]?.toString() ?? 'Unnamed';
    let group = acc.find((group) => meshName(group[0]) === name);
    if (group) {
      group.push(mesh);
    } else {
      acc.push([mesh]);
    }
    return acc;
  }, [] as Array<Array<Mesh>>);
}

function meshName(mesh: Mesh) {
  return mesh.getExtras()[extrasNameKey]?.toString() ?? 'Unnamed';
}

function onRemove(mesh: Mesh) {
  emit('remove', meshName(mesh))
}

function findModel(name: string) {
  console.log('Find model', name);
  if (!expandedNames.value.includes(name)) expandedNames.value.push(name);
  console.log('Expanded', expandedNames.value);
}

defineExpose({findModel})
</script>

<template>
  <Loading v-if="!props.document"/>
  <v-expansion-panels v-else v-for="meshes in meshesList(props.document)" :key="meshName(meshes[0])"
                      v-model="expandedNames" multiple>
    <model :meshes="meshes" :viewer="props.viewer" :document="props.document" @remove="onRemove(meshes[0])"/>
  </v-expansion-panels>
</template>

<style>
.mdi-chevron-down, .mdi-menu-down { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 10l5 5 5-5H7z"/></svg>');
}

.mdi-chevron-up, .mdi-menu-up { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 14l5-5 5 5H7z"/></svg>');
}

.v-overlay--active > .v-overlay__content {
  display: block !important; /* HACK: Fix buggy tooltips not showing? */
}
</style>