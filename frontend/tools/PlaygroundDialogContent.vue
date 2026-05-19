<script setup lang="ts">
import { setupMonaco } from "./monaco.ts";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import { nextTick, onMounted, ref, shallowRef } from "vue";
import Loading from "../misc/Loading.vue";
import { newPyodideWorker } from "./pyodide-worker-api.ts";
import {
    mdiBroom,
    mdiCircleOpacity,
    mdiClose,
    mdiContentSave,
    mdiFolderOpen,
    mdiPlay,
    mdiReload,
    mdiShare,
    mdiUpload,
    mdiBug,
    mdiTextLong,
} from "@mdi/js";
import {
    VBtn,
    VCard,
    VCardText,
    VCardTitle,
    VCardActions,
    VSlider,
    VSpacer,
    VToolbar,
    VToolbarTitle,
    VTooltip,
    VTextField,
    VCheckbox,
    VDialog,
    VDivider,
    VTextarea,
} from "vuetify/components";
// @ts-expect-error
import SvgIcon from "@jamescoyle/vue-icon";
import { version as pyodideVersion } from "pyodide";
import { gzip } from "pako";
import { b64UrlEncode } from "./b64.ts";
import { Base64 } from "js-base64"; // More compatible with binary data from python...
import { NetworkUpdateEvent, NetworkUpdateEventModel } from "../misc/network.ts";
import { settings } from "../misc/settings.ts";
// @ts-expect-error
import playgroundStartupCode from "./PlaygroundStartup.py?raw";
import { uploadFile } from "./upload-file.ts";

const model = defineModel<{ code: string; firstTime: boolean }>({ required: true }); // Initial code should only be set on first load!
const emit = defineEmits<{ close: []; updateModel: [NetworkUpdateEvent] }>();

// ============ LOAD MONACO EDITOR ============
setupMonaco(); // Must be called before using the editor

const outputText = ref(``);
const pgVersion = ref("stable"); // Build123d version
const pgDebug = ref(false); // Use debug wheels (prefer newest .dev OCP WASM wheel versions)
const pgConstraints = ref("asdasd"); // Global package constraints (free text format)
const showConstraintsDialog = ref(false); // Show/hide constraints configuration dialog
let currentWorkerVersion = "stable"; // Track which version the current worker was initialized with
let currentWorkerDebug = false; // Track which debug setting the current worker was initialized with
let currentWorkerConstraints = ""; // Track which constraints the current worker was initialized with
const workerReady = ref(false); // Track if worker successfully initialized

function output(text: string) {
    outputText.value += text; // Append to output
    // Avoid too much output, keep it reasonable
    let max_output = 100000; // 100k characters
    if (outputText.value.length > max_output) {
        outputText.value = outputText.value.slice(-max_output); // Keep only the last 10k characters
    }
    console.log(text); // Also log to console
    nextTick(() => {
        // Scroll to bottom
        const consoleElement = document.querySelector(".playground-console");
        if (consoleElement) {
            consoleElement.scrollTop = consoleElement.scrollHeight;
        }
    });
}

const MONACO_EDITOR_OPTIONS = {
    automaticLayout: true,
    formatOnType: true,
    formatOnPaste: true,
};

const editorTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? `vs-dark` : `vs`;
const editor = shallowRef();
const handleMount = (editorInstance: typeof VueMonacoEditor) => (editor.value = editorInstance);
const opacity = ref(0.9); // Opacity for the editor (overriden when settings are loaded)

// ============ LOAD PYODIDE (ASYNC) ============
let pyodideWorker: ReturnType<typeof newPyodideWorker> | null = (import.meta as any).hot?.data?.pyodideWorker || null;
const running = ref(true);

