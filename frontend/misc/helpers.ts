// noinspection JSVoidFunctionReturnValueUsed,JSUnresolvedReference

import { Document, type TypedArray } from "@gltf-transform/core";
import { Vector2 } from "three/src/math/Vector2.js";
import { Vector3 } from "three/src/math/Vector3.js";
import { Matrix4 } from "three/src/math/Matrix4.js";

/** Exports the colors used for the axes, primary and secondary. They match the orientation gizmo. */
export const AxesColors = {
  x: [
    [247, 60, 60],
    [148, 36, 36],
  ],
  z: [
    [108, 203, 38],
    [65, 122, 23],
  ],
  y: [
    [23, 140, 240],
    [14, 84, 144],
  ],
};

function buildSimpleGltf(
  doc: Document,
  rawPositions: number[],
  rawIndices: number[],
  rawColors: number[] | null,
  transform: Matrix4,
  name: string = "__helper",
  mode: number = WebGL2RenderingContext.LINES,
) {
  const buffer = doc.getRoot().listBuffers()[0] ?? doc.createBuffer(name + "Buffer");
  const scene = doc.getRoot().getDefaultScene() ?? doc.getRoot().listScenes()[0] ?? doc.createScene(name + "Scene");
  if (!scene) throw new Error("Scene is undefined");
  if (!rawPositions) throw new Error("rawPositions is undefined");
  const positions = doc
    .createAccessor(name + "Position")
    .setArray(new Float32Array(rawPositions) as TypedArray)
    .setType("VEC3")
    .setBuffer(buffer);
  const indices = doc
    .createAccessor(name + "Indices")
    .setArray(new Uint32Array(rawIndices) as TypedArray)
    .setType("SCALAR")
    .setBuffer(buffer);
  let colors = null;
  if (rawColors) {
    colors = doc
      .createAccessor(name + "Color")
      .setArray(new Float32Array(rawColors) as TypedArray)
      .setType("VEC4")
      .setBuffer(buffer);
  }
  const material = doc.createMaterial(name + "Material").setAlphaMode("OPAQUE");
  const geometry = doc
    .createPrimitive()
    .setIndices(indices)
    .setAttribute("POSITION", positions)
    .setMode(mode as any)
    .setMaterial(material);
  if (rawColors) {
    geometry.setAttribute("COLOR_0", colors);
  }
  if (mode == WebGL2RenderingContext.TRIANGLES) {
    geometry.setExtras({
      face_triangles_end: [
        rawIndices.length / 6,
        (rawIndices.length * 2) / 6,
        (rawIndices.length * 3) / 6,
        (rawIndices.length * 4) / 6,
        (rawIndices.length * 5) / 6,
        rawIndices.length,
      ],
    });
  } else if (mode == WebGL2RenderingContext.LINES) {
    geometry.setExtras({ edge_points_end: [rawIndices.length / 3, (rawIndices.length * 2) / 3, rawIndices.length] });
  }
  const mesh = doc.createMesh(name + "Mesh").addPrimitive(geometry);
  const node = doc
    .createNode(name + "Node")
    .setMesh(mesh)
    .setMatrix(transform.elements as any);
  scene.addChild(node);
}

/**
 * Create a new Axes helper as a GLTF model, useful for debugging positions and orientations.
 */
export function newAxes(doc: Document, size: Vector3, transform: Matrix4) {
  let rawIndices = [0, 1, 2, 3, 4, 5];
  let rawPositions = [0, 0, 0, size.x, 0, 0, 0, 0, 0, 0, size.y, 0, 0, 0, 0, 0, 0, -size.z];
  let rawColors = [
    ...(AxesColors.x[0] ?? [255, 0, 0]),
    255,
    ...(AxesColors.x[1] ?? [255, 0, 0]),
    255,
    ...(AxesColors.y[0] ?? [0, 255, 0]),
    255,
    ...(AxesColors.y[1] ?? [0, 255, 0]),
    255,
    ...(AxesColors.z[0] ?? [0, 0, 255]),
    255,
    ...(AxesColors.z[1] ?? [0, 0, 255]),
    255,
  ].map((x) => x / 255.0);
  // Axes at (0, 0, 0)
  buildSimpleGltf(doc, rawPositions, rawIndices, rawColors, new Matrix4(), "__helper_axes");
  buildSimpleGltf(doc, [0, 0, 0], [0], [1, 1, 1, 1], new Matrix4(), "__helper_axes", WebGL2RenderingContext.POINTS);
  // Axes at center
  if (new Matrix4() != transform) {
    buildSimpleGltf(doc, rawPositions, rawIndices, rawColors, transform, "__helper_axes_center");
    buildSimpleGltf(
      doc,
      [0, 0, 0],
      [0],
      [1, 1, 1, 1],
      transform,
      "__helper_axes_center",
      WebGL2RenderingContext.POINTS,
    );
  }
}

