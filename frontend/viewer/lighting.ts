import { ModelViewerElement } from "@google/model-viewer";
import { $scene } from "@google/model-viewer/lib/model-viewer-base";
import { settings } from "../misc/settings.ts";

export let currentSceneRotation = 0; // radians, 0 is the default rotation

export async function setupLighting(modelViewer: ModelViewerElement) {
  modelViewer[$scene].environmentIntensity = (await settings).environmentIntensity;
  // Code is mostly copied from the example at: https://modelviewer.dev/examples/stagingandcameras/#turnSkybox
  let lastX: number;
  let panning = false;
  let radiansPerPixel: number;

  const startPan = () => {
    const orbit = modelViewer.getCameraOrbit();
    const { radius } = orbit;
    radiansPerPixel = (-1 * radius) / modelViewer.getBoundingClientRect().height;
    modelViewer.interactionPrompt = "none";
  };

  const updatePan = (thisX: number) => {
    const delta = (thisX - lastX) * radiansPerPixel;
    lastX = thisX;
    currentSceneRotation += delta;
    const orbit = modelViewer.getCameraOrbit();
    orbit.theta += delta;
    modelViewer.cameraOrbit = orbit.toString();
    modelViewer.resetTurntableRotation(currentSceneRotation);
    modelViewer.jumpCameraToGoal();
  };

  modelViewer.addEventListener(
    "mousedown",
    (event) => {
      panning = event.metaKey || event.shiftKey;
      if (!panning) return;

      lastX = event.clientX;
      startPan();
      event.stopPropagation();
    },
    true,
  );

  modelViewer.addEventListener(
    "touchstart",
    (event) => {
      const { targetTouches, touches } = event;
      panning = targetTouches.length === 2 && targetTouches.length === touches.length;
      if (!panning) return;

      lastX = 0.5 * ((targetTouches[0]?.clientX ?? 0) + (targetTouches[1]?.clientX ?? 0));
      startPan();
    },
    true,
  );

  document.addEventListener(
    "mousemove",
    (event) => {
      if (!panning) return;

      updatePan(event.clientX);
      event.stopPropagation();
    },
    true,
  );

  modelViewer.addEventListener(
    "touchmove",
    (event) => {
      if (!panning || event.targetTouches.length !== 2) return;

      const { targetTouches } = event;
      const thisX = 0.5 * ((targetTouches[0]?.clientX ?? 0) + (targetTouches[1]?.clientX ?? 0));
      updatePan(thisX);
    },
    true,
  );

  document.addEventListener(
    "mouseup",
    (event) => {
      panning = false;
    },
    true,
  );

  modelViewer.addEventListener(
    "touchend",
    (event) => {
      panning = false;
    },
    true,
  );
}