async function setupPyodide(
    first: boolean,
    loadSnapshot: Uint8Array | undefined = undefined,
    version: string = "stable",
    debug: boolean = false,
    constraints: string = "",
) {
    running.value = true;
    workerReady.value = false;
    try {
        if (opacity.value == 0.0 && !first) opacity.value = 0.9; // User doesn't know how to show code again, reset after reopening
        if (pyodideWorker === null) {
            output("Creating new Pyodide worker...\n");
            try {
                pyodideWorker = newPyodideWorker(
                    Object.assign(
                        {
                            // Note: python wheels are downloaded from the CDN, as we can't know which ones are needed in advance to bundle them
                            // Furthermore, this lets us use the latest version of all wheels including ocp-specific ones without app updates
                            indexURL: `https://cdn.jsdelivr.net/pyodide/v${pyodideVersion}/full/`,
                            packages: ["micropip", "sqlite3"], // Faster load if done here
                            // _makeSnapshot: true, // Enable snapshotting for faster startup (still experimental: breaks loading any packages)
                        },
                        loadSnapshot ? { _loadSnapshot: loadSnapshot } : {},
                    ),
                ); // Load snapshot if provided
                if ((import.meta as any).hot) (import.meta as any).hot.data.pyodideWorker = pyodideWorker;
                currentWorkerVersion = version;
                currentWorkerDebug = debug;
                currentWorkerConstraints = constraints;
            } catch (e) {
                output(`ERR: Failed to create worker: ${e}\n`);
                throw e;
            }
        } else {
            output("Reusing existing Pyodide instance...\n");
        }
        output("Preloading packages...\n");
        try {
            await pyodideWorker.asyncRun(playgroundStartupCode, output, output, version, debug, constraints); // Also import yacv_server and mock ocp_vscode here for faster custom code execution
        } catch (e) {
            output(`ERR: Bootstrap failed: ${e}\n`);
            throw e;
        }
        output("Pyodide worker ready.\n");
        workerReady.value = true;
    } catch (e) {
        output(`ERR: Pyodide setup failed: ${e}\n`);
        running.value = false;
        workerReady.value = false;
        throw e;
    }
    running.value = false; // Indicate that Pyodide is ready
}

async function runCode() {
    if (pyodideWorker === null || !workerReady.value) {
        output("ERR: Pyodide worker not ready. Please wait...\n");
        return;
    }
    if (running.value) {
        output("ERR: Pyodide is already running. Please wait...\n");
        return;
    }

    // Check if version, debug, or constraints changed - if so, reset worker
    if (pgVersion.value !== currentWorkerVersion || pgDebug.value !== currentWorkerDebug || pgConstraints.value !== currentWorkerConstraints) {
        if (pgVersion.value !== currentWorkerVersion) {
            output(`INF: Version changed from ${currentWorkerVersion} to ${pgVersion.value}, resetting worker...\n`);
        }
        if (pgDebug.value !== currentWorkerDebug) {
            output(`INF: Debug mode changed, resetting worker...\n`);
        }
        if (pgConstraints.value !== currentWorkerConstraints) {
            output(`INF: Constraints changed, resetting worker...\n`);
        }
        resetWorker();
        return; // Wait for worker to be ready before running code
    }

    output("Running code...\n");
    running.value = true;
    try {
        await pyodideWorker.asyncRun(
            model.value.code,
            output,
            (msg: string) => {
                // Detect models printed to console (since http server is not available in pyodide)
                if (msg.startsWith(yacvServerModelPrefix)) {
                    try {
                        const modelData = msg.slice(yacvServerModelPrefix.length);
                        onModelData(modelData);
                    } catch (e) {
                        output(`ERR: Failed to process model data: ${e}\n`);
                    }
                } else {
                    output(msg); // Print other messages directly
                }
            },
            pgVersion.value,
        );
        output("Code execution finished successfully.\n");
    } catch (e) {
        output(`ERR: Code execution failed: ${e}\n`);
    } finally {
        running.value = false; // Stop loading state on completion or error
    }
}

const yacvServerModelPrefix = "yacv_server://model/";

