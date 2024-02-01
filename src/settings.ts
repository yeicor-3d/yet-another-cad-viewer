// @ts-ignore
import skyboxUrl from '../assets/st_peters_square_night_8k.jpg';
// @ts-ignore
import logo from "url:../assets/fox.glb";

export const settings = {
    // ModelViewer settings
    preloadModel: logo,
    autoplay: true,
    arModes: 'webxr scene-viewer quick-look',
    shadowIntensity: 1,
    background: skyboxUrl,
}

// Auto-override any settings from the URL
const url = new URL(window.location.href);
url.searchParams.forEach((value, key) => {
    if (key in settings) {
        switch (typeof settings[key]) {
            case 'boolean':
                settings[key] = value === 'true';
                break;
            case 'number':
                settings[key] = Number(value);
                break;
            default:
                settings[key] = value;
        }
    }
})