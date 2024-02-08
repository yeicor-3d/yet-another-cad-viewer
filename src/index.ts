// @ts-ignore
globalThis.__VUE_OPTIONS_API__ = process.env.NODE_ENV === "development"
// @ts-ignore
globalThis.__VUE_PROD_DEVTOOLS__ = process.env.NODE_ENV === "development"
// @ts-ignore
globalThis.__VUE_PROD_HYDRATION_MISMATCH_DETAILS__ = process.env.NODE_ENV === "development"

// import {createApp} from 'vue/dist/vue.esm-browser.prod.js'
// import {createApp} from 'vue/dist/vue.esm-browser.js'
import {createApp} from 'vue'
// @ts-ignore
import App from './App.vue'

const app = createApp(App)
app.config.compilerOptions.isCustomElement = tag => tag === 'model-viewer'
app.mount('body')