function onModelData(modelData: string) {
    try {
        output(`Model data detected... ${modelData.length}B\n`);
        // Decode the model data and emit the event for the interface to handle
        // - Start by finding the end of the initial json object by looking for brackets.
        let i = 0;
        let openBrackets = 0;
        for (; i < modelData.length; i++) {
            if (modelData[i] === "{") openBrackets++;
            else if (modelData[i] === "}") openBrackets--;
            if (openBrackets === 0) break; // Found the end of the JSON object
        }
        if (openBrackets !== 0) throw `Invalid model JSON structure`;
        const jsonData = modelData.slice(0, i + 1); // Extract the JSON part and parse it into the proper class
        let modelMetadataRaw = JSON.parse(jsonData);
        const modelMetadata: any = new NetworkUpdateEventModel(modelMetadataRaw.name, "", modelMetadataRaw.hash, modelMetadataRaw.is_remove);
        // console.debug(`Model metadata:`, modelMetadata);
        output(`Model metadata: ${JSON.stringify(modelMetadata)}\n`);
        // - Now decode the rest of the model data which is a single base64 encoded glb file (or an empty string)
        if (!modelMetadata.isRemove) {
            try {
                const binaryData = Base64.toUint8Array(modelData.slice(i + 1)); // Extract the base64 part
                if (binaryData.slice(0, 4).toString() !== "103,108,84,70") {
                    throw `Invalid GLTF magic bytes: ${binaryData.slice(0, 4).toString()}`;
                }
                // - Save for upload and share link feature
                builtModelsGlb[modelMetadata.name] = binaryData;
                // - Create a Blob from the binary data to be used as a URL
                const blob = new Blob([binaryData as ArrayBufferView<ArrayBuffer>], { type: "model/gltf-binary" });
                modelMetadata.url = URL.createObjectURL(blob); // Set the hacked URL in the model metadata XXX: revoked on App.vue
            } catch (e) {
                throw `Failed to decode GLTF data: ${e}`;
            }
        } else {
            delete builtModelsGlb[modelMetadata.name]; // Remove from built models if it's a remove request
        }
        // - Emit the event with the model metadata and URL
        let networkUpdateEvent = new NetworkUpdateEvent([modelMetadata], () => {});
        emit("updateModel", networkUpdateEvent);
    } catch (e) {
        throw `Model processing error: ${e}`;
    }
}

function resetWorker(loadSnapshot: Uint8Array | undefined = undefined) {
    try {
        if (pyodideWorker) {
            pyodideWorker.terminate(); // Terminate existing worker
            pyodideWorker = null; // Reset worker reference
        }
        workerReady.value = false;
        outputText.value = ``; // Clear output text
        setupPyodide(false, loadSnapshot, pgVersion.value, pgDebug.value, pgConstraints.value); // Reinitialize Pyodide with current settings
    } catch (e) {
        output(`ERR: Failed to reset worker: ${e}\n`);
        running.value = false;
        workerReady.value = false;
    }
}

function shareLinkCommon(added: Record<string, Array<string> | string>, forgotten: Array<string>) {
    const baseUrl = window.location;
    const searchParams = new URLSearchParams(baseUrl.search);
    for (const k of forgotten) searchParams.delete(k);
    const hashParams = new URLSearchParams(baseUrl.hash.slice(1)); // Keep all previous URL parameters
    for (const k of forgotten) hashParams.delete(k);
    for (const k in added) {
        if (Array.isArray(added[k])) {
            for (const v of added[k]) {
                hashParams.append(k, v); // Prefer hash to GET
            }
        } else if (typeof added[k] === "string") {
            hashParams.set(k, added[k]); // Prefer hash to GET
        }
    }
    const shareUrl = `${baseUrl.origin}${baseUrl.pathname}?${searchParams}#${hashParams}`;
    output(`Share link ready: ${shareUrl}\n`);
    if (navigator.clipboard?.writeText === undefined) {
        output("Clipboard API not available. Please copy the link manually.\n");
        return;
    } else {
        navigator.clipboard
            .writeText(shareUrl)
            .then(() => output("Link copied to clipboard!\n"))
            .catch((err) => output(`Failed to copy link: ${err}\n`));
    }
}

function shareLink() {
    const toShare: Record<string, Array<string> | string> = {
        pg_code: b64UrlEncode(gzip(model.value.code, { level: 9 })),
    };
    if (pgVersion.value !== "stable") {
        toShare["pg_version"] = pgVersion.value;
    }
    if (pgDebug.value) {
        toShare["pg_debug"] = "true";
    }
    if (pgConstraints.value !== "") {
        toShare["pg_constraints"] = pgConstraints.value;
    }
    shareLinkCommon(toShare, ["pg_code"]);
}

