// Model management from the graphics side

import type { MObject3D } from "./Selection.vue";
import type { Intersection } from "three";
import { Box3 } from "three";
import { extrasNameKey } from "../misc/gltf";

/** Information about a single item in the selection */
export class SelectionInfo {
  /** The object which was (partially) selected */
  object: MObject3D;
  /** The type of the selection */
  kind: "face" | "edge" | "vertex";
  /** Start and end indices of the primitives in the geometry */
  indices: [number, number];

  constructor(object: MObject3D, kind: "face" | "edge" | "vertex", indices: [number, number]) {
    this.object = object;
    this.kind = kind;
    this.indices = indices;
  }

  public getObjectName() {
    return this.object.userData[extrasNameKey];
  }

  public matches(object: MObject3D) {
    return (
      this.getObjectName() === object.userData[extrasNameKey] &&
      ((this.kind === "face" && (object.type === "Mesh" || object.type === "SkinnedMesh")) ||
        (this.kind === "edge" && (object.type === "Line" || object.type === "LineSegments")) ||
        (this.kind === "vertex" && object.type === "Points"))
    );
  }

  public getKey() {
    return this.object.uuid + this.kind + this.indices[0].toFixed() + this.indices[1].toFixed();
  }

  public getBox(): Box3 {
    let index = this.object.geometry.index || { getX: (i: number) => i };
    let pos = this.object.geometry.getAttribute("position");
    let min = [Infinity, Infinity, Infinity];
    let max = [-Infinity, -Infinity, -Infinity];
    for (let i = this.indices[0]; i < this.indices[1]; i++) {
      let vertIndex = index!.getX(i);
      let x = pos.getX(vertIndex);
      let y = pos.getY(vertIndex);
      let z = pos.getZ(vertIndex);
      min[0] = Math.min(min[0] ?? Infinity, x);
      min[1] = Math.min(min[1] ?? Infinity, y);
      min[2] = Math.min(min[2] ?? Infinity, z);
      max[0] = Math.max(max[0] ?? -Infinity, x);
      max[1] = Math.max(max[1] ?? -Infinity, y);
      max[2] = Math.max(max[2] ?? -Infinity, z);
    }
    return new Box3().setFromArray([...min, ...max]);
  }
}

export function hitToSelectionInfo(hit: Intersection<MObject3D>): SelectionInfo | null {
  let kind = hit.object.type;
  if (kind == "Mesh" || kind == "SkinnedMesh") {
    let indices = hitFaceTriangleIndices(hit);
    if (indices === null) return null;
    return new SelectionInfo(hit.object, "face", indices);
  } else if (kind == "Line" || kind == "LineSegments") {
    // Select raw lines, not the wide meshes representing them
    // This is because the indices refer to the raw lines, not the wide meshes
    // Furthermore, this allows better "fuzzy" raycasting logic
    let indices = hitEdgePointIndices(hit);
    if (indices === null) return null;
    return new SelectionInfo(hit.object, "edge", indices);
  } else if (kind == "Points") {
    if (hit.index === undefined) return null;
    return new SelectionInfo(hit.object, "vertex", [hit.index, hit.index + 1]);
  }
  return null;
}

function hitFaceTriangleIndices(hit: Intersection<MObject3D>): [number, number] | null {
  let faceTrianglesEnd = hit?.object?.geometry?.userData?.face_triangles_end;
  if (!hit.faceIndex) return null;
  if (!faceTrianglesEnd) {
    // Fallback to selecting the whole imported mesh
    //console.log("No face_triangles_end found, selecting the whole mesh");
    return [0, (hit.object.geometry.index ?? hit.object.geometry.attributes.position)?.count ?? 0];
  } else {
    // Normal CAD model
    let rawIndex = hit.faceIndex * 3; // Faces are triangles with 3 indices
    for (let i = 0; i < faceTrianglesEnd.length; i++) {
      let faceSwapIndex = faceTrianglesEnd[i];
      if (rawIndex < faceSwapIndex) {
        let start = i === 0 ? 0 : faceTrianglesEnd[i - 1];
        return [start, faceTrianglesEnd[i]];
      }
    }
  }
  return null;
}

