import {Document, TypedArray} from '@gltf-transform/core'
import {Matrix4, Vector2, Vector3} from 'three'


/** Exports the colors used for the axes, primary and secondary. They match the orientation gizmo. */
export const AxesColors = {
    x: [[247, 60, 60], [148, 36, 36]],
    z: [[108, 203, 38], [65, 122, 23]],
    y: [[23, 140, 240], [14, 84, 144]]
}

function buildSimpleGltf(doc: Document, rawPositions: number[], rawIndices: number[], rawColors: number[] | null, transform: Matrix4, name: string = '__helper', mode: number = WebGL2RenderingContext.LINES) {
    const buffer = doc.getRoot().listBuffers()[0] ?? doc.createBuffer(name + 'Buffer')
    const scene = doc.getRoot().getDefaultScene() ?? doc.getRoot().listScenes()[0] ?? doc.createScene(name + 'Scene')
    const positions = doc.createAccessor(name + 'Position')
        .setArray(new Float32Array(rawPositions) as TypedArray)
        .setType('VEC3')
        .setBuffer(buffer)
    const indices = doc.createAccessor(name + 'Indices')
        .setArray(new Uint32Array(rawIndices) as TypedArray)
        .setType('SCALAR')
        .setBuffer(buffer)
    const colors = doc.createAccessor(name + 'Color')
        .setArray(new Float32Array(rawColors) as TypedArray)
        .setType('VEC3')
        .setBuffer(buffer)
    const material = doc.createMaterial(name + 'Material')
        .setAlphaMode('OPAQUE')
    const geometry = doc.createPrimitive()
        .setIndices(indices)
        .setAttribute('POSITION', positions)
        .setMode(mode as any)
        .setMaterial(material)
    if (rawColors) {
        geometry.setAttribute('COLOR_0', colors)
    }
    const mesh = doc.createMesh(name + 'Mesh').addPrimitive(geometry)
    const node = doc.createNode(name + 'Node').setMesh(mesh).setMatrix(transform.elements as any)
    scene.addChild(node)
}

/**
 * Create a new Axes helper as a GLTF model, useful for debugging positions and orientations.
 */
export function newAxes(doc: Document, size: Vector3, transform: Matrix4) {
    let rawPositions = [
        0, 0, 0,
        size.x, 0, 0,
        0, 0, 0,
        0, size.y, 0,
        0, 0, 0,
        0, 0, -size.z,
    ];
    let rawIndices = [0, 1, 2, 3, 4, 5];
    let rawColors = [
        ...(AxesColors.x[0]), ...(AxesColors.x[1]),
        ...(AxesColors.y[0]), ...(AxesColors.y[1]),
        ...(AxesColors.z[0]), ...(AxesColors.z[1]),
    ].map(x => x / 255.0);
    buildSimpleGltf(doc, rawPositions, rawIndices, rawColors, transform, '__helper_axes');
}

/**
 * Create a new Grid helper as a GLTF model, useful for debugging sizes with an OrthographicCamera.
 *
 * The grid is built as a box of triangles (representing lines) looking to the inside of the box.
 * This ensures that only the back of the grid is always visible, regardless of the camera position.
 */
export function newGridBox(doc: Document, size: Vector3, baseTransform: Matrix4 = new Matrix4(), divisions = 10) {
    // Create transformed positions for the inner faces of the box
    for (let axis of [new Vector3(1, 0, 0), new Vector3(0, 1, 0), new Vector3(0, 0, -1)]) {
        for (let positive of [1, -1]) {
            let offset = axis.clone().multiply(size.clone().multiplyScalar(0.5 * positive));
            let translation = new Matrix4().makeTranslation(offset.x, offset.y, offset.z)
            let rotation = new Matrix4().lookAt(new Vector3(), offset, new Vector3(0, 1, 0))
            let size2 = new Vector2();
            if (axis.x) size2.set(size.z, size.y);
            if (axis.y) size2.set(size.x, size.z);
            if (axis.z) size2.set(size.x, size.y);
            let transform = baseTransform.clone().multiply(translation).multiply(rotation);
            newGridPlane(doc, size2, transform, divisions);
        }
    }
}

export function newGridPlane(doc: Document, size: Vector2, transform: Matrix4 = new Matrix4(), divisions = 10, divisionWidth = 0.2) {
    const rawPositions = [];
    const rawIndices = [];
    // Build the grid as triangles
    for (let i = 0; i <= divisions; i++) {
        const x = -size.x / 2 + size.x * i / divisions;
        const y = -size.y / 2 + size.y * i / divisions;

        // Vertical quad (two triangles)
        rawPositions.push(x - divisionWidth / 2, -size.y / 2, 0);
        rawPositions.push(x + divisionWidth / 2, -size.y / 2, 0);
        rawPositions.push(x + divisionWidth / 2, size.y / 2, 0);
        rawPositions.push(x - divisionWidth / 2, size.y / 2, 0);
        const baseIndex = i * 4;
        rawIndices.push(baseIndex, baseIndex + 1, baseIndex + 2);
        rawIndices.push(baseIndex, baseIndex + 2, baseIndex + 3);

        // Horizontal quad (two triangles)
        rawPositions.push(-size.x / 2, y - divisionWidth / 2, 0);
        rawPositions.push(size.x / 2, y - divisionWidth / 2, 0);
        rawPositions.push(size.x / 2, y + divisionWidth / 2, 0);
        rawPositions.push(-size.x / 2, y + divisionWidth / 2, 0);
        const baseIndex2 = (divisions+1 + i) * 4;
        rawIndices.push(baseIndex2, baseIndex2 + 1, baseIndex2 + 2);
        rawIndices.push(baseIndex2, baseIndex2 + 2, baseIndex2 + 3);
    }
    buildSimpleGltf(doc, rawPositions, rawIndices, null, transform, '__helper_grid', WebGL2RenderingContext.TRIANGLES);
}