const builtModelsGlb: Record<string, Uint8Array> = {}; // Store built models to support uploading
async function uploadAndShareLink() {
    try {
        output("Uploading files...\n");

        // Upload code.py
        try {
            const codeBlob = new Blob([model.value.code], { type: "text/x-python" });
            const newParams: Record<string, string | Array<string>> = {
                pg_code: await uploadFile("code.py", new Uint8Array(await codeBlob.arrayBuffer())),
            };

            // Include version if not default
            if (pgVersion.value !== "stable") {
                newParams["pg_version"] = pgVersion.value;
            }

            // Include debug if enabled
            if (pgDebug.value) {
                newParams["pg_debug"] = "true";
            }

            // Include constraints if set
            if (pgConstraints.value !== "") {
                newParams["pg_constraints"] = pgConstraints.value;
            }

            // Upload all models
            newParams["preload"] = [];
            for (const name in builtModelsGlb) {
                try {
                    const glb: any = builtModelsGlb[name];
                    const url = await uploadFile(name + ".glb", glb);
                    newParams["preload"].push(url); // Add to preload list
                } catch (e) {
                    output(`WARN: Failed to upload model ${name}: ${e}\n`);
                }
            }

            // Build share URL
            return shareLinkCommon(newParams, ["pg_code", "pg_version"]);
        } catch (e) {
            throw `Upload failed: ${e}`;
        }
    } catch (e) {
        output(`ERR: ${e}. Falling back to private share link.\n`);
        return shareLink(); // Fallback to private share link if upload fails
    }
}

function saveSnapshot() {
    throw new Error("Not implemented yet!"); // TODO: Implement snapshot saving
}

function loadSnapshot() {
    throw new Error("Not implemented yet!"); // TODO: Implement snapshot loading
}

(async () => {
    let sett: any;
    try {
        sett = await settings;
        if (model.value.firstTime) opacity.value = sett.pg_opacity_loading;
        pgVersion.value = sett.pg_version; // Load version from settings
        pgDebug.value = sett.pg_debug; // Load debug setting from settings
        pgConstraints.value = sett.pg_constraints; // Load constraints from settings
        try {
            await setupPyodide(true, undefined, sett.pg_version, sett.pg_debug, sett.pg_constraints);
        } catch (e) {
            output(`ERR: Initial setup failed: ${e}\n`);
            running.value = false;
            workerReady.value = false;
            if (model.value.firstTime && sett) opacity.value = sett.pg_opacity_loaded;
            return;
        }
        if (model.value.firstTime) {
            try {
                await runCode();
            } catch (e) {
                output(`ERR: Initial code execution failed: ${e}\n`);
            }
            opacity.value = sett.pg_opacity_loaded;
            model.value.firstTime = false;
        }
    } catch (e) {
        output(`ERR: Playground initialization failed: ${e}\n`);
        running.value = false;
        workerReady.value = false;
        if (model.value.firstTime && sett) opacity.value = sett.pg_opacity_loaded;
    }
})();

// Add keyboard shortcuts
const editorRef = ref<HTMLElement | null>(null);
onMounted(() => {
    if (editorRef.value) {
        editorRef.value.addEventListener("keydown", (event: Event) => {
            if (!(event instanceof KeyboardEvent)) return; // Ensure event is a KeyboardEvent
            if (event.key === "F10") {
                // Run code on F10
                event.preventDefault(); // Prevent default behavior of the key
                runCode();
            } else if (event.key === "Escape") {
                // Close on Escape key
                emit("close");
            }
        });
    }
});
</script>

