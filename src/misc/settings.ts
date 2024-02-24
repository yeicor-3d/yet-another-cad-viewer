// These are the default values for the settings, which are overridden below
export const settings = {
    preloadModels: [
        // @ts-ignore
        new URL('../../assets/fox.glb', import.meta.url).href,
        // @ts-ignore
        new URL('../../assets/logo.glb', import.meta.url).href,
        // Websocket URLs automatically listen for new models from the python backend
        // "ws://localhost:32323/"
    ],
    displayLoadingEveryMs: 1000, /* How often to display partially loaded models */
    checkServerEveryMs: 100, /* How often to check for a new server */
    // ModelViewer settings
    autoplay: true,
    arModes: 'webxr scene-viewer quick-look',
    exposure: 1,
    shadowIntensity: 0,
    background: '',
}

const firstTimeNames = []; // Needed for array values, which clear the array when overridden
function parseSetting(name: string, value: string): any {
    let arrayElem = name.endsWith(".0")
    if (arrayElem) name = name.slice(0, -2);
    let prevValue = settings[name];
    if (prevValue === undefined) throw new Error(`Unknown setting: ${name}`);
    if (Array.isArray(prevValue) && !arrayElem) {
        let toExtend = []
        if (!firstTimeNames.includes(name)) {
            firstTimeNames.push(name);
        } else {
            toExtend = prevValue;
        }
        toExtend.push(parseSetting(name + ".0", value));
        return toExtend;
    }
    switch (typeof prevValue) {
        case 'boolean':
            return value === 'true';
        case 'number':
            return Number(value);
        case 'string':
            return value;
        default:
            throw new Error(`Unknown setting type: ${typeof prevValue}`);
    }
}

// Auto-override any settings from the URL
const url = new URL(window.location.href);
url.searchParams.forEach((value, key) => {
    if (key in settings) settings[key] = parseSetting(key, value);
})