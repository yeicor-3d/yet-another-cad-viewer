<script setup lang="ts">
import {setupMonaco} from "./monaco.ts";
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import {nextTick, ref, shallowRef} from "vue";
import Loading from "../misc/Loading.vue";
import {newPyodideWorker} from "./pyodide-worker-api.ts";
import {mdiCircleOpacity, mdiClose, mdiPlay, mdiReload, mdiShare} from "@mdi/js";
import {VBtn, VCard, VCardText, VSlider, VSpacer, VToolbar, VToolbarTitle} from "vuetify/components";
import SvgIcon from '@jamescoyle/vue-icon';
import {version as pyodideVersion} from "pyodide";
import {gzip} from 'pako';
import {b66Encode} from "./b66.ts";
import {Base64} from 'js-base64'; // More compatible with binary data from python...
import {NetworkUpdateEvent, NetworkUpdateEventModel} from "../misc/network.ts";

const props = defineProps<{ initialCode: string }>();
const emit = defineEmits<{ close: [], updateModel: [NetworkUpdateEvent] }>()

// ============ LOAD MONACO EDITOR ============
setupMonaco() // Must be called before using the editor

const code = ref(props.initialCode); // TODO: Default code as input (and autorun!)
const outputText = ref(``);

function output(text: string) {
  outputText.value += text; // Append to output
  console.log(text); // Also log to console
  nextTick(() => { // Scroll to bottom
    const consoleElement = document.querySelector('.playground-console');
    if (consoleElement) {
      consoleElement.scrollTop = consoleElement.scrollHeight;
    }
  })
}

const MONACO_EDITOR_OPTIONS = {
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
}

const editorTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? `vs-dark` : `vs`
const editor = shallowRef()
const handleMount = (editorInstance: typeof VueMonacoEditor) => (editor.value = editorInstance)
const opacity = ref(0.9); // Opacity for the editor

// ============ LOAD PYODIDE (ASYNC) ============
let pyodideWorker: ReturnType<typeof newPyodideWorker> | null = (import.meta as any).hot?.data?.pyodideWorker || null;
const running = ref(true);

async function setupPyodide() {
  running.value = true;
  if (opacity.value == 0.0) opacity.value = 0.9; // User doesn't know how to show code again, reset after reopening
  if (pyodideWorker === null) {
    output("Creating new Pyodide worker...\n");
    pyodideWorker = newPyodideWorker({
      indexURL: `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`, // FIXME: Local deployment?
      packages: ["micropip", "sqlite3"], // Faster load if done here
    });
    if ((import.meta as any).hot) (import.meta as any).hot.data.pyodideWorker = pyodideWorker
  } else {
    output("Reusing existing Pyodide instance...\n");
  }
  output("Preloading packages...\n");
  await pyodideWorker.asyncRun(`import micropip, asyncio
micropip.set_index_urls(["https://yeicor.github.io/OCP.wasm", "https://pypi.org/simple"])
await (micropip.install("lib3mf"))
micropip.add_mock_package("py-lib3mf", "2.4.1", modules={"py_lib3mf": '''from lib3mf import *'''})
await (micropip.install(["https://files.pythonhosted.org/packages/67/25/80be117f39ff5652a4fdbd761b061123c5425e379f4b0a5ece4353215d86/yacv_server-0.10.0a4-py3-none-any.whl"]))
from yacv_server import *`, output, output); // Also import yacv_server here for faster custom code execution
  running.value = false; // Indicate that Pyodide is ready
  output("Pyodide worker initialized.\n");
}

async function runCode() {
  if (pyodideWorker === null) {
    output("Pyodide worker is not initialized. Please wait...\n");
    return;
  }
  if (running.value) {
    output("Pyodide is already running. Please wait...\n");
    return;
  }
  output("Running code...\n");
  try {
    running.value = true;
    await pyodideWorker.asyncRun(code.value, output, (msg: string) => {
      // Detect models printed to console (since http server is not available in pyodide)
      if (msg.startsWith(yacvServerModelPrefix)) {
        const modelData = msg.slice(yacvServerModelPrefix.length);
        onModelData(modelData);
      } else {
        output(msg); // Print other messages directly
      }
    });
  } catch (e) {
    output(`Error running initial code: ${e}\n`);
  } finally {
    running.value = false; // Indicate that Pyodide is ready
  }
}

const yacvServerModelPrefix = "yacv_server://model/";

