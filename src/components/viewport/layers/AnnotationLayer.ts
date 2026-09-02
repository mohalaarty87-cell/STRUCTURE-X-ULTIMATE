import * as THREE from 'three';
import { StructuralModel, NodePoint, AnnotationSettings, DEFAULT_ANNOTATION_SETTINGS } from '../../../types/structure';

export class AnnotationLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'AnnotationLayer';
  }

  public update(
    model: StructuralModel,
    isVisible: boolean = true,
    settings: AnnotationSettings = DEFAULT_ANNOTATION_SETTINGS,
    activeStoryFilter: string = 'all'
  ): void {
    this.clear();
    if (!isVisible) return;

    const nodeMap = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    // 1. Element ID Labels
    if (settings.showElementLabels) {
      model.members.forEach(member => {
        if (activeStoryFilter !== 'all' && member.story !== activeStoryFilter) return;
        const n1 = nodeMap.get(member.startNodeId);
        const n2 = nodeMap.get(member.endNodeId);
        if (!n1 || !n2) return;

        const mid = new THREE.Vector3((n1.x + n2.x) / 2, (n1.y + n2.y) / 2, (n1.z + n2.z) / 2);
        const isCol = member.type === 'column';
        const badgeColor = isCol ? '#7ed99e' : '#96ccff';
        const offset = isCol ? new THREE.Vector3(0.3, 0, 0) : new THREE.Vector3(0, 0.25, 0);

        this.createTextBadge(member.id, mid.clone().add(offset), badgeColor);
      });
    }

    // 2. Node ID Labels
    if (settings.showNodeLabels) {
      model.nodes.forEach(node => {
        this.createTextBadge(node.id, new THREE.Vector3(node.x, node.y + 0.2, node.z), '#e2e2e5', 0.8);
      });
    }

    // 3. Structural Bay Dimensions
    if (settings.showDimensions && model.gridLinesX.length > 1) {
      const zRef = (model.gridLinesY[0]?.coordinate || 0) - 2.5;
      for (let i = 0; i < model.gridLinesX.length - 1; i++) {
        const x1 = model.gridLinesX[i].coordinate;
        const x2 = model.gridLinesX[i + 1].coordinate;
        const span = Math.abs(x2 - x1);

        const p1 = new THREE.Vector3(x1, 0.05, zRef);
        const p2 = new THREE.Vector3(x2, 0.05, zRef);

        // Dimension Line
        const dimGeo = new THREE.BufferGeometry().setFromPoints([p1, p2]);
        const dimMat = new THREE.LineBasicMaterial({ color: 0x8b919a });
        this.group.add(new THREE.Line(dimGeo, dimMat));

        // Dimension Witness Ticks
        const tick1 = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x1, 0.05, zRef - 0.25),
          new THREE.Vector3(x1, 0.05, zRef + 0.25)
        ]);
        const tick2 = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x2, 0.05, zRef - 0.25),
          new THREE.Vector3(x2, 0.05, zRef + 0.25)
        ]);
        this.group.add(new THREE.Line(tick1, dimMat));
        this.group.add(new THREE.Line(tick2, dimMat));

        // Dimension text
        const midX = (x1 + x2) / 2;
        this.createTextBadge(`${span.toFixed(2)} m`, new THREE.Vector3(midX, 0.1, zRef - 0.35), '#c1c7d0', 0.9);
      }
    }

    // 4. Cardinal North Arrow Indicator
    this.createNorthArrow(model);
  }

  private createNorthArrow(model: StructuralModel): void {
    const minX = model.gridLinesX[0]?.coordinate || -8;
    const maxZ = model.gridLinesY[model.gridLinesY.length - 1]?.coordinate || 6;
    const origin = new THREE.Vector3(minX - 3, 0.1, maxZ + 2);

    const dir = new THREE.Vector3(0, 0, -1); // North pointing in -Z direction
    const arrow = new THREE.ArrowHelper(dir, origin, 1.8, 0xef4444, 0.4, 0.25);
    this.group.add(arrow);

    this.createTextBadge('N', new THREE.Vector3(origin.x, origin.y + 0.2, origin.z - 2.2), '#ef4444', 1.0);
  }

  private createTextBadge(text: string, position: THREE.Vector3, color: string, scale: number = 1.0): void {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 48;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, 128, 48);
    ctx.fillStyle = '#1e2022e6';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.roundRect ? ctx.roundRect(2, 4, 124, 40, 4) : ctx.rect(2, 4, 124, 40);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.font = 'bold 20px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 64, 24);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.copy(position);
    sprite.scale.set(1.0 * scale, 0.38 * scale, 1);
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
