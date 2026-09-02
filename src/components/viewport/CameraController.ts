import * as THREE from 'three';
import { CameraProjection, CameraPreset, StructuralModel } from '../../types/structure';

export class CameraController {
  public perspectiveCamera: THREE.PerspectiveCamera;
  public orthographicCamera: THREE.OrthographicCamera;
  public activeCamera: THREE.Camera;
  public projection: CameraProjection = 'perspective';
  public target: THREE.Vector3 = new THREE.Vector3(0, 3.5, 0);

  private width: number = 800;
  private height: number = 600;
  private orthoFrustumSize: number = 22;

  // Spherical orbit coordinates for smooth manipulation
  public radius: number = 25;
  public theta: number = Math.PI / 4; // Azimuth angle (45 deg)
  public phi: number = Math.PI / 3;   // Polar angle (60 deg from top)

  constructor(width: number, height: number) {
    this.width = width;
    this.height = height;
    const aspect = width / height;

    // 1. Perspective Camera
    this.perspectiveCamera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
    this.perspectiveCamera.position.set(18, 14, 20);
    this.perspectiveCamera.lookAt(this.target);

    // 2. Orthographic Camera
    const halfH = this.orthoFrustumSize / 2;
    const halfW = halfH * aspect;
    this.orthographicCamera = new THREE.OrthographicCamera(-halfW, halfW, halfH, -halfH, 0.1, 1000);
    this.orthographicCamera.position.set(18, 14, 20);
    this.orthographicCamera.lookAt(this.target);

    this.activeCamera = this.perspectiveCamera;
  }

  public setSize(width: number, height: number): void {
    this.width = width;
    this.height = height;
    const aspect = width / height;

    this.perspectiveCamera.aspect = aspect;
    this.perspectiveCamera.updateProjectionMatrix();

    const halfH = this.orthoFrustumSize / 2;
    const halfW = halfH * aspect;
    this.orthographicCamera.left = -halfW;
    this.orthographicCamera.right = halfW;
    this.orthographicCamera.top = halfH;
    this.orthographicCamera.bottom = -halfH;
    this.orthographicCamera.updateProjectionMatrix();
  }

  public setProjection(projection: CameraProjection): void {
    this.projection = projection;
    const currentPos = this.activeCamera.position.clone();
    if (projection === 'perspective') {
      this.perspectiveCamera.position.copy(currentPos);
      this.perspectiveCamera.lookAt(this.target);
      this.activeCamera = this.perspectiveCamera;
    } else {
      this.orthographicCamera.position.copy(currentPos);
      this.orthographicCamera.lookAt(this.target);
      this.activeCamera = this.orthographicCamera;
    }
    this.setSize(this.width, this.height);
  }

