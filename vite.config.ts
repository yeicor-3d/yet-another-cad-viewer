import {fileURLToPath, URL} from 'node:url'

import {defineConfig} from 'vite'
// @ts-ignore
import vue from '@vitejs/plugin-vue'
// @ts-ignore
import vueJsx from '@vitejs/plugin-vue-jsx'
import {name, version} from './package.json'
import {execSync} from 'child_process'
import {viteStaticCopy} from "vite-plugin-static-copy";
import {dirname, join} from "path";
import {version as pyodideVersion} from "pyodide";

let wantsSmallBuild = process.env.YACV_SMALL_BUILD == "true";

// https://vitejs.dev/config/
export default defineConfig({
    base: "",
    plugins: [
        vue({
            template: {
                compilerOptions: {
                    isCustomElement: (tag: string) => tag == 'model-viewer'
                }
            }
        }),
        vueJsx(),
        viteStaticCopyPyodide(),
    ],
    optimizeDeps: {exclude: ["pyodide"]},
    resolve: {
        alias: {
            // @ts-ignore
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    build: {
        assetsDir: '.', // Support deploying to a subdirectory using relative URLs
        cssCodeSplit: false, // Small enough to inline
        chunkSizeWarningLimit: 1024, // KB. Three.js is big. Draco is even bigger but not likely to be used.
        sourcemap: true, // For debugging production
        rollupOptions: {
            output: {
                experimentalMinChunkSize: 512000, // 512KB (avoid too many small chunks)
            },
            external: wantsSmallBuild ? [
                // Exclude some large optional dependencies if small build is requested (for embedding in python package)
                "pyodide",
                /.*\/pyodide-worker.*/,
                "monaco-editor",
                /monaco-editor\/.*/,
                "@guolao/vue-monaco-editor",
                /three\/examples\/jsm\/libs\/draco\/draco_(en|de)coder\.js/,
            ] : [],
        },
    },
    worker: {
        format: 'es', // Use ES modules for workers (IIFE is not supported with code-splitting)
    },
    define: {
        __APP_NAME__: JSON.stringify(name),
        __APP_VERSION__: JSON.stringify(version),
        __APP_GIT_SHA__: JSON.stringify(execSync('git rev-parse HEAD').toString().trim()),
        __APP_GIT_DIRTY__: JSON.stringify(execSync('git diff --quiet || echo dirty').toString().trim()),
        __YACV_SMALL_BUILD__: JSON.stringify(wantsSmallBuild)
    }
})


function viteStaticCopyPyodide() {
    const PYODIDE_EXCLUDE = [
        "!**/*.{md,html}",
        "!**/*.d.ts",
        "!**/*.whl",
        "!**/node_modules",
    ];
    // @ts-ignore
    const pyodideDir = dirname(fileURLToPath(import.meta.resolve("pyodide")));
    return viteStaticCopy({
        targets: wantsSmallBuild ? [] : [
            {
                src: [join(pyodideDir, "*")].concat(PYODIDE_EXCLUDE),
                dest: "pyodide-v" + pyodideVersion, // It would be better to use hashed names instead of folder...
            },
        ],
    });
}
