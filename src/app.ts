import {ModelViewerElement} from '@google/model-viewer';
import {$scene} from "@google/model-viewer/lib/model-viewer-base";
import {OrientationGizmo} from "./orientation";
import {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
import {settings} from "./settings";

export class App {
    element: ModelViewerElement

    install() {
        this.element = new ModelViewerElement();
        this.element.setAttribute('alt', 'The CAD Viewer is not supported on this browser.');
        this.element.setAttribute('camera-controls', '');
        this.element.setAttribute('camera-orbit', '30deg 75deg auto');
        this.element.setAttribute('max-camera-orbit', 'Infinity 180deg auto');
        this.element.setAttribute('min-camera-orbit', '-Infinity 0deg auto');
        this.element.setAttribute('interaction-prompt', 'none'); // Quits selected views from gizmo
        // this.element.setAttribute('auto-rotate', ''); // Messes with the gizmo (rotates model instead of camera)
        if (settings.autoplay) this.element.setAttribute('autoplay', '');
        if (settings.arModes) {
            this.element.setAttribute('ar', '');
            this.element.setAttribute('ar-modes', settings.arModes);
        }
        if (settings.shadowIntensity) {
            this.element.setAttribute('shadow-intensity', '1');
        }
        if (settings.background) {
            this.element.setAttribute('skybox-image', settings.background);
            this.element.setAttribute('environment-image', settings.background);
        }
        console.log('ModelViewerElement', this.element)
        document.body.appendChild(this.element);
        // Misc installation
        let scene: ModelScene = this.element[$scene];
        let gizmo = new OrientationGizmo(scene);
        gizmo.install();

        function updateGizmo() {
            gizmo.update();
            requestAnimationFrame(updateGizmo);
        }

        updateGizmo();
    }

    replaceModel(url: string) {
        this.element.setAttribute('src', url)
    }
}