  public applyPreset(preset: CameraPreset, model?: StructuralModel): void {
    const center = this.target.clone();

    switch (preset) {
      case 'plan': // Top XY (Looking down from +Y to -Y)
        this.theta = 0;
        this.phi = 0.001;
        this.activeCamera.position.set(center.x, center.y + this.radius, center.z + 0.001);
        this.activeCamera.up.set(0, 0, -1);
        break;

      case 'elevation-xz': // Front View (Looking from +Z to -Z)
        this.theta = 0;
        this.phi = Math.PI / 2;
        this.activeCamera.position.set(center.x, center.y, center.z + this.radius);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'elevation-yz': // Side View (Looking from +X to -X)
        this.theta = Math.PI / 2;
        this.phi = Math.PI / 2;
        this.activeCamera.position.set(center.x + this.radius, center.y, center.z);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'iso-ne': // 3D Isometric North-East
        this.theta = Math.PI / 4;
        this.phi = Math.PI / 3;
        this.activeCamera.position.set(center.x + 18, center.y + 14, center.z + 18);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'iso-nw': // 3D Isometric North-West
        this.theta = -Math.PI / 4;
        this.phi = Math.PI / 3;
        this.activeCamera.position.set(center.x - 18, center.y + 14, center.z + 18);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'iso-se': // 3D Isometric South-East
        this.theta = (3 * Math.PI) / 4;
        this.phi = Math.PI / 3;
        this.activeCamera.position.set(center.x + 18, center.y + 14, center.z - 18);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'iso-sw': // 3D Isometric South-West
        this.theta = -(3 * Math.PI) / 4;
        this.phi = Math.PI / 3;
        this.activeCamera.position.set(center.x - 18, center.y + 14, center.z - 18);
        this.activeCamera.up.set(0, 1, 0);
        break;

      case 'iso':
      default:
        this.theta = Math.PI / 4;
        this.phi = Math.PI / 3;
        this.activeCamera.position.set(center.x + 16, center.y + 12, center.z + 18);
        this.activeCamera.up.set(0, 1, 0);
        break;
    }

    this.activeCamera.lookAt(this.target);
    if (this.projection === 'orthographic') {
      this.orthographicCamera.position.copy(this.activeCamera.position);
      this.orthographicCamera.lookAt(this.target);
      this.orthographicCamera.updateProjectionMatrix();
    } else {
      this.perspectiveCamera.position.copy(this.activeCamera.position);
      this.perspectiveCamera.lookAt(this.target);
      this.perspectiveCamera.updateProjectionMatrix();
    }
  }

  public fitModel(model: StructuralModel): void {
    if (model.nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    model.nodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
      if (n.z < minZ) minZ = n.z;
      if (n.z > maxZ) maxZ = n.z;
    });

    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const cz = (minZ + maxZ) / 2;
    this.target.set(cx, cy, cz);

    const sizeX = maxX - minX;
    const sizeY = maxY - minY;
    const sizeZ = maxZ - minZ;
    const maxDim = Math.max(sizeX, sizeY, sizeZ, 8);

    this.radius = maxDim * 1.75;
    this.orthoFrustumSize = maxDim * 1.5;

    this.applyPreset('iso', model);
    this.setSize(this.width, this.height);
  }

  public orbit(deltaX: number, deltaY: number): void {
    const speed = 0.005;
    this.theta -= deltaX * speed;
    this.phi = Math.max(0.05, Math.min(Math.PI - 0.05, this.phi + deltaY * speed));

    const x = this.target.x + this.radius * Math.sin(this.phi) * Math.sin(this.theta);
    const y = this.target.y + this.radius * Math.cos(this.phi);
    const z = this.target.z + this.radius * Math.sin(this.phi) * Math.cos(this.theta);

    this.activeCamera.position.set(x, y, z);
    this.activeCamera.lookAt(this.target);
  }

  public pan(deltaX: number, deltaY: number): void {
    const factor = this.projection === 'orthographic' ? (this.orthoFrustumSize / this.height) : (this.radius * 0.0015);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(this.activeCamera.quaternion);
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(this.activeCamera.quaternion);

    const panOffset = right.clone().multiplyScalar(-deltaX * factor).add(up.clone().multiplyScalar(deltaY * factor));
    this.target.add(panOffset);
    this.activeCamera.position.add(panOffset);
  }

  public zoom(delta: number): void {
    if (this.projection === 'perspective') {
      const zoomFactor = delta > 0 ? 1.1 : 0.9;
      const dir = this.activeCamera.position.clone().sub(this.target);
      this.radius = Math.max(2, Math.min(250, dir.length() * zoomFactor));
      dir.normalize().multiplyScalar(this.radius);
      this.activeCamera.position.copy(this.target.clone().add(dir));
      this.perspectiveCamera.updateProjectionMatrix();
    } else {
      const zoomFactor = delta > 0 ? 1.1 : 0.9;
      this.orthoFrustumSize = Math.max(2, Math.min(200, this.orthoFrustumSize * zoomFactor));
      this.setSize(this.width, this.height);
    }
  }
}
