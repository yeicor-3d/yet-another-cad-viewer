globalThis.__VUE_OPTIONS_API__ = process.env.NODE_ENV === "development"
globalThis.__VUE_PROD_DEVTOOLS__ = process.env.NODE_ENV === "development"
globalThis.__VUE_PROD_HYDRATION_MISMATCH_DETAILS__ = process.env.NODE_ENV === "development"

// import {createApp} from 'vue/dist/vue.esm-browser.prod.js'
// import {createApp} from 'vue/dist/vue.esm-browser.js'
import {createApp} from 'vue'
import App from './App.vue'

import {createVuetify} from 'vuetify';
import * as directives from 'vuetify/lib/directives';

const vuetify = createVuetify({
    directives,
    theme: {
        defaultTheme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    }
});

const app = createApp(App)
app.use(vuetify)
app.mount('body')

// Start non-blocking loading of Vuetify and icon styles
import('vuetify/lib/styles/main.sass');
import('@mdi/font/css/materialdesignicons.css');