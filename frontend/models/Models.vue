<script lang="ts" setup>
import {VExpansionPanels} from "vuetify/lib/components/index.mjs";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {Document, Mesh} from "@gltf-transform/core";
import {extrasNameKey} from "../misc/gltf";
import Model from "./Model.vue";
import {inject, ref, type Ref} from "vue";

const props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();
const emit = defineEmits<{ removeModel: [string] }>()

let {sceneDocument} = inject<{ sceneDocument: Ref<Document> }>('sceneDocument')!!;

const expandedNames = ref<Array<string>>([]);

function meshesList(sceneDocument: Document): Array<Array<Mesh>> {
  // Grouped by shared name
  return sceneDocument.getRoot().listMeshes().reduce((acc, mesh) => {
    let name = mesh.getExtras()[extrasNameKey]?.toString() ?? 'Unnamed';
    let group = acc.find((group) => group[0] && meshName(group[0]) === name);
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
  emit('removeModel', meshName(mesh))
}

function findModel(name: string) {
  if (!expandedNames.value.includes(name)) expandedNames.value.push(name);
}

defineExpose({findModel})
</script>

<template>
  <v-expansion-panels v-for="meshes in meshesList(sceneDocument)" :key="meshes[0] ? meshName(meshes[0]) : 'unnamed'"
                      v-model="expandedNames as any" multiple>
    <model :meshes="meshes" :viewer="props.viewer" @remove="meshes[0] ? onRemove(meshes[0]) : undefined"/>
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
