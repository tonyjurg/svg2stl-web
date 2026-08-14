import * as THREE from "./three.module.min.js";
import { OrbitControls } from "./OrbitControls.js";
import { STLLoader } from "./STLLoader.js";

/** Create a self-contained STL viewer in the supplied element. */
export function createStlViewer(container) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (error) {
    throw new Error("3D preview is unavailable because WebGL could not start.", {
      cause: error,
    });
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.className = "stl-canvas";
  renderer.domElement.setAttribute("aria-label", "Interactive STL preview");
  container.replaceChildren(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.01, 10000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.screenSpacePanning = true;
  controls.zoomToCursor = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x52656a, 2.5));
  const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
  keyLight.position.set(3, 5, 4);
  scene.add(keyLight);
  const fillLight = new THREE.DirectionalLight(0xbde9e4, 1.8);
  fillLight.position.set(-4, 2, -3);
  scene.add(fillLight);

  let mesh = null;
  let disposed = false;

  function render() {
    if (!disposed) renderer.render(scene, camera);
  }

  function resize() {
    if (disposed) return;
    const width = Math.max(container.clientWidth, 1);
    const height = Math.max(container.clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    render();
  }

  function fitView() {
    if (!mesh) return;
    const box = new THREE.Box3().setFromObject(mesh);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maximum = Math.max(size.x, size.y, size.z, 0.01);
    const distance = maximum / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    const fittedDistance = distance * 1.35;

    camera.near = Math.max(maximum / 1000, 0.001);
    camera.far = Math.max(maximum * 100, 100);
    camera.position.set(
      center.x + fittedDistance * 0.85,
      center.y + fittedDistance * 0.65,
      center.z + fittedDistance,
    );
    camera.updateProjectionMatrix();
    controls.target.copy(center);
    controls.minDistance = maximum * 0.08;
    controls.maxDistance = maximum * 40;
    controls.update();
    controls.saveState();
    resize();
  }

  function removeMesh() {
    if (!mesh) return;
    scene.remove(mesh);
    mesh.geometry.dispose();
    mesh.material.dispose();
    mesh = null;
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(container);
  controls.addEventListener("change", render);

  return {
    async load(blob) {
      if (disposed) throw new Error("The 3D preview has already been closed.");
      const geometry = new STLLoader().parse(await blob.arrayBuffer());
      if (!geometry.getAttribute("position")?.count) {
        geometry.dispose();
        throw new Error("The STL does not contain any triangles to preview.");
      }

      removeMesh();
      geometry.center();
      geometry.computeVertexNormals();
      mesh = new THREE.Mesh(
        geometry,
        new THREE.MeshStandardMaterial({
          color: 0x08766d,
          metalness: 0.05,
          roughness: 0.62,
          side: THREE.DoubleSide,
        }),
      );
      // STL uses Z as the extrusion axis; rotate it into Three.js's Y-up view.
      mesh.rotation.x = -Math.PI / 2;
      scene.add(mesh);
      fitView();
    },

    reset() {
      controls.reset();
      resize();
    },

    zoom(factor) {
      const offset = camera.position.clone().sub(controls.target);
      const distance = THREE.MathUtils.clamp(
        offset.length() / factor,
        controls.minDistance,
        controls.maxDistance,
      );
      camera.position.copy(controls.target).add(offset.setLength(distance));
      controls.update();
      resize();
    },

    resize,

    dispose() {
      if (disposed) return;
      disposed = true;
      resizeObserver.disconnect();
      controls.removeEventListener("change", render);
      controls.dispose();
      removeMesh();
      renderer.dispose();
      container.replaceChildren();
    },
  };
}
