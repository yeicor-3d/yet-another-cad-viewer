// These are the default values for the settings, which are overridden below
export const settings = {
    preload: [
        // @ts-ignore
        // new URL('../../assets/fox.glb', import.meta.url).href,
        // @ts-ignore
        // new URL('../../assets/logo_build/base.glb', import.meta.url).href,
        // @ts-ignore
        // new URL('../../assets/logo_build/location.glb', import.meta.url).href,
        // @ts-ignore
        // new URL('../../assets/logo_build/img.jpg.glb', import.meta.url).href,
        // Websocket URLs automatically listen for new models from the python backend
        "dev+http://127.0.0.1:32323/"
    ],
    loadHelpers: true,
    edgeWidth: 0, /* The default line size for edges, set to 0 to use basic gl.LINEs */
    displayLoadingEveryMs: 1000, /* How often to display partially loaded models */
    monitorEveryMs: 100,
    monitorOpenTimeoutMs: 1000,
    // ModelViewer settings
    autoplay: true, // Global animation toggle
    arModes: 'webxr scene-viewer quick-look',
    zoomSensitivity: 0.25,
    orbitSensitivity: 1,
    panSensitivity: 1,
    exposure: 1,
    shadowIntensity: 0,
    background: '',
}

const firstTimeNames: Array<string> = []; // Needed for array values, which clear the array when overridden
function parseSetting(name: string, value: string): any {
    let arrayElem = name.endsWith(".0")
    if (arrayElem) name = name.slice(0, -2);
    let prevValue = (settings as any)[name];
    if (prevValue === undefined) throw new Error(`Unknown setting: ${name}`);
    if (Array.isArray(prevValue)) {
        if (!arrayElem) {
            let toExtend = []
            if (!firstTimeNames.includes(name)) {
                firstTimeNames.push(name);
            } else {
                toExtend = prevValue;
            }
            toExtend.push(parseSetting(name + ".0", value));
            return toExtend;
        } else {
            prevValue = prevValue[0];
        }
    }
    switch (typeof prevValue) {
        case 'boolean':
            return value === 'true';
        case 'number':
            return Number(value);
        case 'string':
            return value;
        default:
            throw new Error(`Unknown setting type: ${typeof prevValue} -- ${prevValue}`);
    }
}

// Auto-override any settings from the URL
const url = new URL(window.location.href);
url.searchParams.forEach((value, key) => {
    if (key in settings) (settings as any)[key] = parseSetting(key, value);
})