<script setup lang="ts">
import {
  VBtn,
  VBtnToggle,
  VCheckboxBtn,
  VDivider,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSlider,
  VSpacer,
  VTooltip,
} from "vuetify/lib/components";
import {extrasNameKey, extrasNameValueHelpers} from "../misc/gltf";
import {Document, Mesh} from "@gltf-transform/core";
import {inject, ref, ShallowRef, watch, Ref} from "vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {
  mdiCircleOpacity,
  mdiCube,
  mdiDelete,
  mdiRectangle,
  mdiRectangleOutline,
  mdiSwapHorizontal,
  mdiVectorRectangle
} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';
import {SceneMgr} from "../misc/scene";
import {BackSide, FrontSide} from "three/src/constants";
import {Box3} from "three/src/math/Box3";
import {Color} from "three/src/math/Color";
import {Plane} from "three/src/math/Plane";
import {Vector3} from "three/src/math/Vector3";

const props = defineProps<{
  meshes: Array<Mesh>,
  viewer: InstanceType<typeof ModelViewerWrapper> | null
}>();
const emit = defineEmits<{ remove: [] }>()

let modelName = props.meshes[0].getExtras()[extrasNameKey] // + " blah blah blah blah blag blah blah blah"

// Reactive properties
const enabledFeatures = defineModel<Array<number>>("enabledFeatures", {default: [0, 1, 2]});
const opacity = defineModel<number>("opacity", {default: 1});
const clipPlaneX = ref(1);
const clipPlaneSwappedX = ref(false);
const clipPlaneY = ref(1);
const clipPlaneSwappedY = ref(false);
const clipPlaneZ = ref(1);
const clipPlaneSwappedZ = ref(false);

// Count the number of faces, edges and vertices
let faceCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.TRIANGLES).length).reduce((a, b) => a + b, 0)
let edgeCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() in [WebGL2RenderingContext.LINE_STRIP, WebGL2RenderingContext.LINES]).length).reduce((a, b) => a + b, 0)
let vertexCount = props.meshes.map((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.POINTS).length).reduce((a, b) => a + b, 0)

// Set initial defaults for the enabled features
if (faceCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 0)
if (edgeCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 1)
if (vertexCount === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 2)

// Listeners for changes in the properties (or viewer reloads)
function onEnabledFeaturesChange(newEnabledFeatures: Array<number>) {
  //console.log('Enabled features may have changed', newEnabledFeatures)
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their visibility based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      let childIsFace = child.type == 'Mesh' || child.type == 'SkinnedMesh'
      let childIsEdge = child.type == 'Line' || child.type == 'LineSegments'
      let childIsVertex = child.type == 'Points'
      if (childIsFace || childIsEdge || childIsVertex) {
        let visible = newEnabledFeatures.includes(childIsFace ? 0 : childIsEdge ? 1 : childIsVertex ? 2 : -1);
        if (child.visible !== visible) {
          child.visible = visible;
          if (child.userData.backChild) child.userData.backChild.visible = visible;
        }
      }
    }
  });
  scene.queueRender()
}

watch(enabledFeatures, onEnabledFeaturesChange);

function onOpacityChange(newOpacity: number) {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their opacity based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  // console.log('Opacity may have changed', newOpacity)
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.material && child.material.opacity !== newOpacity) {
        child.material.transparent = newOpacity < 1;
        child.material.opacity = newOpacity;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender()
}

watch(opacity, onOpacityChange);

let {sceneDocument}: {sceneDocument: ShallowRef<Document>} = inject('sceneDocument');

