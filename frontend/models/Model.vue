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
} from "vuetify/lib/components/index.mjs";
import {extrasNameKey, extrasNameValueHelpers} from "../misc/gltf";
import {Mesh} from "@gltf-transform/core";
import {ref, watch} from "vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {
  mdiCircleOpacity,
  mdiCube,
  mdiDelete,
  mdiRectangle,
  mdiRectangleOutline,
  mdiSwapHorizontal,
  mdiVectorLine,
  mdiVectorRectangle
} from '@mdi/js'
import SvgIcon from '@jamescoyle/vue-icon';
import {BackSide, FrontSide} from "three/src/constants.js";
import {Box3} from "three/src/math/Box3.js";
import {Color} from "three/src/math/Color.js";
import {Plane} from "three/src/math/Plane.js";
import {Vector3} from "three/src/math/Vector3.js";
import type {MObject3D} from "../tools/Selection.vue";
import {toLineSegments} from "../misc/lines.js";
import {settings} from "../misc/settings.js";

const props = defineProps<{
  meshes: Array<Mesh>,
  viewer: InstanceType<typeof ModelViewerWrapper> | null
}>();
const emit = defineEmits<{ remove: [] }>()

let modelName = props.meshes[0].getExtras()[extrasNameKey] // + " blah blah blah blah blag blah blah blah"

// Count the number of faces, edges and vertices
let faceCount = ref(-1);
let edgeCount = ref(-1);
let vertexCount = ref(-1);

// Clipping planes are handled in y-up space (swapped on interface, Z inverted later)
const clipPlaneX = ref(1);
const clipPlaneSwappedX = ref(false);
const clipPlaneY = ref(1);
const clipPlaneSwappedY = ref(false);
const clipPlaneZ = ref(1);
const clipPlaneSwappedZ = ref(false);
const edgeWidth = ref(settings.edgeWidth);

// Misc properties
const enabledFeatures = defineModel<Array<number>>("enabledFeatures", {default: [0, 1, 2]});
const opacity = defineModel<number>("opacity", {default: 1});
const wireframe = ref(false);

