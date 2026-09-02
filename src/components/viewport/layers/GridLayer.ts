import * as THREE from 'three';
import { StructuralModel } from '../../../types/structure';

export class GridLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'GridLayer';
  }

  public update(model: StructuralModel, isVisible: boolean = true): void {
    this.clear();
    if (!isVisible) return;

    // 1. Base Grid Plane Helper
    const baseGrid = new THREE.GridHelper(30, 30, 0x5b96c9, 0x282a2c);
    baseGrid.position.y = 0;
    this.group.add(baseGrid);

    // 2. Structural Grid Lines (X and Y axis lines)
    const lineMatX = new THREE.LineDashedMaterial({
      color: 0x96ccff,
      dashSize: 0.5,
      gapSize: 0.25,
      linewidth: 1,
      transparent: true,
      opacity: 0.65
    });

    const lineMatY = new THREE.LineDashedMaterial({
      color: 0x7ed99e,
      dashSize: 0.5,
      gapSize: 0.25,
      linewidth: 1,
      transparent: true,
      opacity: 0.65
    });

    const minX = model.gridLinesX.length > 0 ? Math.min(...model.gridLinesX.map(g => g.coordinate)) - 3 : -10;
    const maxX = model.gridLinesX.length > 0 ? Math.max(...model.gridLinesX.map(g => g.coordinate)) + 3 : 10;
    const minY = model.gridLinesY.length > 0 ? Math.min(...model.gridLinesY.map(g => g.coordinate)) - 3 : -10;
    const maxY = model.gridLinesY.length > 0 ? Math.max(...model.gridLinesY.map(g => g.coordinate)) + 3 : 10;

    // Draw Grid Lines X (running along Z axis)
    model.gridLinesX.forEach(gx => {
      const pts = [
        new THREE.Vector3(gx.coordinate, 0.02, minY),
        new THREE.Vector3(gx.coordinate, 0.02, maxY)
      ];
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, lineMatX);
      line.computeLineDistances();
      this.group.add(line);

      // Grid Bubbles at ends
      this.createGridBubble(gx.label, new THREE.Vector3(gx.coordinate, 0.05, maxY + 0.8), 0x96ccff);
      this.createGridBubble(gx.label, new THREE.Vector3(gx.coordinate, 0.05, minY - 0.8), 0x96ccff);
    });

    // Draw Grid Lines Y (running along X axis)
    model.gridLinesY.forEach(gy => {
      const pts = [
        new THREE.Vector3(minX, 0.02, gy.coordinate),
        new THREE.Vector3(maxX, 0.02, gy.coordinate)
      ];
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, lineMatY);
      line.computeLineDistances();
      this.group.add(line);

      // Grid Bubbles at ends
      this.createGridBubble(gy.label, new THREE.Vector3(maxX + 0.8, 0.05, gy.coordinate), 0x7ed99e);
      this.createGridBubble(gy.label, new THREE.Vector3(minX - 0.8, 0.05, gy.coordinate), 0x7ed99e);
    });
  }

  private createGridBubble(text: string, position: THREE.Vector3, color: number): void {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw Circle Bubble
    ctx.clearRect(0, 0, 64, 64);
    ctx.fillStyle = '#1e2022';
    ctx.beginPath();
    ctx.arc(32, 32, 28, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = `#${color.toString(16).padStart(6, '0')}`;
    ctx.lineWidth = 4;
    ctx.stroke();

    // Draw Text Label
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 28px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 32, 33);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.copy(position);
    sprite.scale.set(1.2, 1.2, 1);
    this.group.add(sprite);
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