function onClipPlanesChange() {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  let enabledX = clipPlaneX.value < 1 && !clipPlaneSwappedX.value || clipPlaneX.value > 0 && clipPlaneSwappedX.value;
  let enabledY = clipPlaneY.value < 1 && !clipPlaneSwappedY.value || clipPlaneY.value > 0 && clipPlaneSwappedY.value;
  let enabledZ = clipPlaneZ.value < 1 && !clipPlaneSwappedZ.value || clipPlaneZ.value > 0 && clipPlaneSwappedZ.value;
  // let enabled = [enabledX, enabledY, enabledZ];
  let bbox: Box3;
  if (props.viewer?.renderer && (enabledX || enabledY || enabledZ)) {
    // Global value for all models, once set it cannot be unset (unknown for other models...)
    props.viewer.renderer.threeRenderer.localClippingEnabled = true;
    // Due to model-viewer's camera manipulation, the bounding box needs to be transformed
    bbox = SceneMgr.getBoundingBox(sceneDocument.value);
    bbox.applyMatrix4(sceneModel.matrixWorld);
  }
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.material) {
        if (bbox) {
          let offsetX = bbox.min.x + clipPlaneX.value * (bbox.max.x - bbox.min.x);
          let offsetY = bbox.min.z + clipPlaneY.value * (bbox.max.z - bbox.min.z);
          let offsetZ = bbox.min.y + clipPlaneZ.value * (bbox.max.y - bbox.min.y);
          let planes = [
            new Plane(new Vector3(-1, 0, 0), offsetX),
            new Plane(new Vector3(0, 0, 1), offsetY),
            new Plane(new Vector3(0, -1, 0), offsetZ),
          ];
          if (clipPlaneSwappedX.value) planes[0].negate();
          if (clipPlaneSwappedY.value) planes[1].negate();
          if (clipPlaneSwappedZ.value) planes[2].negate();
          if (!enabledZ) planes.pop();
          if (!enabledY) planes.splice(1, 1);
          if (!enabledX) planes.shift();
          child.material.clippingPlanes = planes;
          if (child.userData.backChild) child.userData.backChild.material.clippingPlanes = planes;
        } else {
          child.material.clippingPlanes = [];
          if (child.userData.backChild) child.userData.backChild.material.clippingPlanes = [];
        }
      }
    }
  });
  scene.queueRender()
}

watch(clipPlaneX, onClipPlanesChange);
watch(clipPlaneY, onClipPlanesChange);
watch(clipPlaneZ, onClipPlanesChange);
watch(clipPlaneSwappedX, onClipPlanesChange);
watch(clipPlaneSwappedY, onClipPlanesChange);
watch(clipPlaneSwappedZ, onClipPlanesChange);
// Clip planes are also affected by the camera position, so we need to listen to camera changes
props.viewer.onElemReady((elem) => elem.addEventListener('camera-change', onClipPlanesChange))

function onModelLoad() {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  // Iterate all primitives of the mesh and set their visibility based on the enabled features
  // Use the scene graph instead of the document to avoid reloading the same model, at the cost
  // of not actually removing the primitives from the scene graph
  let childrenToAdd = [];
  sceneModel.traverse((child) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.type == 'Mesh' || child.type == 'SkinnedMesh') {
        // We could implement cutting planes using the stencil buffer:
        // https://threejs.org/examples/?q=clipping#webgl_clipping_stencil
        // But this is buggy for lots of models, so instead we just draw
        // back faces with a different material.
        child.material.side = FrontSide;

        if (modelName !== extrasNameValueHelpers) {
          // The back of the material only writes to the stencil buffer the areas
          // that should be covered by the plane, but does not render anything
          let backChild = child.clone();
          backChild.material = child.material.clone();
          backChild.material.side = BackSide;
          backChild.material.color = new Color(0.25, 0.25, 0.25)
          child.userData.backChild = backChild;
          childrenToAdd.push(backChild);
        }
      }
      // if (child.type == 'Line' || child.type == 'LineSegments') {
      // child.material.linewidth = 3; // Not supported in WebGL2
      // If wide lines are really needed, we need https://threejs.org/examples/?q=line#webgl_lines_fat
      // }
      if (child.type == 'Points') {
        child.material.size = 5;
        child.material.needsUpdate = true;
      }
    }
  });
  childrenToAdd.forEach((child) => sceneModel.add(child));
  scene.queueRender()

  // Furthermore...
  // Enabled features may have been reset after a reload
  onEnabledFeaturesChange(enabledFeatures.value)
  // Opacity may have been reset after a reload
  onOpacityChange(opacity.value)
  // Clip planes may have been reset after a reload
  onClipPlanesChange()
}

// props.viewer.elem may not yet be available, so we need to wait for it
props.viewer.onElemReady((elem) => elem.addEventListener('load', onModelLoad))
</script>

