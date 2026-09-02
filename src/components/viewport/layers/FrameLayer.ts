import * as THREE from 'three';
import { StructuralModel, NodePoint, SectionProperty, Material, DisplayMode } from '../../../types/structure';

export class FrameLayer {
  public group: THREE.Group;
  public pickableObjects: THREE.Object3D[] = [];

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'FrameLayer';
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
    const secMap = new Map<string, SectionProperty>(model.sections.map(s => [s.id, s]));
    const matMap = new Map<string, Material>(model.materials.map(m => [m.id, m]));

    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;

      const n1 = nodeMap.get(member.startNodeId);
      const n2 = nodeMap.get(member.endNodeId);
      if (!n1 || !n2) return;

      const v1 = new THREE.Vector3(n1.x, n1.y, n1.z);
      const v2 = new THREE.Vector3(n2.x, n2.y, n2.z);
      const dir = v2.clone().sub(v1);
      const length = dir.length();
      if (length <= 0.001) return;
      const mid = v1.clone().add(v2).multiplyScalar(0.5);

      const isSelected = selectedElementId === member.id;
      const isHovered = hoveredElementId === member.id;
      const isColumn = member.type === 'column';
      const section = secMap.get(member.sectionId);
      const width = (section?.dimensions.width || 400) / 1000;
      const height = (section?.dimensions.height || 400) / 1000;

      // Color computation
      let colorHex = isColumn ? 0x2f4f4f : 0x4682b4; // Default CAD slate / steel
      if (displayMode === 'stress' && member.forces) {
        const u = member.forces.utilizationRatio;
        if (u < 0.5) colorHex = 0x3b82f6; // Blue (Low)
        else if (u < 0.75) colorHex = 0x22c55e; // Green (Optimal)
        else if (u < 0.9) colorHex = 0xeab308; // Yellow (Warning)
        else colorHex = 0xef4444; // Red (Critical)
      } else if (displayMode === 'axial' && member.forces) {
        colorHex = member.forces.axialP < 0 ? 0x3b82f6 : 0xef4444; // Compression blue / Tension red
      } else if (isSelected) {
        colorHex = 0x96ccff;
      } else if (isHovered) {
        colorHex = 0xcee5ff;
      }

      if (displayMode === 'wireframe') {
        // Centerline 1D Line Element
        const lineGeo = new THREE.BufferGeometry().setFromPoints([v1, v2]);
        const lineMat = new THREE.LineBasicMaterial({
          color: isSelected ? 0x96ccff : (isHovered ? 0xffffff : (isColumn ? 0x7ed99e : 0x96ccff)),
          linewidth: isSelected ? 3 : 1
        });
        const line = new THREE.Line(lineGeo, lineMat);
        line.userData = { id: member.id, type: member.type, isPickable: true };
        this.group.add(line);
        this.pickableObjects.push(line);
      } else {
        // 3D Extruded Solid Member
        const boxGeo = new THREE.BoxGeometry(width, length, height);
        const boxMat = new THREE.MeshStandardMaterial({
          color: colorHex,
          roughness: 0.45,
          metalness: member.materialId.includes('steel') ? 0.75 : 0.15,
          emissive: isSelected ? 0x003353 : (isHovered ? 0x1a2b3c : 0x000000),
          emissiveIntensity: isSelected ? 0.6 : (isHovered ? 0.3 : 0.0)
        });

        const mesh = new THREE.Mesh(boxGeo, boxMat);
        mesh.position.copy(mid);

        // Orient along span vector
        const defaultAxis = new THREE.Vector3(0, 1, 0);
        const quat = new THREE.Quaternion().setFromUnitVectors(defaultAxis, dir.clone().normalize());
        mesh.setRotationFromQuaternion(quat);

        mesh.userData = { id: member.id, type: member.type, isPickable: true };
        this.group.add(mesh);
        this.pickableObjects.push(mesh);

        // Edge Chamfer / Wireframe outline for clear CAD aesthetics
        const wireGeo = new THREE.EdgesGeometry(boxGeo);
        const wireMat = new THREE.LineBasicMaterial({
          color: isSelected ? 0xffffff : (isHovered ? 0x96ccff : 0x1f2327),
          linewidth: isSelected ? 2 : 1
        });
        const wireSegments = new THREE.LineSegments(wireGeo, wireMat);
        mesh.add(wireSegments);
      }
    });
  }

  public clear(): void {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
        if (child.geometry) child.geometry.dispose();
      }
      this.group.remove(child);
    }
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
