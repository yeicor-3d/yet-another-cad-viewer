import {Document, TypedArray} from '@gltf-transform/core'
import {Matrix4, Vector3} from 'three'


/** Exports the colors used for the axes, primary and secondary. They match the orientation gizmo. */
export const AxesColors = {
    x: [[247, 60, 60], [148, 36, 36]],
    z: [[108, 203, 38], [65, 122, 23]],
    y: [[23, 140, 240], [14, 84, 144]]
}

/**
 * Create a new Axes helper as a GLTF model, useful for debugging positions and orientations.
 */
export function newAxes(doc: Document, size: Vector3, transform: Matrix4) {
    const buffer = doc.createBuffer()
    const positions = doc.createAccessor('axesPosition')
        .setArray(new Float32Array([
            0, 0, 0,
            size.x, 0, 0,
            0, 0, 0,
            0, size.y, 0,
            0, 0, 0,
            0, 0, -size.z,
        ]) as TypedArray)
        .setType('VEC3')
        .setBuffer(buffer)
    const indices = doc.createAccessor('axesIndices')
        .setArray(new Uint32Array([0, 1, 2, 3, 4, 5]) as TypedArray)
        .setType('SCALAR')
        .setBuffer(buffer)
    const colors = doc.createAccessor('axesColor')
        .setArray(new Float32Array([
            ...(AxesColors.x[0]), ...(AxesColors.x[1]),
            ...(AxesColors.y[0]), ...(AxesColors.y[1]),
            ...(AxesColors.z[0]), ...(AxesColors.z[1]),
        ].map(x => x / 255.0)) as TypedArray)
        .setType('VEC3')
        .setBuffer(buffer)
    const material = doc.createMaterial('axesMaterial')
        .setAlphaMode('OPAQUE')
    const geometry = doc.createPrimitive()
        .setIndices(indices)
        .setAttribute('POSITION', positions)
        .setAttribute('COLOR_0', colors)
        .setMode(WebGL2RenderingContext.LINES)
        .setMaterial(material)
    const mesh = doc.createMesh('axes').addPrimitive(geometry)
    const node = doc.createNode('axes').setMesh(mesh).setMatrix(transform.elements as any)
    doc.createScene('axesScene').addChild(node)
}

/**
 * Create a new Grid helper as a GLTF model, useful for debugging sizes with an OrthographicCamera.
 *
 * The grid is built as a box of triangles (representing lines) looking to the inside of the box.
 * This ensures that only the back of the grid is always visible, regardless of the camera position.
 */
export function newGrid(doc: Document, size: Vector3, transform: Matrix4 = new Matrix4(), divisions = 10) {
    const buffer = doc.createBuffer();
    // TODO: implement grid
}
