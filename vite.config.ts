import {fileURLToPath, URL} from 'node:url'

import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import {name, version} from './package.json'
import {execSync} from 'child_process'
import { viteStaticCopy } from "vite-plugin-static-copy";
import { dirname, join } from "path";

// https://vitejs.dev/config/
export default defineConfig({
    base: "",
    plugins: [
        vue({
            template: {
                compilerOptions: {
                    isCustomElement: tag => tag == 'model-viewer'
                }
            }
        }),
        vueJsx(),
        viteStaticCopyPyodide(),
    ],
    optimizeDeps: { exclude: ["pyodide"] },
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
            }
        }
    },
    define: {
        __APP_NAME__: JSON.stringify(name),
        __APP_VERSION__: JSON.stringify(version),
        __APP_GIT_SHA__: JSON.stringify(execSync('git rev-parse HEAD').toString().trim()),
        __APP_GIT_DIRTY__: JSON.stringify(execSync('git diff --quiet || echo dirty').toString().trim()),
    }
})


function viteStaticCopyPyodide() {
    const PYODIDE_EXCLUDE = [
        "!**/*.{md,html}",
        "!**/*.d.ts",
        "!**/*.whl",
        "!**/node_modules",
    ];
    const pyodideDir = dirname(fileURLToPath(import.meta.resolve("pyodide")));
    return viteStaticCopy({
        targets: [
            {
                src: [join(pyodideDir, "*")].concat(PYODIDE_EXCLUDE),
                dest: "assets",
            },
        ],
    });
}
