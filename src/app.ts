import * as THREE from "three";
import {Box3, Matrix4, Vector3} from "three";
import {OrbitControls} from "three/examples/jsm/controls/OrbitControls";
import {GLTFLoader} from "three/examples/jsm/loaders/GLTFLoader";
import {OrientationGizmo} from "./orientation";
import * as Stats from "stats.js";

export class App {
    renderer = new THREE.WebGLRenderer({antialias: true});
    //camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.01, 1000);
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 1000);
    private controls = new OrbitControls(this.camera, this.renderer.domElement);
    // CAD has Z up, so rotate the scene to match
    scene = new THREE.Scene();
    private helperGroup = new THREE.Group();
    private modelGroup = new THREE.Group();
    loader = new GLTFLoader();
    private gizmo = new OrientationGizmo(this.camera, this.controls);
    private stats = new Stats();

    install() {
        // Prepare camera and scene
        //this.setupSceneHelpers(new THREE.Box3().setFromCenterAndSize(new THREE.Vector3(), new THREE.Vector3(10, 10, 10)));
        // this.helperGroup.setRotationFromMatrix(this.threeToCad)
        this.scene.add(this.helperGroup);
        // this.modelGroup.setRotationFromMatrix(this.threeToCad)
        this.scene.add(this.modelGroup);
        // Set up renderer
        document.body.appendChild(this.renderer.domElement);
        this.renderer.setAnimationLoop(this._loop.bind(this));
        // On window resize, also resize the renderer
        let onResize = () => {
            this.renderer.setSize(window.innerWidth, window.innerHeight);
            if (this.camera instanceof THREE.PerspectiveCamera) {
                this.camera.aspect = window.innerWidth / window.innerHeight;
            } else {
                const aspect = window.innerWidth / window.innerHeight;
                const frustumSize = 2
                this.camera.left = - frustumSize * aspect / 2;
                this.camera.right = frustumSize * aspect / 2;
                this.camera.top = frustumSize / 2;
                this.camera.bottom = - frustumSize / 2;
            }
            this.camera.updateProjectionMatrix();
        };
        window.addEventListener('resize', onResize);
        onResize()
        // Misc installation
        this.gizmo.install();
        document.body.appendChild(this.stats.dom)
        this.stats.dom.style.left = '';
        this.stats.dom.style.right = '0px';
        this.stats.dom.style.top = '120px';
        this.stats.showPanel(1); // 0: fps, 1: ms, 2: mb, 3+: custom
    }

    private setupSceneHelpers(bb: Box3) { // The bounding box in three.js coordinates
        this.helperGroup.clear();
        let center = bb.getCenter(new THREE.Vector3());
        this.helperGroup.applyMatrix4(new Matrix4().makeTranslation(center))
        let size = bb.getSize(new THREE.Vector3());
        console.log(center, size)
        this.controls.target.set(center.x, center.y, center.z);
        this.camera.position.set(center.x, center.y, center.z);
        this.camera.position.x += size.x * 0.75;
        this.camera.position.y += size.y * 0.5;
        this.camera.position.z += size.z;
        this.controls.update()
        this.helperGroup.add(new THREE.HemisphereLight(0xffffff, 0x444444))
        let gridXZ = new THREE.GridHelper(1, 10);
        gridXZ.applyMatrix4(new Matrix4().makeTranslation(new Vector3(0, -size.y / 2, 0)))
        gridXZ.scale.set(size.x, 1, size.z)
        this.helperGroup.add(gridXZ)
        let gridXY = new THREE.GridHelper(1, 10);
        gridXY.applyMatrix4(new Matrix4().makeRotationX(Math.PI / 2))
        gridXY.applyMatrix4(new Matrix4().makeTranslation(new Vector3(0, 0, -size.z / 2)))
        gridXY.scale.set(size.x, 1, size.y)
        this.helperGroup.add(gridXY)
        let gridYZ = new THREE.GridHelper(1, 10);
        gridYZ.applyMatrix4(new Matrix4().makeRotationZ(Math.PI / 2))
        gridYZ.applyMatrix4(new Matrix4().makeTranslation(new Vector3(-size.x / 2, 0, 0)))
        // noinspection JSSuspiciousNameCombination
        gridYZ.scale.set(size.y, 1, size.z)
        this.helperGroup.add(gridYZ)
        let axes = new THREE.AxesHelper(size.length() / 4);
        axes.applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2)) // Y-up to Z-up (reference-only)
        this.helperGroup.add(axes)
    }

    addModel(url: string) {
        this.loader.loadAsync(url, console.log).then((model) => {
            this.modelGroup.add(model.scene)
            this.setupSceneHelpers(new THREE.Box3().setFromObject(model.scene));
        });
    }

    _loop(time) {
        this.stats.begin();
        this.controls.update();
        this.gizmo.update();
        this.renderer.render(this.scene, this.camera);
        this.stats.end();
        this.stats.update();
    }
}