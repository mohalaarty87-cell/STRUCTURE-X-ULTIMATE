/**
 * STRUCTURE-X ULTIMATE — Analytical Model Generator & Meshing Engine (Phase 16)
 * Generates FEA Analytical Models and discretizes 2D Shells (Slabs & Shear Walls)
 * into conforming finite element meshes with quality diagnostics.
 */

import {
  StructuralModel,
  NodePoint,
  StructuralMember,
  SlabElement,
  WallElement
} from '../../types/structure';

export interface AnalyticalDOFMap {
  nodeId: string;
  dofs: [number, number, number, number, number, number]; // Global equation indices (or -1 if restrained)
}

export interface MeshNode {
  id: string;
  x: number;
  y: number;
  z: number;
  isBoundary: boolean;
  parentEntityId: string;
}

export interface MeshQuadElement {
  id: string;
  entityId: string;
  entityType: 'slab' | 'wall';
  nodeIds: [string, string, string, string];
  thickness: number;
  materialId: string;
  aspectRatio: number;
  jacobianDet: number;
  area: number;
  centroid: { x: number; y: number; z: number };
}

export interface MeshQualityDiagnostics {
  totalMeshNodes: number;
  totalMeshElements: number;
  quadCount: number;
  triCount: number;
  minAspectRatio: number;
  maxAspectRatio: number;
  avgAspectRatio: number;
  minJacobianDet: number;
  elementsWithWarnings: number;
  isValid: boolean;
  warnings: string[];
}

export interface AnalyticalModel {
  totalDOFs: number;
  freeDOFs: number;
  restrainedDOFs: number;
  dofMap: Map<string, AnalyticalDOFMap>;
  nodes: NodePoint[];
  frameElements: StructuralMember[];
  meshNodes: MeshNode[];
  meshElements: MeshQuadElement[];
  meshQuality: MeshQualityDiagnostics;
  diaphragmConstraints: Array<{
    storyId: string;
    type: string;
    masterNodeId: string;
    slaveNodeIds: string[];
  }>;
}

export class AnalyticalModelGenerator {
  /**
   * Generates the Analytical FEA Model from physical structural representation,
   * including 6-DOF equation mapping and boundary condition enforcement.
   */
  public static generateAnalyticalModel(
    model: StructuralModel,
    options?: { targetMeshSize?: number }
  ): AnalyticalModel {
    const dofMap = new Map<string, AnalyticalDOFMap>();
    let currentEqIndex = 0;
    let restrainedCount = 0;

    // 1. Establish 6-DOF map for all structural nodes
    for (const node of model.nodes) {
      const rest = node.isRestrained || {};
      const dofs: [number, number, number, number, number, number] = [-1, -1, -1, -1, -1, -1];
      const restKeys: (keyof typeof rest)[] = ['fx', 'fy', 'fz', 'mx', 'my', 'mz'];

      for (let d = 0; d < 6; d++) {
        const isFixed = Boolean(rest[restKeys[d]]);
        if (isFixed) {
          dofs[d] = -1;
          restrainedCount++;
        } else {
          dofs[d] = currentEqIndex++;
        }
      }

      dofMap.set(node.id, { nodeId: node.id, dofs });
    }

    // 2. Perform 2D shell meshing for slabs and shear walls
    const { meshNodes, meshElements, meshQuality } = this.meshAreaEntities(
      model,
      options?.targetMeshSize || 1.5
    );

    // 3. Formulate diaphragm rigid body master-slave kinematic links
    const diaphragmConstraints: AnalyticalModel['diaphragmConstraints'] = [];
    if (model.diaphragms && model.diaphragms.length > 0) {
      for (const dia of model.diaphragms) {
        diaphragmConstraints.push({
          storyId: dia.story,
          type: dia.type,
          masterNodeId: `MASTER_${dia.id}`,
          slaveNodeIds: dia.nodeIds
        });
      }
    } else {
      // Automatic rigid diaphragm constraint per story
      for (const story of (model.stories || [])) {
        const storyNodes = model.nodes.filter(n => Math.abs(n.y - story.elevation) < 0.05);
        if (storyNodes.length > 0) {
          diaphragmConstraints.push({
            storyId: story.id,
            type: 'rigid',
            masterNodeId: `MASTER_${story.id}`,
            slaveNodeIds: storyNodes.map(n => n.id)
          });
        }
      }
    }

    return {
      totalDOFs: model.nodes.length * 6,
      freeDOFs: currentEqIndex,
      restrainedDOFs: restrainedCount,
      dofMap,
      nodes: [...model.nodes],
      frameElements: [...model.members],
      meshNodes,
      meshElements,
      meshQuality,
      diaphragmConstraints
    };
  }