// Listeners for changes in the properties (or viewer reloads)
function onEnabledFeaturesChange(newEnabledFeatures: Array<number>) {
  //console.log('Enabled features may have changed', newEnabledFeatures)
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
    if (child.userData[extrasNameKey] === modelName) {
      let childIsFace = child.type == 'Mesh' || child.type == 'SkinnedMesh'
      let childIsEdge = child.type == 'Line' || child.type == 'LineSegments' || child.type == 'LineSegments2'
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

watch(enabledFeatures, onEnabledFeaturesChange, {deep: true});

function onOpacityChange(newOpacity: number) {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
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

function onWireframeChange(newWireframe: boolean) {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.material && child.material.wireframe !== newWireframe) {
        child.material.wireframe = newWireframe;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender()
}

watch(wireframe, onWireframeChange);

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
    // Get the bounding box containing all features of this model
    bbox = new Box3();
    sceneModel.traverse((child: MObject3D) => {
      if (child.userData[extrasNameKey] === modelName) {
        bbox.expandByObject(child);
      }
    });
  }
  sceneModel.traverse((child: MObject3D) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.material) {
        if (bbox?.isEmpty() == false) {
          let offsetX = bbox.min.x + clipPlaneX.value * (bbox.max.x - bbox.min.x);
          let offsetY = bbox.min.y + clipPlaneY.value * (bbox.max.y - bbox.min.y);
          let offsetZ = bbox.min.z + (1 - clipPlaneZ.value) * (bbox.max.z - bbox.min.z);
          let planes = [
            new Plane(new Vector3(-1, 0, 0), offsetX),
            new Plane(new Vector3(0, -1, 0), offsetY),
            new Plane(new Vector3(0, 0, 1), -offsetZ),
          ];
          if (clipPlaneSwappedX.value) planes[0].negate();
          if (clipPlaneSwappedY.value) planes[1].negate();
          if (clipPlaneSwappedZ.value) planes[2].negate();
          if (!enabledZ) planes.pop();
          if (!enabledY) planes.splice(1, 1);
          if (!enabledX) planes.shift();
          child.material.clippingPlanes = planes;
          if (child.userData.backChild && child.userData.backChild.material) child.userData.backChild.material.clippingPlanes = planes;
        } else {
          child.material.clippingPlanes = [];
          if (child.userData.backChild && child.userData.backChild.material) child.userData.backChild.material.clippingPlanes = [];
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
props.viewer!!.onElemReady((elem) => elem.addEventListener('camera-change', onClipPlanesChange))

let edgeWidthChangeCleanup = [] as Array<() => void>;

function onEdgeWidthChange(newEdgeWidth: number) {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  edgeWidthChangeCleanup.forEach((f) => f());
  edgeWidthChangeCleanup = [];
  let linesToImprove: Array<MObject3D> = [];
  sceneModel.traverse((child: MObject3D) => {
    if (child.userData[extrasNameKey] === modelName) {
      if (child.type == 'Line' || child.type == 'LineSegments') {
        // child.material.linewidth = 3; // Not supported in WebGL2
        // Swap geometry with LineGeometry to support widths
        // https://threejs.org/examples/?q=line#webgl_lines_fat
        if (newEdgeWidth > 0) linesToImprove.push(child);
      }
      if (child.type == 'Points') {
        (child.material as any).size = newEdgeWidth > 0 ? newEdgeWidth * 50 : 5;
        child.material.needsUpdate = true;
      }
    }
  });
  linesToImprove.forEach(async (line: MObject3D) => {
    let line2 = await toLineSegments(line.geometry, newEdgeWidth);
    // Update resolution on resize
    let resizeListener = (elem: HTMLElement) => {
      line2.material.resolution.set(elem.clientWidth, elem.clientHeight);
      line2.material.needsUpdate = true;
    };
    props.viewer!!.onElemReady((elem) => {
      elem.addEventListener('resize', () => resizeListener(elem));
      resizeListener(elem);
    });
    // Copy the transform of the original line
    line2.position.copy(line.position);
    line2.computeLineDistances();
    line2.userData = Object.assign({}, line.userData);
    line.parent!.add(line2);
    line.children.forEach((o) => line2.add(o));
    line.visible = false;
    line.userData.niceLine = line2;
    // line.parent!.remove(line); // Keep it for better raycast and selection!
    line2.userData.noHit = true;
    edgeWidthChangeCleanup.push(() => {
      line2.parent!.remove(line2);
      line.visible = true;
      props.viewer!!.onElemReady((elem) => {
        elem.removeEventListener('resize', () => resizeListener(elem));
      });
    });
  });
  scene.queueRender()
}

watch(edgeWidth, onEdgeWidthChange);

function onModelLoad() {
  let scene = props.viewer?.scene;
  let sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;

  // Count the number of faces, edges and vertices
  const isFirstLoad = faceCount.value === -1;
  faceCount.value = props.meshes
      .flatMap((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.TRIANGLES))
      .map(p => (p.getExtras()?.face_triangles_end as any)?.length ?? 1)
      .reduce((a, b) => a + b, 0)
  edgeCount.value = props.meshes
      .flatMap((m) => m.listPrimitives().filter(p => p.getMode() in [WebGL2RenderingContext.LINE_STRIP, WebGL2RenderingContext.LINES]))
      .map(p => (p.getExtras()?.edge_points_end as any)?.length ?? 0)
      .reduce((a, b) => a + b, 0)
  vertexCount.value = props.meshes
      .flatMap((m) => m.listPrimitives().filter(p => p.getMode() === WebGL2RenderingContext.POINTS))
      .map(p => (p.getAttribute("POSITION")?.getCount() ?? 0))
      .reduce((a, b) => a + b, 0)

  // First time: set the enabled features to all provided features
  if (isFirstLoad) {
    if (faceCount.value === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 0)
    else if (!enabledFeatures.value.includes(0)) enabledFeatures.value.push(0)
    if (edgeCount.value === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 1)
    else if (!enabledFeatures.value.includes(1)) enabledFeatures.value.push(1)
    if (vertexCount.value === 0) enabledFeatures.value = enabledFeatures.value.filter((f) => f !== 2)
    else if (!enabledFeatures.value.includes(2)) enabledFeatures.value.push(2)
  }

  // Add darkened back faces for all face objects to improve cutting planes
  let childrenToAdd: Array<MObject3D> = [];
  sceneModel.traverse((child: MObject3D) => {
    child.updateMatrixWorld();  // Objects are mostly static, so ensure updated matrices
    if (child.userData[extrasNameKey] === modelName) {
      if (child.type == 'Mesh' || child.type == 'SkinnedMesh') {
        // Compute a BVH for faster raycasting (MUCH faster selection)
        // @ts-ignore
        child.geometry?.computeBoundsTree({indirect: true}); // indirect to avoid changing index order
        // TODO: Accelerated raycast for lines and points (https://github.com/gkjohnson/three-mesh-bvh/issues/243)
        // TODO: ParallelMeshBVHWorker

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
          backChild.userData.noHit = true;
          child.userData.backChild = backChild;
          childrenToAdd.push(backChild as MObject3D);
        }
      }
    }
  });
  childrenToAdd.forEach((child: MObject3D) => sceneModel.add(child));

  // Furthermore...
  // Enabled features may have been reset after a reload
  onEnabledFeaturesChange(enabledFeatures.value)
  // Opacity may have been reset after a reload
  onOpacityChange(opacity.value)
  // Wireframe may have been reset after a reload
  onWireframeChange(wireframe.value)
  // Clip planes may have been reset after a reload
  onClipPlanesChange()
  // Edge width may have been reset after a reload
  onEdgeWidthChange(edgeWidth.value)

  scene.queueRender()
}

// props.viewer.elem may not yet be available, so we need to wait for it
props.viewer!!.onElemReady((elem) => elem.addEventListener('load', onModelLoad))
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
        <template v-slot:append>
          <v-tooltip activator="parent">Wireframe</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-triangle-outline" falseIcon="mdi-triangle" v-model="wireframe"></v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-if="edgeCount > 0 || vertexCount > 0" v-model="edgeWidth" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Edge and vertex sizes</v-tooltip>
          <svg-icon type="mdi" :path="mdiVectorLine"></svg-icon>
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
      <v-slider v-model="clipPlaneZ" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Clip plane Y</v-tooltip>
          <svg-icon type="mdi" :path="mdiCube" :rotate="-120"></svg-icon>
          Y
        </template>
        <template v-slot:append>
          <v-tooltip activator="parent">Swap clip plane Y</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-checkbox-marked-outline" falseIcon="mdi-checkbox-blank-outline"
                          v-model="clipPlaneSwappedZ">
            <template v-slot:label>
              <svg-icon type="mdi" :path="mdiSwapHorizontal"></svg-icon>
            </template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-model="clipPlaneY" hide-details min="0" max="1">
        <template v-slot:prepend>
          <v-tooltip activator="parent">Clip plane Z</v-tooltip>
          <svg-icon type="mdi" :path="mdiCube"></svg-icon>
          Z
        </template>
        <template v-slot:append>
          <v-tooltip activator="parent">Swap clip plane Z</v-tooltip>
          <v-checkbox-btn trueIcon="mdi-checkbox-marked-outline" falseIcon="mdi-checkbox-blank-outline"
                          v-model="clipPlaneSwappedY">
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

.mdi-triangle { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M1 21h22L12 2"/></svg>');
}

.mdi-triangle-outline { /* HACK: mdi is not fully imported, only required icons... */
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M12 2L1 21h22M12 6l7.53 13H4.47"/></svg>');
}
</style>