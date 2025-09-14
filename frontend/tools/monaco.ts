import {loader} from "@guolao/vue-monaco-editor"

import * as monaco from "monaco-editor"
//@ts-ignore
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker"
//@ts-ignore
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker"
//@ts-ignore
import cssWorker from "monaco-editor/esm/vs/language/css/css.worker?worker"
//@ts-ignore
import htmlWorker from "monaco-editor/esm/vs/language/html/html.worker?worker"
//@ts-ignore
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker"

(self as any).MonacoEnvironment = {
    getWorker(_: any, label: string) {
        if (label === "json") {
            return new jsonWorker()
        }
        if (label === "css" || label === "scss" || label === "less") {
            return new cssWorker()
        }
        if (label === "html" || label === "handlebars" || label === "razor") {
            return new htmlWorker()
        }
        if (label === "typescript" || label === "javascript") {
            return new tsWorker()
        }
        return new editorWorker()
    }
}

export function setupMonaco() {
    loader.config({monaco})
}
