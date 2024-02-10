globalThis.__VUE_OPTIONS_API__ = process.env.NODE_ENV === "development"
globalThis.__VUE_PROD_DEVTOOLS__ = process.env.NODE_ENV === "development"
globalThis.__VUE_PROD_HYDRATION_MISMATCH_DETAILS__ = process.env.NODE_ENV === "development"

// import {createApp} from 'vue/dist/vue.esm-browser.prod.js'
// import {createApp} from 'vue/dist/vue.esm-browser.js'
import {createApp} from 'vue'
import App from './App.vue'


import 'vuetify/lib/styles/main.sass';
import { createVuetify } from 'vuetify';
import '@mdi/font/css/materialdesignicons.css'

// TODO: Only import the components and directives that are actually used
// @ts-ignore
import * as components from 'vuetify/lib/components';
// @ts-ignore
import * as directives from 'vuetify/lib/directives';

const vuetify = createVuetify({
    components,
    directives,
    theme: {
        defaultTheme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    }
});

const app = createApp(App)
app.use(vuetify)
app.mount('body')