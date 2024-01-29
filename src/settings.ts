// @ts-ignore
import skyboxUrl from './../img/st_peters_square_night_8k.jpg';

export const settings = {
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