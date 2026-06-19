import { createApp } from "vue";
import App from "./App.vue";

import { createVuetify } from "vuetify";
import * as directives from "vuetify/lib/directives/index.mjs";
// @ts-ignore
import "vuetify/dist/vuetify.css";

// @ts-ignore
if (__APP_NAME__) {
  // @ts-ignore
  console.log(`Starting ${__APP_NAME__} v${__APP_VERSION__} (${__APP_GIT_SHA__}${__APP_GIT_DIRTY__ ? "+dirty" : ""})...`);
}

const vuetify = createVuetify({
  directives,
  theme: {
    defaultTheme: window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
    themes: {
      light: {
        colors: {
          // Vuetify 4 defaults invert surface-variant between light and dark (light gets dark variant).
          // Fix: light theme surface-variant should be a light tone with dark on- color.
          "surface-variant": "#F0F0F0",
          "on-surface-variant": "#1E1E1E",
        },
      },
      dark: {
        colors: {
          // Vuetify 4 defaults: dark theme surface-variant is too light.
          // Fix: dark theme surface-variant should be a dark tone with light on- color.
          "surface-variant": "#333333",
          "on-surface-variant": "#E0E0E0",
        },
      },
    },
  },
});

const app = createApp(App);
app.use(vuetify);
app.mount("body");
