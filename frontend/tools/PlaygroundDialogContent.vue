<script setup lang="ts">
import {setupMonaco} from "./monaco.ts";
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import {ref, shallowRef} from "vue";
import Loading from "../misc/Loading.vue";
import {asyncRun, pyodideWorker, resetState} from "./pyodide-worker-api.ts";
import {mdiCircleOpacity, mdiClose, mdiLockReset, mdiPlay, mdiReload, mdiRun} from "@mdi/js";
import {VBtn, VCard, VCardText, VSlider, VSpacer, VToolbar, VToolbarTitle} from "vuetify/components";
import SvgIcon from '@jamescoyle/vue-icon';

const props = defineProps<{ initialCode: string }>();
const emit = defineEmits<{ (e: 'close'): void }>()

// ============ LOAD MONACO EDITOR ============
setupMonaco() // Must be called before using the editor

const code = ref(props.initialCode); // TODO: Default code as input (and autorun!)
const outputText = ref(``);

function output(text: string) {
  outputText.value += text; // Append to output
  console.log(text); // Also log to console
  setTimeout(() => { // Scroll to bottom? TODO: Test
    const consoleElement = document.querySelector('.playground-console pre');
    if (consoleElement) {
      consoleElement.scrollTop = consoleElement.scrollHeight;
    }
  }, 0);
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

const running = ref(true);

async function setupPyodide() {
  if (opacity.value == 0.0) opacity.value = 0.9; // User doesn't know how to show code again, reset after reopening
  let firstTime = pyodideWorker === null;
  if (firstTime) {
    resetState();
    output("Loading packages...\n");
    await asyncRun(`import micropip, asyncio
  micropip.set_index_urls(["https://yeicor.github.io/OCP.wasm", "https://pypi.org/simple"])
  await (micropip.install("lib3mf"))
  micropip.add_mock_package("py-lib3mf", "2.4.1", modules={"py_lib3mf": '''from lib3mf import *'''})
  await (micropip.install(["build123d"]))`, output);
    if (props.initialCode != "") {
      await runCode();
      opacity.value = 0.0; // Hide editor after running initial code
    } else {
      output("Ready for custom code.\n");
    }
  } else {
    output("Reusing existing Pyodide instance...\n");
  }
  running.value = false; // Indicate that Pyodide is ready
}

setupPyodide()

async function runCode() {
  output("Running code...\n");
  try {
    running.value = true;
    await asyncRun(code.value, output);
  } catch (e) {
    output(`Error running initial code: ${e}\n`);
  } finally {
    running.value = false; // Indicate that Pyodide is ready
  }
}
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

      <v-btn icon @click="resetState()">
        <svg-icon :path="mdiReload" type="mdi"/>
      </v-btn>

      <v-btn icon @click="runCode()">
        <svg-icon :path="mdiPlay" type="mdi"/>
      </v-btn>

      <v-btn icon @click="emit('close')">
        <svg-icon :path="mdiClose" type="mdi"/>
      </v-btn>
    </v-toolbar>
    <v-card-text class="popup-card-text" :style="opacity == 0 ? `display: none` : ``">
      <!-- Only show content if opacity is greater than 0 -->
      <div class="playground-container">
        <div class="playground-editor">
          <VueMonacoEditor
              v-model:value="code"
              :theme="editorTheme"
              :options="MONACO_EDITOR_OPTIONS"
              language="python"
              @mount="handleMount"
          />
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