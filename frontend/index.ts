import {createApp} from 'vue'
import App from './App.vue'

import {createVuetify} from 'vuetify';
import * as directives from 'vuetify/lib/directives/index.mjs';
import 'vuetify/dist/vuetify.css';

const vuetify = createVuetify({
    directives,
    theme: {
        defaultTheme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    }
});

const app = createApp(App)
app.use(vuetify)
app.mount('body')
