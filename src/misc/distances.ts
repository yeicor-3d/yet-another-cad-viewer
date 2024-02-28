import {Vector3} from 'three';
import type {MObject3D} from "../tools/Selection.vue";


/**
 * Given two THREE.Object3D objects, returns their closest and farthest vertices, and the geometric centers.
 * All of them are approximated and should not be used for precise calculations.
 */
export function distances(
    a: InstanceType<typeof MObject3D>, b: InstanceType<typeof MObject3D>): {
    min: Array<Vector3>,
    center: Array<Vector3>,
    max: Array<Vector3>
} {
    // Simplify this problem (approximate) by using the distance between each of their vertices.
    // TODO: Compute actual min and max distances between the two objects.
    a.updateMatrixWorld();
    b.updateMatrixWorld();
    // FIXME: Working for points and lines, but not triangles...
    const aVertices = a.geometry.getAttribute('position').array;
    const aCenter = new Vector3();
    const bVertices = b.geometry.getAttribute('position').array;
    const bCenter = new Vector3();
    let minDistance = Infinity;
    let minDistanceVertices = [new Vector3(), new Vector3()];
    let maxDistance = -Infinity;
    let maxDistanceVertices = [new Vector3(), new Vector3()];
    for (let i = 0; i < aVertices.length; i += 3) {
        const v = new Vector3(aVertices[i], aVertices[i + 1], aVertices[i + 2]);
        //a.localToWorld(v);
        aCenter.add(v);
        for (let j = 0; j < bVertices.length; j += 3) {
            const w = new Vector3(bVertices[j], bVertices[j + 1], bVertices[j + 2]);
            //b.localToWorld(w);
            bCenter.add(w);
            const d = v.distanceTo(w);
            if (d < minDistance) {
                minDistance = d;
                minDistanceVertices = [v, w];
            }
            if (d > maxDistance) {
                maxDistance = d;
                maxDistanceVertices = [v, w];
            }
        }
    }
    aCenter.divideScalar(aVertices.length / 3);
    bCenter.divideScalar(bVertices.length / 3);
    return {
        min: minDistanceVertices,
        center: [aCenter, bCenter],
        max: maxDistanceVertices
    };
}