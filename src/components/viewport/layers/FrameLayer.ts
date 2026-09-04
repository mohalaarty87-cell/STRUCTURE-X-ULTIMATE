import * as THREE from 'three';
import { StructuralModel, NodePoint, SectionProperty, Material, DisplayMode } from '../../../types/structure';

/**
 * High-Performance Frame Layer
 * PHASE 15 — Optimized for 1,000 to 50,000+ structural members.
 * 
 * Uses:
 * - THREE.InstancedMesh with unit box geometry (single draw call for tens of thousands of solid members)
 * - THREE.LineSegments with single contiguous Float32Array (single draw call for wireframe)
 * - O(1) instance-to-element mapping for raycasting/picking
 * - Dynamic color buffer updates on selection/hover/stress display
 * - Full resource disposal to prevent WebGL memory leaks
 */
export class FrameLayer {
  public group: THREE.Group;
  public pickableObjects: THREE.Object3D[] = [];

  // Instancing structures
  private instancedMesh: THREE.InstancedMesh | null = null;
  private lineSegments: THREE.LineSegments | null = null;
  private instanceToMemberMap: string[] = [];
  private memberToInstanceMap: Map<string, number> = new Map();
  private sharedBoxGeo: THREE.BoxGeometry | null = null;
  private sharedMat: THREE.MeshStandardMaterial | null = null;
  private sharedLineGeo: THREE.BufferGeometry | null = null;
  private sharedLineMat: THREE.LineBasicMaterial | null = null;

