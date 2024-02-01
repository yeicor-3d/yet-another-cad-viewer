import {App} from "./app";
import {settings} from "./settings";
const app = new App()

app.install();

app.replaceModel(settings.preloadModel)
