import {BufferAttribute, InterleavedBufferAttribute, Vector3} from 'three';
import type {MObject3D} from "../tools/Selection.vue";
import type {ModelScene} from '@google/model-viewer/lib/three-components/ModelScene';
import type {SelectionInfo} from "../tools/selection";


function getCenterAndVertexList(selInfo: SelectionInfo, scene: ModelScene): {
    center: Vector3,
    vertices: Array<Vector3>
} {
    selInfo.object.updateMatrixWorld();
    let pos: BufferAttribute | InterleavedBufferAttribute = selInfo.object.geometry.getAttribute('position');
    let ind: BufferAttribute | null = selInfo.object.geometry.index;
    if (ind === null) {
        ind = new BufferAttribute(new Uint16Array(pos.count), 1);
        for (let i = 0; i < pos.count; i++) {
            ind.array[i] = i;
        }
    }
    let center = new Vector3();
    let vertices = [];
    for (let i = selInfo.indices[0]; i < selInfo.indices[1]; i++) {
        let index = ind.getX(i)
        let vertex = new Vector3(pos.getX(index), pos.getY(index), pos.getZ(index));
        vertex = scene.target.worldToLocal(selInfo.object.localToWorld(vertex));
        center.add(vertex);
        vertices.push(vertex);
    }
    center = center.divideScalar(selInfo.indices[1] - selInfo.indices[0]);
    return {center, vertices};
}

/**
 * Given two THREE.Object3D objects, returns their closest and farthest vertices, and the geometric centers.
 * All of them are approximated and should not be used for precise calculations.
 */
export function distances(a: SelectionInfo, b: SelectionInfo, scene: ModelScene): {
    min: Array<Vector3>,
    center: Array<Vector3>,
    max: Array<Vector3>
} {
    // Simplify this problem (approximate) by using the distance between each of their vertices.
    // Find the center of each object.
    let {center: aCenter, vertices: aVertices} = getCenterAndVertexList(a, scene);
    let {center: bCenter, vertices: bVertices} = getCenterAndVertexList(b, scene);

    // Find the closest and farthest vertices.
    // TODO: Compute actual min and max distances between the two objects.
    // FIXME: Really slow... (use a BVH or something)
    let minDistance = Infinity;
    let minDistanceVertices = [new Vector3(), new Vector3()];
    let maxDistance = -Infinity;
    let maxDistanceVertices = [new Vector3(), new Vector3()];
    for (let i = 0; i < aVertices.length; i++) {
        for (let j = 0; j < bVertices.length; j++) {
            let distance = aVertices[i].distanceTo(bVertices[j]);
            if (distance < minDistance) {
                minDistance = distance;
                minDistanceVertices[0] = aVertices[i];
                minDistanceVertices[1] = bVertices[j];
            }
            if (distance > maxDistance) {
                maxDistance = distance;
                maxDistanceVertices[0] = aVertices[i];
                maxDistanceVertices[1] = bVertices[j];
            }
        }
    }

    // Return the results.
    return {
        min: minDistanceVertices,
        center: [aCenter, bCenter],
        max: maxDistanceVertices
    };
}