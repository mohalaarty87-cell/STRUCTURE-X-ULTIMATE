import * as THREE from 'three';
import { StructuralModel, NodePoint, DisplayMode } from '../../../types/structure';

export class ShellLayer {
  public group: THREE.Group;
  public pickableObjects: THREE.Object3D[] = [];

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'ShellLayer';
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
    if (!isVisible) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    model.slabs.forEach(slab => {
      if (activeStoryFilter !== 'all' && slab.story !== activeStoryFilter) return;

      const corners = slab.nodeIds.map(nid => nodeMap.get(nid)).filter(Boolean) as NodePoint[];
      if (corners.length < 4) return;

      const minX = Math.min(...corners.map(c => c.x));
      const maxX = Math.max(...corners.map(c => c.x));
      const minZ = Math.min(...corners.map(c => c.z));
      const maxZ = Math.max(...corners.map(c => c.z));
      const elev = corners[0].y;

      const width = maxX - minX;
      const depth = maxZ - minZ;
      const centerX = (minX + maxX) / 2;
      const centerZ = (minZ + maxZ) / 2;

      const isSelected = selectedElementId === slab.id;
      const isHovered = hoveredElementId === slab.id;

      // Slab 3D Box geometry
      const slabGeo = new THREE.BoxGeometry(width, slab.thickness || 0.2, depth);
      const slabMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0x96ccff : (isHovered ? 0xb0d8ff : 0x707880),
        transparent: true,
        opacity: displayMode === 'wireframe' ? 0.15 : 0.65,
        roughness: 0.65,
        metalness: 0.1,
        emissive: isSelected ? 0x003353 : 0x000000,
        emissiveIntensity: isSelected ? 0.4 : 0.0
      });

      const slabMesh = new THREE.Mesh(slabGeo, slabMat);
      slabMesh.position.set(centerX, elev - (slab.thickness || 0.2) / 2, centerZ);
      slabMesh.userData = { id: slab.id, type: 'slab', isPickable: true };
      this.group.add(slabMesh);
      this.pickableObjects.push(slabMesh);

      // Edge wireframe outline
      const edgeGeo = new THREE.EdgesGeometry(slabGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: isSelected ? 0xffffff : (isHovered ? 0x96ccff : 0x383c42),
        linewidth: isSelected ? 2 : 1
      });
      const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
      slabMesh.add(edgeLines);

      // Slabs internal sub-mesh lines to indicate FEA 2D Plate Discretization
      this.createSubMeshGrid(minX, maxX, minZ, maxZ, elev, slabMesh);
    });
  }

  private createSubMeshGrid(minX: number, maxX: number, minZ: number, maxZ: number, elev: number, parent: THREE.Mesh): void {
    const nx = 4;
    const nz = 3;
    const dx = (maxX - minX) / nx;
    const dz = (maxZ - minZ) / nz;
    const pts: THREE.Vector3[] = [];

    // Internal mesh lines
    for (let i = 1; i < nx; i++) {
      const x = minX + i * dx - parent.position.x;
      pts.push(new THREE.Vector3(x, 0.101, minZ - parent.position.z));
      pts.push(new THREE.Vector3(x, 0.101, maxZ - parent.position.z));
    }
    for (let j = 1; j < nz; j++) {
      const z = minZ + j * dz - parent.position.z;
      pts.push(new THREE.Vector3(minX - parent.position.x, 0.101, z));
      pts.push(new THREE.Vector3(maxX - parent.position.x, 0.101, z));
    }

    if (pts.length > 0) {
      const meshGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const meshMat = new THREE.LineBasicMaterial({ color: 0x4a5058, transparent: true, opacity: 0.4 });
      const internalLines = new THREE.LineSegments(meshGeo, meshMat);
      parent.add(internalLines);
    }
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
