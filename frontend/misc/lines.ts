import {BufferGeometry} from 'three/src/core/BufferGeometry.js';
import {Vector2} from 'three/src/math/Vector2.js';

// The following imports must be done dynamically to be able to import three.js separately (smaller bundle sizee)
// import {LineSegments2} from "three/examples/jsm/lines/LineSegments2.js";
// import {LineMaterial} from "three/examples/jsm/lines/LineMaterial.js";
// import {LineSegmentsGeometry} from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
const LineSegments2Import = import('three/examples/jsm/lines/LineSegments2.js');
const LineMaterialImport = import('three/examples/jsm/lines/LineMaterial.js');
const LineSegmentsGeometryImport = import('three/examples/jsm/lines/LineSegmentsGeometry.js');

export async function toLineSegments(bufferGeometry: BufferGeometry, lineWidth: number = 0.1) {
    const LineSegments2 = (await LineSegments2Import).LineSegments2;
    const LineMaterial = (await LineMaterialImport).LineMaterial;
    return new LineSegments2(await toLineSegmentsGeometry(bufferGeometry), new LineMaterial({
        color: 0xffffffff,
        vertexColors: true,
        linewidth: lineWidth, // mm
        worldUnits: true,
        resolution: new Vector2(1, 1), // Update resolution on resize!!!
    }));
}

async function toLineSegmentsGeometry(bufferGeometry: BufferGeometry) {
    const LineSegmentsGeometry = (await LineSegmentsGeometryImport).LineSegmentsGeometry;
    const lg = new LineSegmentsGeometry();

    const position = bufferGeometry.getAttribute('position');
    const indexAttribute = bufferGeometry.index!!;
    const positions = [];
    for (let index = 0; index != indexAttribute.count; ++index) {
        const i = indexAttribute.getX(index);
        const x = position.getX(i);
        const y = position.getY(i);
        const z = position.getZ(i);
        positions.push(x, y, z);
    }
    lg.setPositions(positions);

    const colors = [];
    const color = bufferGeometry.getAttribute('color');
    if (color) {
        for (let index = 0; index != indexAttribute.count; ++index) {
            const i = indexAttribute.getX(index);
            const r = color.getX(i);
            const g = color.getY(i);
            const b = color.getZ(i);
            colors.push(r, g, b);
        }
        lg.setColors(colors);
    }

    lg.userData = bufferGeometry.userData;
    return lg;
}