  /**
   * Discretizes 2D shell panels (Slabs & Shear Walls) into regular quadrilateral finite elements.
   */
  public static meshAreaEntities(
    model: StructuralModel,
    targetMeshSize: number = 1.5
  ): {
    meshNodes: MeshNode[];
    meshElements: MeshQuadElement[];
    meshQuality: MeshQualityDiagnostics;
  } {
    const meshNodes: MeshNode[] = [];
    const meshElements: MeshQuadElement[] = [];
    const nodeLookup = new Map<string, NodePoint>(model.nodes.map(n => [n.id, n]));

    let totalAspect = 0;
    let minAspect = 999.0;
    let maxAspect = 0.0;
    let minJac = 1.0;
    let warningCount = 0;
    const warnings: string[] = [];

    // Mesh Slabs (Horizontal XZ planes)
    for (const slab of (model.slabs || [])) {
      const slabPts = (slab.nodeIds || []).map(id => nodeLookup.get(id)).filter(Boolean) as NodePoint[];
      if (slabPts.length >= 4) {
        const minX = Math.min(...slabPts.map(p => p.x));
        const maxX = Math.max(...slabPts.map(p => p.x));
        const minZ = Math.min(...slabPts.map(p => p.z));
        const maxZ = Math.max(...slabPts.map(p => p.z));
        const elevY = slabPts[0].y;

        const spanX = Math.max(0.1, maxX - minX);
        const spanZ = Math.max(0.1, maxZ - minZ);

        const divX = Math.max(1, Math.round(spanX / targetMeshSize));
        const divZ = Math.max(1, Math.round(spanZ / targetMeshSize));

        const dx = spanX / divX;
        const dz = spanZ / divZ;

        const gridNodeIds: string[][] = [];

        for (let i = 0; i <= divX; i++) {
          gridNodeIds[i] = [];
          for (let j = 0; j <= divZ; j++) {
            const gx = minX + i * dx;
            const gz = minZ + j * dz;
            const nid = `MN_SLAB_${slab.id}_${i}_${j}`;
            meshNodes.push({
              id: nid,
              x: Math.round(gx * 1000) / 1000,
              y: elevY,
              z: Math.round(gz * 1000) / 1000,
              isBoundary: i === 0 || i === divX || j === 0 || j === divZ,
              parentEntityId: slab.id
            });
            gridNodeIds[i][j] = nid;
          }
        }

        // Create Quads
        for (let i = 0; i < divX; i++) {
          for (let j = 0; j < divZ; j++) {
            const aspect = Math.max(dx, dz) / Math.max(Math.min(dx, dz), 1e-4);
            const jac = 1.0; // Regular orthogonal quad has exact normalized Jacobian of 1.0
            const area = dx * dz;

            totalAspect += aspect;
            if (aspect < minAspect) minAspect = aspect;
            if (aspect > maxAspect) maxAspect = aspect;
            if (jac < minJac) minJac = jac;

            if (aspect > 3.0) {
              warningCount++;
              warnings.push(`Slab ${slab.id} Element (${i},${j}) aspect ratio ${aspect.toFixed(2)} exceeds 3.0`);
            }

            meshElements.push({
              id: `ME_SLAB_${slab.id}_${i}_${j}`,
              entityId: slab.id,
              entityType: 'slab',
              nodeIds: [
                gridNodeIds[i][j],
                gridNodeIds[i + 1][j],
                gridNodeIds[i + 1][j + 1],
                gridNodeIds[i][j + 1]
              ],
              thickness: slab.thickness,
              materialId: slab.materialId,
              aspectRatio: Math.round(aspect * 100) / 100,
              jacobianDet: jac,
              area: Math.round(area * 1000) / 1000,
              centroid: {
                x: Math.round((minX + (i + 0.5) * dx) * 1000) / 1000,
                y: elevY,
                z: Math.round((minZ + (j + 0.5) * dz) * 1000) / 1000
              }
            });
          }
        }
      }
    }

    // Mesh Shear Walls (Vertical XY or ZY planes)
    for (const wall of (model.walls || [])) {
      const wallPts = (wall.nodeIds || []).map(id => nodeLookup.get(id)).filter(Boolean) as NodePoint[];
      if (wallPts.length >= 4) {
        const minY = Math.min(...wallPts.map(p => p.y));
        const maxY = Math.max(...wallPts.map(p => p.y));
        const height = Math.max(0.1, maxY - minY);

        const p0 = wallPts[0];
        const p1 = wallPts[1];
        const wallLength = Math.sqrt((p1.x - p0.x) ** 2 + (p1.z - p0.z) ** 2);

        const divL = Math.max(1, Math.round(wallLength / targetMeshSize));
        const divH = Math.max(1, Math.round(height / targetMeshSize));

        const dL = wallLength / divL;
        const dH = height / divH;

        const dirX = (p1.x - p0.x) / (wallLength || 1);
        const dirZ = (p1.z - p0.z) / (wallLength || 1);

        const wallNodeIds: string[][] = [];

        for (let i = 0; i <= divL; i++) {
          wallNodeIds[i] = [];
          for (let j = 0; j <= divH; j++) {
            const wx = p0.x + i * dL * dirX;
            const wy = minY + j * dH;
            const wz = p0.z + i * dL * dirZ;
            const nid = `MN_WALL_${wall.id}_${i}_${j}`;

            meshNodes.push({
              id: nid,
              x: Math.round(wx * 1000) / 1000,
              y: Math.round(wy * 1000) / 1000,
              z: Math.round(wz * 1000) / 1000,
              isBoundary: i === 0 || i === divL || j === 0 || j === divH,
              parentEntityId: wall.id
            });
            wallNodeIds[i][j] = nid;
          }
        }

        // Create Quads for Wall
        for (let i = 0; i < divL; i++) {
          for (let j = 0; j < divH; j++) {
            const aspect = Math.max(dL, dH) / Math.max(Math.min(dL, dH), 1e-4);
            const jac = 1.0;
            const area = dL * dH;

            totalAspect += aspect;
            if (aspect < minAspect) minAspect = aspect;
            if (aspect > maxAspect) maxAspect = aspect;

            meshElements.push({
              id: `ME_WALL_${wall.id}_${i}_${j}`,
              entityId: wall.id,
              entityType: 'wall',
              nodeIds: [
                wallNodeIds[i][j],
                wallNodeIds[i + 1][j],
                wallNodeIds[i + 1][j + 1],
                wallNodeIds[i][j + 1]
              ],
              thickness: wall.thickness,
              materialId: wall.materialId,
              aspectRatio: Math.round(aspect * 100) / 100,
              jacobianDet: jac,
              area: Math.round(area * 1000) / 1000,
              centroid: {
                x: Math.round((p0.x + (i + 0.5) * dL * dirX) * 1000) / 1000,
                y: Math.round((minY + (j + 0.5) * dH) * 1000) / 1000,
                z: Math.round((p0.z + (i + 0.5) * dL * dirZ) * 1000) / 1000
              }
            });
          }
        }
      }
    }

    const totalElems = meshElements.length;
    const avgAspect = totalElems > 0 ? totalAspect / totalElems : 1.0;

    const meshQuality: MeshQualityDiagnostics = {
      totalMeshNodes: meshNodes.length,
      totalMeshElements: totalElems,
      quadCount: totalElems,
      triCount: 0,
      minAspectRatio: minAspect === 999.0 ? 1.0 : Math.round(minAspect * 100) / 100,
      maxAspectRatio: Math.round(maxAspect * 100) / 100,
      avgAspectRatio: Math.round(avgAspect * 100) / 100,
      minJacobianDet: minJac,
      elementsWithWarnings: warningCount,
      isValid: warningCount === 0 || (warningCount / Math.max(totalElems, 1)) < 0.1,
      warnings
    };

    return {
      meshNodes,
      meshElements,
      meshQuality
    };
  }
}
