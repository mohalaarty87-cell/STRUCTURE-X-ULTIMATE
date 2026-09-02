import * as THREE from 'three';
import { StructuralModel, NodePoint } from '../../../types/structure';

export class LoadLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'LoadLayer';
  }

  public update(model: StructuralModel, isVisible: boolean = true, activeStoryFilter: string = 'all'): void {
    this.clear();
    if (!isVisible) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    // 1. Nodal Concentrated Loads
    model.nodes.forEach(node => {
      if (node.loads) {
        const { fx, fy, fz } = node.loads;

        // Vertical Point Load (FY)
        if (fy && Math.abs(fy) > 0.01) {
          const dir = new THREE.Vector3(0, fy > 0 ? 1 : -1, 0);
          const len = 1.4;
          const origin = new THREE.Vector3(node.x, fy > 0 ? node.y : node.y + len, node.z);
          const arrow = new THREE.ArrowHelper(dir, origin, len, 0xff4d4d, 0.35, 0.2);
          this.group.add(arrow);

          this.createLoadTextBadge(`${Math.abs(fy)} kN`, new THREE.Vector3(node.x, node.y + 1.6, node.z), 0xff4d4d);
        }

        // Lateral Force X (Wind / Seismic)
        if (fx && Math.abs(fx) > 0.01) {
          const dir = new THREE.Vector3(fx > 0 ? 1 : -1, 0, 0);
          const len = 1.2;
          const origin = new THREE.Vector3(fx > 0 ? node.x - len : node.x, node.y, node.z);
          const arrow = new THREE.ArrowHelper(dir, origin, len, 0xffad68, 0.3, 0.18);
          this.group.add(arrow);

          this.createLoadTextBadge(`Fx: ${fx} kN`, new THREE.Vector3(node.x - 0.8, node.y + 0.3, node.z), 0xffad68);
        }
      }
    });

    // 2. Distributed Line Loads on Beams
    model.members.forEach(member => {
      if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
      if (member.type === 'beam' && member.distributedLoad && member.distributedLoad > 0) {
        const n1 = nodeMap.get(member.startNodeId);
        const n2 = nodeMap.get(member.endNodeId);
        if (!n1 || !n2) return;

        const p1 = new THREE.Vector3(n1.x, n1.y, n1.z);
        const p2 = new THREE.Vector3(n2.x, n2.y, n2.z);
        const count = 5;

        for (let i = 0; i <= count; i++) {
          const t = i / count;
          const pt = p1.clone().lerp(p2, t);
          const origin = new THREE.Vector3(pt.x, pt.y + 0.8, pt.z);
          const dir = new THREE.Vector3(0, -1, 0);
          const arrow = new THREE.ArrowHelper(dir, origin, 0.8, 0xffb77d, 0.2, 0.12);
          this.group.add(arrow);
        }

        // Top load line connecting arrows
        const topP1 = new THREE.Vector3(p1.x, p1.y + 0.8, p1.z);
        const topP2 = new THREE.Vector3(p2.x, p2.y + 0.8, p2.z);
        const lineGeo = new THREE.BufferGeometry().setFromPoints([topP1, topP2]);
        const lineMat = new THREE.LineBasicMaterial({ color: 0xffb77d, linewidth: 2 });
        const topBar = new THREE.Line(lineGeo, lineMat);
        this.group.add(topBar);

        // Value text
        const mid = p1.clone().add(p2).multiplyScalar(0.5);
        this.createLoadTextBadge(`${member.distributedLoad} kN/m`, new THREE.Vector3(mid.x, mid.y + 1.05, mid.z), 0xffb77d);
      }
    });
  }

  private createLoadTextBadge(text: string, position: THREE.Vector3, color: number): void {
    const canvas = document.createElement('canvas');
    canvas.width = 160;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, 160, 48);
    ctx.fillStyle = '#1e2022';
    ctx.strokeStyle = `#${color.toString(16).padStart(6, '0')}`;
    ctx.lineWidth = 2;
    ctx.roundRect ? ctx.roundRect(2, 4, 156, 40, 4) : ctx.rect(2, 4, 156, 40);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
    ctx.font = 'bold 18px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 80, 24);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.copy(position);
    sprite.scale.set(1.4, 0.45, 1);
    this.group.add(sprite);
  }

  public clear(): void {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child instanceof THREE.Mesh || child instanceof THREE.Line || child instanceof THREE.ArrowHelper) {
        if ('geometry' in child && child.geometry) (child.geometry as THREE.BufferGeometry).dispose();
      }
      this.group.remove(child);
    }
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