/**
 * Create a new Grid helper as a GLTF model, useful for debugging sizes with an OrthographicCamera.
 *
 * The grid is built as a box of triangles (representing lines) looking to the inside of the box.
 * This ensures that only the back of the grid is always visible, regardless of the camera position.
 */
export function newGridBox(doc: Document, size: Vector3, baseTransform: Matrix4, divisions = 10) {
  // Create transformed positions for the inner faces of the box
  let allPositions: number[] = [];
  let allIndices: number[] = [];
  for (let axis of [new Vector3(1, 0, 0), new Vector3(0, 1, 0), new Vector3(0, 0, -1)]) {
    for (let positive of [1, -1]) {
      let offset = axis.clone().multiply(size.clone().multiplyScalar(0.5 * positive));
      let translation = new Matrix4().makeTranslation(offset.x, offset.y, offset.z);
      let rotation = new Matrix4().lookAt(new Vector3(), offset, new Vector3(0, 1, 0));
      let size2 = new Vector2();
      if (axis.x) size2.set(size.z, size.y);
      if (axis.y) size2.set(size.x, size.z);
      if (axis.z) size2.set(size.x, size.y);
      let transform = new Matrix4().multiply(translation).multiply(rotation);
      let [rawPositions, rawIndices] = newGridPlane(size2, divisions);
      let baseIndex = allPositions.length / 3;
      for (let i of rawIndices) {
        allIndices.push(i + baseIndex);
      }
      // Apply transform to the positions before adding them to the list
      for (let i = 0; i < rawPositions.length; i += 3) {
        let pos = new Vector3(rawPositions[i], rawPositions[i + 1], rawPositions[i + 2]);
        pos.applyMatrix4(transform);
        allPositions.push(pos.x, pos.y, pos.z);
      }
    }
  }
  let colors = new Array((allPositions.length / 3) * 4).fill(1);
  buildSimpleGltf(
    doc,
    allPositions,
    allIndices,
    colors,
    baseTransform,
    "__helper_grid",
    WebGL2RenderingContext.TRIANGLES,
  );
}

export function newGridPlane(size: Vector2, divisions = 10, divisionWidth = 0.002): [number[], number[]] {
  const rawPositions = [];
  const rawIndices = [];
  // Build the grid as triangles
  for (let i = 0; i <= divisions; i++) {
    const x = -size.x / 2 + (size.x * i) / divisions;
    const y = -size.y / 2 + (size.y * i) / divisions;

    // Vertical quad (two triangles)
    rawPositions.push(x - (divisionWidth * size.x) / 2, -size.y / 2, 0);
    rawPositions.push(x + (divisionWidth * size.x) / 2, -size.y / 2, 0);
    rawPositions.push(x + (divisionWidth * size.x) / 2, size.y / 2, 0);
    rawPositions.push(x - (divisionWidth * size.x) / 2, size.y / 2, 0);
    const baseIndex = i * 4;
    rawIndices.push(baseIndex, baseIndex + 1, baseIndex + 2);
    rawIndices.push(baseIndex, baseIndex + 2, baseIndex + 3);

    // Horizontal quad (two triangles)
    rawPositions.push(-size.x / 2, y - (divisionWidth * size.y) / 2, 0);
    rawPositions.push(size.x / 2, y - (divisionWidth * size.y) / 2, 0);
    rawPositions.push(size.x / 2, y + (divisionWidth * size.y) / 2, 0);
    rawPositions.push(-size.x / 2, y + (divisionWidth * size.y) / 2, 0);
    const baseIndex2 = (divisions + 1 + i) * 4;
    rawIndices.push(baseIndex2, baseIndex2 + 1, baseIndex2 + 2);
    rawIndices.push(baseIndex2, baseIndex2 + 2, baseIndex2 + 3);
  }
  return [rawPositions, rawIndices];
}