<template>
  <v-expansion-panel :value="modelName">
    <v-expansion-panel-title expand-icon="hide-this-icon" collapse-icon="hide-this-icon">
      <v-btn-toggle v-model="enabledFeatures" multiple @click.stop color="surface-light">
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Faces ({{ faceCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiRectangle" :rotate="90"></svg-icon>
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Edges ({{ edgeCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiRectangleOutline" :rotate="90"></svg-icon>
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Vertices ({{ vertexCount }})</v-tooltip>
          <svg-icon type="mdi" :path="mdiVectorRectangle" :rotate="90"></svg-icon>
        </v-btn>
      </v-btn-toggle>
      <div class="model-name">{{ modelName }}</div>
      <v-spacer></v-spacer>
      <v-btn icon @click.stop="emit('remove')">
        <v-tooltip activator="parent">Remove</v-tooltip>
        <svg-icon type="mdi" :path="mdiDelete"></svg-icon>
      </v-btn>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-slider v-model="opacity" hide-details min="0" max="1" :step="0.1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Change opacity</v-tooltip>
          <svg-icon type="mdi" :path="mdiCircleOpacity"></svg-icon>
        </template>
      </v-slider>
      <v-divider></v-divider>
      <v-slider v-model="clipPlaneX" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Clip plane X</v-tooltip>
          <svg-icon type="mdi" :path="mdiCube" :rotate="120"></svg-icon>
          X
        </template>
        <template v-slot:append>
          <v-tooltip activator="parent">Swap clip plane X</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-checkbox-marked-outline" falseIcon="mdi-checkbox-blank-outline"
                          v-model="clipPlaneSwappedX">
            <template v-slot:label>
              <svg-icon type="mdi" :path="mdiSwapHorizontal"></svg-icon>
            </template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-model="clipPlaneY" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Clip plane Y</v-tooltip>
          <svg-icon type="mdi" :path="mdiCube" :rotate="-120"></svg-icon>
          Y
        </template>
        <template v-slot:append>
          <v-tooltip activator="parent">Swap clip plane Y</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-checkbox-marked-outline" falseIcon="mdi-checkbox-blank-outline"
                          v-model="clipPlaneSwappedY">
            <template v-slot:label>
              <svg-icon type="mdi" :path="mdiSwapHorizontal"></svg-icon>
            </template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-model="clipPlaneZ" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Clip plane Z</v-tooltip>
          <svg-icon type="mdi" :path="mdiCube"></svg-icon>
          Z
        </template>
        <template v-slot:append>
          <v-tooltip activator="parent">Swap clip plane Z</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-checkbox-marked-outline" falseIcon="mdi-checkbox-blank-outline"
                          v-model="clipPlaneSwappedZ">
            <template v-slot:label>
              <svg-icon type="mdi" :path="mdiSwapHorizontal"></svg-icon>
            </template>
          </v-checkbox-btn>
        </template>
      </v-slider>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
/* Fix bug in hidden expansion panel text next to active expansion panel */
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}

/* More compact accordions */
.v-expansion-panel {
  margin-top: 0 !important;
}

.v-expansion-panel-title {
  padding: 0;
}

.v-expansion-panel-title > .v-btn-toggle {
  margin: 0;
  margin-right: 8px;
}

.v-btn {
  --v-btn-height: 16px;
}

.model-name {
  width: 130px;
  min-height: 1.15em; /* HACK: Avoid eating the bottom of the text when using 1 line */
  max-height: 2em;
  text-overflow: ellipsis;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* https://caniuse.com/?search=line-clamp */
  -webkit-box-orient: vertical;
}
</style>

<style>
.v-expansion-panel-text__wrapper {
  padding: 0 !important;
}

.hide-this-icon {
  display: none !important;
}

.mdi-checkbox-blank-outline { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,5V19H5V5H19Z"/></svg>');
}

.mdi-checkbox-marked-outline { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M19,19H5V5H15V3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V11H19M7.91,10.08L6.5,11.5L11,16L21,6L19.59,4.58L11,13.17L7.91,10.08Z"/></svg>');
}
</style>