function hitEdgePointIndices(hit: Intersection<MObject3D>): [number, number] | null {
  let edgePointsEnd = hit?.object?.geometry?.userData?.edge_points_end;
  if (!edgePointsEnd || hit.index === undefined) return null;
  let rawIndex = hit.index; // Faces are triangles with 3 indices
  for (let i = 0; i < edgePointsEnd.length; i++) {
    let edgeSwapIndex = edgePointsEnd[i];
    if (rawIndex < edgeSwapIndex) {
      let start = i === 0 ? 0 : edgePointsEnd[i - 1];
      return [start, edgePointsEnd[i]];
    }
  }
  return null;
}

function applyColor(
  selInfo: SelectionInfo,
  colorAttribute: any,
  color: [number, number, number, number],
): [number, number, number, number] {
  let index = selInfo.object.geometry.index;
  let prevColor: [number, number, number, number] | null = null;
  if (colorAttribute !== undefined) {
    for (let i = selInfo.indices[0]; i < selInfo.indices[1]; i++) {
      let vertIndex = index!.getX(i);
      if (prevColor === null)
        prevColor = [
          colorAttribute.getX(vertIndex),
          colorAttribute.getY(vertIndex),
          colorAttribute.getZ(vertIndex),
          colorAttribute.getW(vertIndex),
        ];
      colorAttribute.setXYZW(vertIndex, color[0], color[1], color[2], color[3]);
    }
    colorAttribute.needsUpdate = true;
    if (selInfo.object.userData.niceLine !== undefined) {
      // Need to update the color of the nice line as well
      let indexAttribute = selInfo.object.geometry.index!!;
      let allNewColors = [];
      for (let i = 0; i < indexAttribute.count; i++) {
        if (indexAttribute.getX(i) >= selInfo.indices[0] && indexAttribute.getX(i) < selInfo.indices[1]) {
          allNewColors.push(color[0], color[1], color[2]);
        } else {
          allNewColors.push(
            colorAttribute.getX(indexAttribute.getX(i)),
            colorAttribute.getY(indexAttribute.getX(i)),
            colorAttribute.getZ(indexAttribute.getX(i)),
          );
        }
      }
      selInfo.object.userData.niceLine.geometry.setColors(allNewColors);
      for (let attribute of Object.values(selInfo.object.userData.niceLine.geometry.attributes)) {
        (attribute as any).needsUpdate = true;
      }
    }
  } else {
    // Fallback to tinting the whole mesh for imported models
    //console.log("No color attribute found, tinting the whole mesh")
    let tmpPrevColor = selInfo.object.material.color;
    prevColor = [tmpPrevColor.r, tmpPrevColor.g, tmpPrevColor.b, 1];
    selInfo.object.material.color.setRGB(color[0], color[1], color[2]);
    selInfo.object.material.needsUpdate = true;
  }
  return prevColor!;
}

export function highlight(selInfo: SelectionInfo): void {
  // Update the color of all the triangles in the face
  let geometry = selInfo.object.geometry;
  let colorAttr = selInfo.object.geometry.getAttribute("color");
  geometry.userData.savedColor = geometry.userData.savedColor || {};
  geometry.userData.savedColor[selInfo.getKey()] = applyColor(selInfo, colorAttr, [1.0, 0.0, 0.0, 1.0]);
}

export function highlightUndo(selInfo: SelectionInfo): void {
  // Update the color of all the triangles in the face
  let geometry = selInfo.object.geometry;
  let colorAttr = selInfo.object.geometry.getAttribute("color");
  let savedColor = geometry.userData.savedColor[selInfo.getKey()];
  applyColor(selInfo, colorAttr, savedColor);
  delete geometry.userData.savedColor[selInfo.getKey()];
}