  // Highlight overlay for selected element
  private selectionMesh: THREE.Mesh | null = null;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'FrameLayer_Optimized';
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
    if (!isVisible || model.members.length === 0) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));
    const secMap = new Map<string, SectionProperty>(model.sections.map(s => [s.id, s]));

    // Filter members by story
    const activeMembers = model.members.filter(m => 
      activeStoryFilter === 'all' || m.story === activeStoryFilter
    );

    const count = activeMembers.length;
    if (count === 0) return;

    this.instanceToMemberMap = new Array(count);
    this.memberToInstanceMap.clear();

    if (displayMode === 'wireframe') {
      // High-Performance Batched LineSegments (1 draw call for all members)
      const positions = new Float32Array(count * 6);
      const colors = new Float32Array(count * 6);
      const colObj = new THREE.Color();

      let validLines = 0;
      activeMembers.forEach((member, i) => {
        const n1 = nodeMap.get(member.startNodeId);
        const n2 = nodeMap.get(member.endNodeId);
        if (!n1 || !n2) return;

        const isSelected = selectedElementId === member.id;
        const isHovered = hoveredElementId === member.id;
        const isColumn = member.type === 'column';

        let hex = isSelected ? 0x96ccff : (isHovered ? 0xffffff : (isColumn ? 0x7ed99e : 0x96ccff));
        colObj.setHex(hex);

        const pIdx = validLines * 6;
        positions[pIdx + 0] = n1.x;
        positions[pIdx + 1] = n1.y;
        positions[pIdx + 2] = n1.z;
        positions[pIdx + 3] = n2.x;
        positions[pIdx + 4] = n2.y;
        positions[pIdx + 5] = n2.z;

        colors[pIdx + 0] = colObj.r;
        colors[pIdx + 1] = colObj.g;
        colors[pIdx + 2] = colObj.b;
        colors[pIdx + 3] = colObj.r;
        colors[pIdx + 4] = colObj.g;
        colors[pIdx + 5] = colObj.b;

        this.instanceToMemberMap[validLines] = member.id;
        this.memberToInstanceMap.set(member.id, validLines);
        validLines++;
      });

      this.sharedLineGeo = new THREE.BufferGeometry();
      this.sharedLineGeo.setAttribute('position', new THREE.BufferAttribute(positions.subarray(0, validLines * 6), 3));
      this.sharedLineGeo.setAttribute('color', new THREE.BufferAttribute(colors.subarray(0, validLines * 6), 3));

      this.sharedLineMat = new THREE.LineBasicMaterial({
        vertexColors: true,
        linewidth: 1
      });

      this.lineSegments = new THREE.LineSegments(this.sharedLineGeo, this.sharedLineMat);
      this.lineSegments.userData = { isFrameBatch: true, isPickable: true };
      this.group.add(this.lineSegments);
      this.pickableObjects.push(this.lineSegments);

    } else {
      // High-Performance InstancedMesh (1 draw call for all solid members)
      this.sharedBoxGeo = new THREE.BoxGeometry(1, 1, 1);
      this.sharedMat = new THREE.MeshStandardMaterial({
        roughness: 0.45,
        metalness: 0.25,
        color: 0xffffff // multiplied with instanceColor
      });

      this.instancedMesh = new THREE.InstancedMesh(this.sharedBoxGeo, this.sharedMat, count);
      this.instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      this.instancedMesh.userData = { isInstancedFrame: true, isPickable: true };

      const dummy = new THREE.Object3D();
      const defaultAxis = new THREE.Vector3(0, 1, 0);
      const colObj = new THREE.Color();

      let validInstances = 0;

      activeMembers.forEach((member) => {
        const n1 = nodeMap.get(member.startNodeId);
        const n2 = nodeMap.get(member.endNodeId);
        if (!n1 || !n2) return;

        const v1 = new THREE.Vector3(n1.x, n1.y, n1.z);
        const v2 = new THREE.Vector3(n2.x, n2.y, n2.z);
        const dir = v2.clone().sub(v1);
        const length = dir.length();
        if (length <= 0.0001) return;

        const mid = v1.clone().add(v2).multiplyScalar(0.5);
        const isColumn = member.type === 'column';
        const section = secMap.get(member.sectionId);
        const width = (section?.dimensions.width || 350) / 1000;
        const height = (section?.dimensions.height || 350) / 1000;

        // Position, Rotation, Scale Matrix
        dummy.position.copy(mid);
        const quat = new THREE.Quaternion().setFromUnitVectors(defaultAxis, dir.clone().normalize());
        dummy.setRotationFromQuaternion(quat);
        dummy.scale.set(width, length, height);
        dummy.updateMatrix();

        this.instancedMesh!.setMatrixAt(validInstances, dummy.matrix);

        // Color computation
        const isSelected = selectedElementId === member.id;
        const isHovered = hoveredElementId === member.id;
        let hex = isColumn ? 0x2f4f4f : 0x4682b4; // Default steel / column slate

        if (displayMode === 'stress' && member.forces) {
          const u = member.forces.utilizationRatio;
          if (u < 0.5) hex = 0x3b82f6; // Blue
          else if (u < 0.75) hex = 0x22c55e; // Green
          else if (u < 0.9) hex = 0xeab308; // Yellow
          else hex = 0xef4444; // Red
        } else if (displayMode === 'axial' && member.forces) {
          hex = member.forces.axialP < 0 ? 0x3b82f6 : 0xef4444;
        }

        if (isSelected) hex = 0x96ccff;
        else if (isHovered) hex = 0xcee5ff;

        colObj.setHex(hex);
        this.instancedMesh!.setColorAt(validInstances, colObj);

        this.instanceToMemberMap[validInstances] = member.id;
        this.memberToInstanceMap.set(member.id, validInstances);
        validInstances++;
      });

      this.instancedMesh.count = validInstances;
      this.instancedMesh.instanceMatrix.needsUpdate = true;
      if (this.instancedMesh.instanceColor) {
        this.instancedMesh.instanceColor.needsUpdate = true;
      }

      this.group.add(this.instancedMesh);
      this.pickableObjects.push(this.instancedMesh);

      // Dedicated Highlight Box for Selected Element to ensure crisp visibility
      if (selectedElementId && this.memberToInstanceMap.has(selectedElementId)) {
        const instIdx = this.memberToInstanceMap.get(selectedElementId)!;
        const matrix = new THREE.Matrix4();
        this.instancedMesh.getMatrixAt(instIdx, matrix);

        const selGeo = new THREE.BoxGeometry(1.04, 1.01, 1.04);
        const selMat = new THREE.MeshBasicMaterial({
          color: 0x96ccff,
          wireframe: true
        });
        this.selectionMesh = new THREE.Mesh(selGeo, selMat);
        this.selectionMesh.applyMatrix4(matrix);
        this.group.add(this.selectionMesh);
      }
    }
  }

  /**
   * Fast O(1) element lookup from raycaster intersection.
   */
  public getMemberIdFromIntersection(intersection: THREE.Intersection): string | null {
    if (intersection.instanceId !== undefined && intersection.instanceId !== null) {
      return this.instanceToMemberMap[intersection.instanceId] || null;
    }
    return null;
  }

  public clear(): void {
    if (this.instancedMesh) {
      this.group.remove(this.instancedMesh);
      this.instancedMesh.dispose();
      this.instancedMesh = null;
    }
    if (this.sharedBoxGeo) {
      this.sharedBoxGeo.dispose();
      this.sharedBoxGeo = null;
    }
    if (this.sharedMat) {
      this.sharedMat.dispose();
      this.sharedMat = null;
    }
    if (this.lineSegments) {
      this.group.remove(this.lineSegments);
      this.lineSegments = null;
    }
    if (this.sharedLineGeo) {
      this.sharedLineGeo.dispose();
      this.sharedLineGeo = null;
    }
    if (this.sharedLineMat) {
      this.sharedLineMat.dispose();
      this.sharedLineMat = null;
    }
    if (this.selectionMesh) {
      this.group.remove(this.selectionMesh);
      this.selectionMesh.geometry.dispose();
      this.selectionMesh = null;
    }
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      this.group.remove(child);
    }
    this.instanceToMemberMap = [];
    this.memberToInstanceMap.clear();
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
