import * as THREE from 'three';
import { StructuralModel, NodePoint, DisplayMode } from '../../../types/structure';

export class WallLayer {
  public group: THREE.Group;
  public pickableObjects: THREE.Object3D[] = [];

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'WallLayer';
  }

  public update(
    model: StructuralModel,
    isVisible: boolean = true,
    displayMode: DisplayMode = 'extruded',
    selectedElementId: string | null = null,
    hoveredElementId: string | null = null,
    activeStoryFilter: string = 'all'
  ): void {
    this.clear();
    this.pickableObjects = [];
    if (!isVisible || !model.walls) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    model.walls.forEach(wall => {
      if (activeStoryFilter !== 'all' && wall.story !== activeStoryFilter) return;

      const corners = wall.nodeIds.map(nid => nodeMap.get(nid)).filter(Boolean) as NodePoint[];
      if (corners.length < 4) return;

      const n1 = corners[0]; // bottom 1
      const n2 = corners[1]; // bottom 2
      const n3 = corners[2]; // top 2
      const n4 = corners[3]; // top 1

      const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
      const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
      const length = p1.distanceTo(p2);
      const height = Math.abs(n4.y - n1.y) || 3.5;
      const thickness = wall.thickness || 0.25;

      const midBase = p1.clone().add(p2).multiplyScalar(0.5);
      const center = new THREE.Vector3(midBase.x, n1.y + height / 2, midBase.z);

      const isSelected = selectedElementId === wall.id;
      const isHovered = hoveredElementId === wall.id;

      // 3D Box geometry for vertical shear wall
      const wallGeo = new THREE.BoxGeometry(thickness, height, length);
      const wallMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0x96ccff : (isHovered ? 0xb0d8ff : 0x5a636e),
        roughness: 0.5,
        metalness: 0.2,
        transparent: true,
        opacity: displayMode === 'wireframe' ? 0.2 : 0.85,
        emissive: isSelected ? 0x003353 : 0x000000,
        emissiveIntensity: isSelected ? 0.5 : 0.0
      });

      const wallMesh = new THREE.Mesh(wallGeo, wallMat);
      wallMesh.position.copy(center);

      // Rotate wall according to span vector in XZ plane
      const spanDir = p2.clone().sub(p1).normalize();
      const angle = Math.atan2(spanDir.x, spanDir.z);
      wallMesh.rotation.y = angle;

      wallMesh.userData = { id: wall.id, type: 'wall', isPickable: true };
      this.group.add(wallMesh);
      this.pickableObjects.push(wallMesh);

      // Wireframe Outline
      const edgeGeo = new THREE.EdgesGeometry(wallGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: isSelected ? 0xffffff : (isHovered ? 0x96ccff : 0x2e3238),
        linewidth: isSelected ? 2 : 1
      });
      const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
      wallMesh.add(edgeLines);
    });
  }

  public clear(): void {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child instanceof THREE.Mesh) {
        if (child.geometry) child.geometry.dispose();
      }
      this.group.remove(child);
    }
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
