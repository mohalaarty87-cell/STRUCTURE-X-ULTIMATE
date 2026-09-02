import * as THREE from 'three';
import { StructuralModel } from '../../../types/structure';

export class SupportLayer {
  public group: THREE.Group;

  constructor() {
    this.group = new THREE.Group();
    this.group.name = 'SupportLayer';
  }

  public update(model: StructuralModel, isVisible: boolean = true): void {
    this.clear();
    if (!isVisible) return;

    model.nodes.forEach(node => {
      if (!node.isRestrained) return;
      const { fx, fy, fz, mx, my, mz } = node.isRestrained;
      const isFixed = fx && fy && fz && mx && my && mz;
      const isPinned = fx && fy && fz && !mx && !my && !mz;
      const isRoller = (fx || fz) && fy && !mx && !my && !mz;

      const pos = new THREE.Vector3(node.x, node.y, node.z);

      if (isFixed) {
        // Fixed Foundation Footing (Solid rectangular pedestal + anchor plate)
        const blockGeo = new THREE.BoxGeometry(0.7, 0.35, 0.7);
        const blockMat = new THREE.MeshStandardMaterial({
          color: 0x47a26b,
          roughness: 0.4,
          metalness: 0.3
        });
        const block = new THREE.Mesh(blockGeo, blockMat);
        block.position.set(pos.x, pos.y - 0.175, pos.z);
        this.group.add(block);

        // Fixed Ground Hash Lines (Anchor Hatch)
        const hatchMat = new THREE.LineBasicMaterial({ color: 0x7ed99e });
        const hatchPts = [
          new THREE.Vector3(pos.x - 0.4, pos.y - 0.35, pos.z - 0.4),
          new THREE.Vector3(pos.x + 0.4, pos.y - 0.35, pos.z - 0.4),
          new THREE.Vector3(pos.x - 0.4, pos.y - 0.35, pos.z + 0.4),
          new THREE.Vector3(pos.x + 0.4, pos.y - 0.35, pos.z + 0.4)
        ];
        const hatchGeo = new THREE.BufferGeometry().setFromPoints(hatchPts);
        const hatch = new THREE.LineSegments(hatchGeo, hatchMat);
        this.group.add(hatch);
      } else if (isPinned) {
        // Pinned Support Pyramid
        const coneGeo = new THREE.ConeGeometry(0.35, 0.5, 4);
        const coneMat = new THREE.MeshStandardMaterial({
          color: 0x7ed99e,
          roughness: 0.4,
          metalness: 0.5
        });
        const cone = new THREE.Mesh(coneGeo, coneMat);
        cone.position.set(pos.x, pos.y - 0.25, pos.z);
        cone.rotation.y = Math.PI / 4;
        this.group.add(cone);
      } else if (isRoller) {
        // Roller Support (Cone + Roller Cylinders + Ground Plate)
        const coneGeo = new THREE.ConeGeometry(0.3, 0.35, 4);
        const coneMat = new THREE.MeshStandardMaterial({ color: 0x96ccff, metalness: 0.6 });
        const cone = new THREE.Mesh(coneGeo, coneMat);
        cone.position.set(pos.x, pos.y - 0.175, pos.z);
        cone.rotation.y = Math.PI / 4;
        this.group.add(cone);

        const rollerGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.5, 8);
        const rollerMat = new THREE.MeshStandardMaterial({ color: 0xc1c7d0, metalness: 0.8 });
        const roller = new THREE.Mesh(rollerGeo, rollerMat);
        roller.position.set(pos.x, pos.y - 0.4, pos.z);
        roller.rotation.z = Math.PI / 2;
        this.group.add(roller);
      } else {
        // Generic Support Pyramid
        const coneGeo = new THREE.ConeGeometry(0.35, 0.5, 4);
        const coneMat = new THREE.MeshStandardMaterial({ color: 0x7ed99e });
        const cone = new THREE.Mesh(coneGeo, coneMat);
        cone.position.set(pos.x, pos.y - 0.25, pos.z);
        this.group.add(cone);
      }
    });
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
