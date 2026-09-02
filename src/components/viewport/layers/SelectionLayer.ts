import * as THREE from 'three';
import { StructuralModel, NodePoint, SectionProperty } from '../../../types/structure';

export class SelectionLayer {
  public group: THREE.Group;
  private selectionBox: THREE.BoxHelper | null = null;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'SelectionLayer';
  }

  public update(
    model: StructuralModel,
    selectedElementId: string | null = null,
    hoveredElementId: string | null = null,
    isVisible: boolean = true
  ): void {
    this.clear();
    if (!isVisible) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));
    const secMap = new Map<string, SectionProperty>(model.sections.map(s => [s.id, s]));

    // 1. Highlight Selected Member
    if (selectedElementId) {
      const member = model.members.find(m => m.id === selectedElementId);
      if (member) {
        const n1 = nodeMap.get(member.startNodeId);
        const n2 = nodeMap.get(member.endNodeId);
        if (n1 && n2) {
          const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
          const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
          const mid = p1.clone().add(p2).multiplyScalar(0.5);
          const dir = p2.clone().sub(p1);
          const len = dir.length();

          const sec = secMap.get(member.sectionId);
          const w = ((sec?.dimensions.width || 400) / 1000) * 1.15;
          const h = ((sec?.dimensions.height || 400) / 1000) * 1.15;

          // Glowing wireframe cage
          const cageGeo = new THREE.BoxGeometry(w, len + 0.05, h);
          const edgeGeo = new THREE.EdgesGeometry(cageGeo);
          const edgeMat = new THREE.LineBasicMaterial({
            color: 0x96ccff,
            linewidth: 3,
            transparent: true,
            opacity: 0.95
          });
          const cage = new THREE.LineSegments(edgeGeo, edgeMat);
          cage.position.copy(mid);

          const defaultAxis = new THREE.Vector3(0, 1, 0);
          const quat = new THREE.Quaternion().setFromUnitVectors(defaultAxis, dir.clone().normalize());
          cage.setRotationFromQuaternion(quat);

          this.group.add(cage);

          // Corner Grip Nodes (CAD Handles)
          this.createGripHandle(p1, 0x96ccff);
          this.createGripHandle(p2, 0x96ccff);
        }
      }

      // Selected Slab
      const slab = model.slabs.find(s => s.id === selectedElementId);
      if (slab) {
        const corners = slab.nodeIds.map(nid => nodeMap.get(nid)).filter(Boolean) as NodePoint[];
        if (corners.length >= 4) {
          const minX = Math.min(...corners.map(c => c.x)) - 0.05;
          const maxX = Math.max(...corners.map(c => c.x)) + 0.05;
          const minZ = Math.min(...corners.map(c => c.z)) - 0.05;
          const maxZ = Math.max(...corners.map(c => c.z)) + 0.05;
          const elev = corners[0].y;

          const boxGeo = new THREE.BoxGeometry(maxX - minX, (slab.thickness || 0.2) * 1.3, maxZ - minZ);
          const edgeGeo = new THREE.EdgesGeometry(boxGeo);
          const edgeMat = new THREE.LineBasicMaterial({ color: 0x96ccff, linewidth: 3 });
          const cage = new THREE.LineSegments(edgeGeo, edgeMat);
          cage.position.set((minX + maxX) / 2, elev - (slab.thickness || 0.2) / 2, (minZ + maxZ) / 2);
          this.group.add(cage);

          corners.forEach(c => this.createGripHandle(new THREE.Vector3(c.x, c.y, c.z), 0x96ccff));
        }
      }
    }

    // 2. Highlight Hovered Element (Subtle indicator)
    if (hoveredElementId && hoveredElementId !== selectedElementId) {
      const hMember = model.members.find(m => m.id === hoveredElementId);
      if (hMember) {
        const n1 = nodeMap.get(hMember.startNodeId);
        const n2 = nodeMap.get(hMember.endNodeId);
        if (n1 && n2) {
          const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
          const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
          const lineGeo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
          const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 });
          const hoverLine = new THREE.Line(lineGeo, lineMat);
          this.group.add(hoverLine);
        }
      }
    }
  }

  private createGripHandle(position: THREE.Vector3, color: number): void {
    const geo = new THREE.BoxGeometry(0.18, 0.18, 0.18);
    const mat = new THREE.MeshBasicMaterial({ color });
    const grip = new THREE.Mesh(geo, mat);
    grip.position.copy(position);
    this.group.add(grip);
  }

  public clear(): void {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child instanceof THREE.Mesh || child instanceof THREE.LineSegments || child instanceof THREE.Line) {
        if (child.geometry) child.geometry.dispose();
      }
      this.group.remove(child);
    }
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