function onModelData(modelData: string) {
  output(`Model data detected... ${modelData.length}B\n`);
  // Decode the model data and emit the event for the interface to handle
  // - Start by finding the end of the initial json object by looking for brackets.
  let i = 0;
  let openBrackets = 0;
  for (; i < modelData.length; i++) {
    if (modelData[i] === '{') openBrackets++;
    else if (modelData[i] === '}') openBrackets--;
    if (openBrackets === 0) break; // Found the end of the JSON object
  }
  if (openBrackets !== 0) throw `Error: Invalid model data received: ${modelData}\n`
  const jsonData = modelData.slice(0, i + 1); // Extract the JSON part and parse it into the proper class
  let modelMetadataRaw = JSON.parse(jsonData);
  const modelMetadata: any = new NetworkUpdateEventModel(modelMetadataRaw.name, "Wait for it...", modelMetadataRaw.hash, modelMetadataRaw.is_remove)
  // console.debug(`Model metadata:`, modelMetadata);
  output(`Model metadata: ${JSON.stringify(modelMetadata)}\n`);
  // - Now decode the rest of the model data which is a single base64 encoded glb file (or an empty string)
  if (!modelMetadata.isRemove) {
    const binaryData = Base64.toUint8Array(modelData.slice(i + 1)); // Extract the base64 part
    console.assert(binaryData.slice(0, 4).toString() == "103,108,84,70", // Ugly...
        "Invalid GLTF binary data received: " + binaryData.slice(0, 4).toString());
    // - Create a Blob from the binary data to be used as a URL
    const blob = new Blob([binaryData], {type: 'model/gltf-binary'});
    modelMetadata.url = URL.createObjectURL(blob); // Set the hacked URL in the model metadata
  }
  // - Emit the event with the model metadata and URL
  let networkUpdateEvent = new NetworkUpdateEvent([modelMetadata], () => {
  });
  emit('updateModel', networkUpdateEvent);
}

function resetWorker() {
  code.value = props.initialCode; // Reset code to initial state
  if (pyodideWorker) {
    pyodideWorker.terminate(); // Terminate existing worker
    pyodideWorker = null; // Reset worker reference
  }
  outputText.value = ``; // Clear output text
  setupPyodide(); // Reinitialize Pyodide
}

function shareLink() {
  const baseUrl = window.location
  const urlParams = new URLSearchParams(baseUrl.search); // Keep all previous URL parameters
  urlParams.set('code', b66Encode(gzip(code.value, {level: 9}))); // Compress and encode the code
  const shareUrl = `${baseUrl.origin}${baseUrl.pathname}?${urlParams.toString()}`;
  output(`Share link ready: ${shareUrl}\n`)
  navigator.clipboard.writeText(shareUrl)
      .then(() => output("Link copied to clipboard!\n"))
      .catch(err => output(`Failed to copy link: ${err}\n`));
}

const reused = (import.meta as any).hot?.data?.pyodideWorker !== undefined;
setupPyodide().then(() => {
  if (props.initialCode != "" && !reused) runCode();
});
</script>

<template>
  <v-card class="popup-card"
          :style="opacity == 0 ? `position: absolute; top: calc(-50vh + 24px); width: calc(100vw - 64px);` : ``">
    <v-toolbar class="popup">
      <v-toolbar-title>Playground</v-toolbar-title>
      <v-spacer></v-spacer>

      <svg-icon :path="mdiCircleOpacity" type="mdi"></svg-icon>
      <v-slider v-model="opacity" :max="1" :min="0" :step="0.1"
                style="max-width: 100px; height: 32px; margin-right: 16px;"></v-slider>

      <!-- TODO: snapshots... -->

      <v-btn icon @click="resetWorker()">
        <svg-icon :path="mdiReload" type="mdi"/>
      </v-btn>

      <v-btn icon @click="runCode()">
        <svg-icon :path="mdiPlay" type="mdi"/>
      </v-btn>

      <v-btn icon @click="shareLink()">
        <svg-icon :path="mdiShare" type="mdi"/>
      </v-btn>

      <v-btn icon @click="emit('close')">
        <svg-icon :path="mdiClose" type="mdi"/>
      </v-btn>
    </v-toolbar>
    <v-card-text class="popup-card-text" :style="opacity == 0 ? `display: none` : ``">
      <!-- Only show content if opacity is greater than 0 -->
      <div class="playground-container">
        <div class="playground-editor">
          <VueMonacoEditor v-model:value="code" :theme="editorTheme" :options="MONACO_EDITOR_OPTIONS"
                           language="python" @mount="handleMount"/>
        </div>
        <div class="playground-console">
          <h3>Console Output</h3>
          <pre>{{ outputText }}</pre> <!-- Placeholder for console output -->
          <Loading v-if="running"/>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.popup-card {
  background-color: #00000000; /* Transparent background */
}

.popup-card-text {
  background-color: #1e1e1e; /* Matches the Monaco editor background */
  opacity: v-bind(opacity);
}

.playground-container {
  display: flex;
  flex-direction: row;
}

.playground-editor {
  flex: 1;
  height: calc(100vh - 150px);
}

.playground-console {
  flex: 0.5;
  padding: 10px;
  overflow-y: auto;
  min-width: 100px;
  height: calc(100vh - 150px);
}

.playground-console pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (min-height: 100vw) {
  /* Adjust layout for vertical space */
  .playground-container {
    flex-direction: column;
  }

  .playground-editor {
    flex: 1;
    min-height: 60vh;
  }

  .playground-editor > * {
    min-height: 60vh;
  }

  .playground-console {
    max-height: calc(40vh - 150px);
  }
}

/* TODO: Adjust more colors on bright mode */
</style>

<style>
/* https://stackoverflow.com/questions/47017753/monaco-editor-dynamically-resizable/71876526#71876526 */
.monaco-editor {
  position: absolute !important;
}
</style>