<template>
    <v-card class="popup-card" :style="opacity == 0 ? `position: absolute; top: calc(-50vh + 24px); width: calc(100vw - 64px);` : ``">
        <v-toolbar class="popup">
            <v-toolbar-title style="flex: 0 1 auto">Playground</v-toolbar-title>
            <v-spacer></v-spacer>

            <span style="display: inline-flex; margin-right: 16px">
                <svg-icon :path="mdiCircleOpacity" type="mdi" style="height: 32px"></svg-icon>
                <v-slider v-model="opacity" :max="1" :min="0" :step="0.1" style="width: 100px; height: 32px"> </v-slider>
                <v-tooltip activator="parent" location="bottom">Opacity of the editor (0 = hidden, 1 = fully visible)</v-tooltip>
            </span>

            <span style="padding-left: 12px; width: 48px"
                ><!-- This span is only needed to force tooltip to work while button is disabled -->
                <v-btn icon disabled @click="saveSnapshot()">
                    <svg-icon :path="mdiContentSave" type="mdi" />
                </v-btn>
                <v-tooltip activator="parent" location="bottom">Save current state to a snapshot for fast startup (WIP)</v-tooltip>
            </span>
            <span style="padding-right: 12px; width: 48px"
                ><!-- This span is only needed to force tooltip to work while button is disabled -->
                <v-btn icon disabled @click="loadSnapshot()">
                    <svg-icon :path="mdiFolderOpen" type="mdi" />
                </v-btn>
                <v-tooltip activator="parent" location="bottom">Load snapshot for fast startup (WIP)</v-tooltip>
            </span>

            <v-btn icon @click="shareLink()" style="padding-left: 12px">
                <svg-icon :path="mdiShare" type="mdi" />
                <v-tooltip activator="parent" location="bottom"
                    >Share link that automatically runs the code.<br />Only people with the link can see the code.
                </v-tooltip>
            </v-btn>

            <v-btn icon @click="uploadAndShareLink()" style="padding-right: 12px">
                <svg-icon :path="mdiShare" type="mdi" style="position: absolute; scale: 75%; top: 6px" />
                <svg-icon :path="mdiUpload" type="mdi" style="position: absolute; scale: 75%; bottom: 6px" />
                <v-tooltip activator="parent" location="bottom"
                    >Uploads all models and code and then shares a link to them.<br />Useful to view the models while the playground loads, but uses
                    third-party storage.
                </v-tooltip>
            </v-btn>

            <span style="display: inline-flex; align-items: center; padding-left: 12px">
                <v-text-field
                    v-model="pgVersion"
                    prepend-inner-icon="mdi-source-branch"
                    density="compact"
                    single-line
                    style="position: relative; top: -4px; width: 110px; height: 32px"
                />
                <v-tooltip activator="parent" location="bottom"
                    >Set build123d version: "X.Y.Z" from PyPI ("stable" points to latest), or GitHub ref (branch/tag/commit/pr, e.g. "dev" or
                    "pull/123/head").</v-tooltip
                >
            </span>

            <v-checkbox v-model="pgDebug" density="compact" style="margin-left: 0; margin-right: 0" hide-details>
                <template #prepend>
                    <svg-icon :path="mdiBug" type="mdi" style="height: 24px; margin-left: 12px; margin-right: -20px" />
                    <v-tooltip activator="parent" location="bottom">Use debug wheels with better error/crash reporting.</v-tooltip>
                </template>
                <v-tooltip activator="parent" location="bottom">Use debug wheels with better error/crash reporting.</v-tooltip>
            </v-checkbox>

            <v-btn icon @click="showConstraintsDialog = true" style="padding: 0 8px; margin-right: 12px">
                <svg-icon :path="mdiTextLong" type="mdi" />
                <v-tooltip activator="parent" location="bottom">Configure package constraints</v-tooltip>
            </v-btn>

            <v-btn icon @click="resetWorker()" style="">
                <svg-icon :path="mdiReload" type="mdi" />
                <v-tooltip activator="parent" location="bottom"
                    >Reset Pyodide worker (this forgets all previous state and will take a little while)
                </v-tooltip>
            </v-btn>

            <v-btn icon @click="runCode()" :disabled="running || !workerReady" style="padding-right: 12px">
                <svg-icon :path="mdiPlay" type="mdi" />
                <Loading v-if="running" style="position: absolute; top: -16%; left: -28%" /><!-- Ugly positioning -->
                <v-tooltip activator="parent" location="bottom">Run code{{ !workerReady ? " (worker initializing...)" : "" }}</v-tooltip>
            </v-btn>

            <v-btn icon @click="emit('close')">
                <svg-icon :path="mdiClose" type="mdi" />
                <v-tooltip activator="parent" location="bottom">Close (Pyodide remains loaded)</v-tooltip>
            </v-btn>
        </v-toolbar>

        <v-dialog v-model="showConstraintsDialog" width="500">
            <v-card>
                <v-card-title>Package Constraints Configuration</v-card-title>
                <v-divider></v-divider>
                <v-card-text style="max-height: 60vh; overflow-y: auto">
                    <p style="margin-bottom: 8px">
                        Example (<a
                            href="https://micropip.pyodide.org/en/stable/project/api.html#micropip.install"
                            target="_blank"
                            rel="noopener"
                            style="color: #90caf9; text-decoration: underline"
                            >docs</a
                        >):<br />
                        <code>svgpathtools == 1.7.1<br />yacv_server &gt;= 0.3.0, &lt; 10.4.0<br />font-fetcher != 1.2.3</code><br />
                    </p>
                    <v-textarea v-model="pgConstraints" label="Package constraints (multiline)" rows="1" auto-grow />
                </v-card-text>
                <v-divider></v-divider>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn @click="showConstraintsDialog = false">Close</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
        <v-card-text class="popup-card-text" :style="opacity == 0 ? `display: none` : ``">
            <!-- Only show content if opacity is greater than 0 -->
            <div class="playground-container">
                <div class="playground-editor" ref="editorRef">
                    <VueMonacoEditor
                        v-model:value="model.code"
                        :theme="editorTheme"
                        :options="MONACO_EDITOR_OPTIONS"
                        language="python"
                        @mount="handleMount"
                    />
                </div>
                <div class="playground-console">
                    <h3 style="display: flex; align-items: center; justify-content: space-between; margin: 0">
                        Console Output
                        <v-spacer></v-spacer>
                        <v-btn @click="outputText = ''">
                            <svg-icon :path="mdiBroom" type="mdi" class="h-" />
                        </v-btn>
                    </h3>
                    <pre>{{ outputText }}</pre>
                    <!-- Placeholder for console output -->
                    <Loading v-if="running" />
                </div>
            </div>
        </v-card-text>
    </v-card>
