import * as THREE from 'three';
import { StructuralModel, NodePoint, DisplayMode } from '../../../types/structure';

export class ResultLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'ResultLayer';
  }

  public update(
    model: StructuralModel,
    isVisible: boolean = true,
    displayMode: DisplayMode = 'extruded',
    activeStoryFilter: string = 'all'
  ): void {
    this.clear();
    if (!isVisible) return;

    // Only render if a result diagram mode is active
    if (!['deformed', 'bmd', 'sfd', 'axial', 'stress'].includes(displayMode)) {
      return;
    }

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    if (displayMode === 'deformed') {
      this.renderDeformedShape(model, nodeMap, activeStoryFilter);
    } else if (displayMode === 'bmd') {
      this.renderBendingMomentDiagram(model, nodeMap, activeStoryFilter);
    } else if (displayMode === 'sfd') {
      this.renderShearForceDiagram(model, nodeMap, activeStoryFilter);
    } else if (displayMode === 'axial') {
      this.renderAxialDiagram(model, nodeMap, activeStoryFilter);
    }
  }

  private renderDeformedShape(model: StructuralModel, nodeMap: Map<string, NodePoint>, activeStoryFilter: string): void {
    const scale = 150.0; // Scaled displacement amplification for visual clarity
    const lineMat = new THREE.LineDashedMaterial({
      color: 0xff7070,
      dashSize: 0.3,
      gapSize: 0.15,
      linewidth: 2
    });

    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
      const n1 = nodeMap.get(member.startNodeId);
      const n2 = nodeMap.get(member.endNodeId);
      if (!n1 || !n2) return;

      const def1 = ((n1.loads?.fx || 0) * 0.0005) * scale;
      const def2 = ((n2.loads?.fx || 0) * 0.0005) * scale;
      const vertDef = member.forces ? -(member.forces.maxDeflection / 1000) * (scale * 0.3) : 0;

      const p1 = new THREE.Vector3(n1.x + def1, n1.y, n1.z);
      const mid = new THREE.Vector3((n1.x + n2.x) / 2 + (def1 + def2) / 2, (n1.y + n2.y) / 2 + vertDef, (n1.z + n2.z) / 2);
      const p2 = new THREE.Vector3(n2.x + def2, n2.y, n2.z);

      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      const pts = curve.getPoints(12);
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, lineMat);
      line.computeLineDistances();
      this.group.add(line);
    });
  }

  private renderBendingMomentDiagram(model: StructuralModel, nodeMap: Map<string, NodePoint>, activeStoryFilter: string): void {
    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
      if (!member.forces) return;

      const n1 = nodeMap.get(member.startNodeId);
      const n2 = nodeMap.get(member.endNodeId);
      if (!n1 || !n2) return;

      const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
      const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
      const moment = member.forces.momentM3;
      const mScale = 0.012; // diagram height scale

      // Parabolic ribbon for beams, linear for columns
      const normal = member.type === 'beam' ? new THREE.Vector3(0, -1, 0) : new THREE.Vector3(1, 0, 0);
      const ptsCount = 10;
      const vertices: number[] = [];
      const colors: number[] = [];

      for (let i = 0; i < ptsCount; i++) {
        const t1 = i / ptsCount;
        const t2 = (i + 1) / ptsCount;

        const base1 = p1.clone().lerp(p2, t1);
        const base2 = p1.clone().lerp(p2, t2);

        // Parabola factor 4*t*(1-t)
        const h1 = moment * 4 * t1 * (1 - t1) * mScale;
        const h2 = moment * 4 * t2 * (1 - t2) * mScale;

        const off1 = base1.clone().add(normal.clone().multiplyScalar(h1));
        const off2 = base2.clone().add(normal.clone().multiplyScalar(h2));

        // Two triangles forming ribbon quad
        vertices.push(
          base1.x, base1.y, base1.z,
          off1.x, off1.y, off1.z,
          off2.x, off2.y, off2.z,

          base1.x, base1.y, base1.z,
          off2.x, off2.y, off2.z,
          base2.x, base2.y, base2.z
        );

        // Color gradient based on moment sign (Cyan / Blue)
        const r = 0.2, g = 0.6, b = 1.0;
        for (let k = 0; k < 6; k++) colors.push(r, g, b);
      }

      const ribbonGeo = new THREE.BufferGeometry();
      ribbonGeo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      ribbonGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

      const ribbonMat = new THREE.MeshBasicMaterial({
        vertexColors: true,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.75
      });
      const mesh = new THREE.Mesh(ribbonGeo, ribbonMat);
      this.group.add(mesh);
    });
  }

  private renderShearForceDiagram(model: StructuralModel, nodeMap: Map<string, NodePoint>, activeStoryFilter: string): void {
    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
      if (!member.forces) return;

      const n1 = nodeMap.get(member.startNodeId);
      const n2 = nodeMap.get(member.endNodeId);
      if (!n1 || !n2) return;

      const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
      const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
      const shear = member.forces.shearV2;
      const sScale = 0.01;

      const normal = member.type === 'beam' ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
      const mid = p1.clone().lerp(p2, 0.5);

      const topP1 = p1.clone().add(normal.clone().multiplyScalar(shear * sScale));
      const topP2 = p2.clone().add(normal.clone().multiplyScalar(-shear * sScale));

      const vertices = [
        p1.x, p1.y, p1.z,  topP1.x, topP1.y, topP1.z,  mid.x, mid.y, mid.z,
        mid.x, mid.y, mid.z,  topP2.x, topP2.y, topP2.z,  p2.x, p2.y, p2.z
      ];

      const sfdGeo = new THREE.BufferGeometry();
      sfdGeo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      const sfdMat = new THREE.MeshBasicMaterial({
        color: 0x7ed99e,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.7
      });
      this.group.add(new THREE.Mesh(sfdGeo, sfdMat));
    });
  }

  private renderAxialDiagram(model: StructuralModel, nodeMap: Map<string, NodePoint>, activeStoryFilter: string): void {
    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
      if (!member.forces) return;

      const n1 = nodeMap.get(member.startNodeId);
      const n2 = nodeMap.get(member.endNodeId);
      if (!n1 || !n2) return;

      const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
      const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
      const axial = member.forces.axialP;
      const isCompression = axial < 0;
      const aScale = Math.min(0.35, Math.abs(axial) * 0.0003);

      const normal = member.type === 'column' ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
      const off1 = p1.clone().add(normal.clone().multiplyScalar(aScale));
      const off2 = p2.clone().add(normal.clone().multiplyScalar(aScale));

      const vertices = [
        p1.x, p1.y, p1.z,  off1.x, off1.y, off1.z,  off2.x, off2.y, off2.z,
        p1.x, p1.y, p1.z,  off2.x, off2.y, off2.z,  p2.x, p2.y, p2.z
      ];

      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      const mat = new THREE.MeshBasicMaterial({
        color: isCompression ? 0x3b82f6 : 0xef4444, // Compression blue, tension red
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.65
      });
      this.group.add(new THREE.Mesh(geo, mat));
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
