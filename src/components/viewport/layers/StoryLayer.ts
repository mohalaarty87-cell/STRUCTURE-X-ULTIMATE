import * as THREE from 'three';
import { StructuralModel } from '../../../types/structure';

export class StoryLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'StoryLayer';
  }

  public update(model: StructuralModel, isVisible: boolean = true, activeStoryFilter: string = 'all'): void {
    this.clear();
    if (!isVisible) return;

    const minX = model.gridLinesX.length > 0 ? Math.min(...model.gridLinesX.map(g => g.coordinate)) - 1 : -8;
    const maxX = model.gridLinesX.length > 0 ? Math.max(...model.gridLinesX.map(g => g.coordinate)) + 1 : 8;
    const minZ = model.gridLinesY.length > 0 ? Math.min(...model.gridLinesY.map(g => g.coordinate)) - 1 : -6;
    const maxZ = model.gridLinesY.length > 0 ? Math.max(...model.gridLinesY.map(g => g.coordinate)) + 1 : 6;

    const width = maxX - minX;
    const depth = maxZ - minZ;
    const centerX = (minX + maxX) / 2;
    const centerZ = (minZ + maxZ) / 2;

    model.stories.forEach(story => {
      if (activeStoryFilter !== 'all' && story.name !== activeStoryFilter) return;

      const isBase = story.elevation === 0;

      // 1. Horizontal Plane Wireframe Bounds
      const planeGeo = new THREE.PlaneGeometry(width, depth);
      const planeMat = new THREE.MeshBasicMaterial({
        color: isBase ? 0x41474f : 0x5b96c9,
        transparent: true,
        opacity: 0.04,
        side: THREE.DoubleSide
      });

      const planeMesh = new THREE.Mesh(planeGeo, planeMat);
      planeMesh.position.set(centerX, story.elevation, centerZ);
      planeMesh.rotation.x = Math.PI / 2;
      this.group.add(planeMesh);

      // Edge outline
      const edgeGeo = new THREE.EdgesGeometry(planeGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: isBase ? 0x555555 : 0x5b96c9,
        transparent: true,
        opacity: 0.35
      });
      const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
      edgeLines.position.set(centerX, story.elevation, centerZ);
      edgeLines.rotation.x = Math.PI / 2;
      this.group.add(edgeLines);

      // 2. Story Elevation Datum Marker & Sprite Badge
      this.createStoryDatumBadge(
        `${story.name} (+${story.elevation.toFixed(1)}m)`,
        new THREE.Vector3(maxX + 1.2, story.elevation, centerZ)
      );
    });
  }

  private createStoryDatumBadge(text: string, position: THREE.Vector3): void {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, 256, 64);
    ctx.fillStyle = '#1e2022';
    ctx.strokeStyle = '#96ccff';
    ctx.lineWidth = 2;
    ctx.roundRect ? ctx.roundRect(4, 8, 248, 48, 6) : ctx.rect(4, 8, 248, 48);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#96ccff';
    ctx.font = 'bold 20px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.copy(position);
    sprite.scale.set(3.2, 0.8, 1);
    this.group.add(sprite);
  }

  public clear(): void {
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      if (child instanceof THREE.Mesh || child instanceof THREE.LineSegments) {
        if (child.geometry) child.geometry.dispose();
      }
      this.group.remove(child);
    }
  }

  public setVisible(visible: boolean): void {
    this.group.visible = visible;
  }
}