</template>

<style scoped>
.popup-card {
    background-color: #00000000; /* Transparent background */
}

.v-toolbar.popup > * {
    overflow-x: auto;
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

.mdi-source-branch {
    /* HACK: mdi is not fully imported, only required icons... */
    background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M13,14C9.64,14 8.54,15.35 8.18,16.24C9.25,16.7 10,17.76 10,19A3,3 0 0,1 7,22A3,3 0 0,1 4,19C4,17.69 4.83,16.58 6,16.17V7.83C4.83,7.42 4,6.31 4,5A3,3 0 0,1 7,2A3,3 0 0,1 10,5C10,6.31 9.17,7.42 8,7.83V13.12C8.88,12.47 10.16,12 12,12C14.67,12 15.56,10.66 15.85,9.77C14.77,9.32 14,8.25 14,7A3,3 0 0,1 17,4A3,3 0 0,1 20,7C20,8.34 19.12,9.5 17.91,9.86C17.65,11.29 16.68,14 13,14M7,18A1,1 0 0,0 6,19A1,1 0 0,0 7,20A1,1 0 0,0 8,19A1,1 0 0,0 7,18M7,4A1,1 0 0,0 6,5A1,1 0 0,0 7,6A1,1 0 0,0 8,5A1,1 0 0,0 7,4M17,6A1,1 0 0,0 16,7A1,1 0 0,0 17,8A1,1 0 0,0 18,7A1,1 0 0,0 17,6Z"/></svg>');
}

.mdi-checkbox-marked {
    /* HACK: mdi is not fully imported, only required icons... */
    background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M19,3A2,2 0 0,1 21,5V19A2,2 0 0,1 19,21H5A2,2 0 0,1 3,19V5A2,2 0 0,1 5,3H19M9.5,16.5L4.5,11.5L6.91,9.08L9.5,11.67L16.59,4.58L19,6.99L9.5,16.5Z"/></svg>');
}
</style>
