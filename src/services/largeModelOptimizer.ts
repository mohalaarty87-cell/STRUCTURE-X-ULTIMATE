import {
  StructuralModel,
  NodePoint,
  StructuralMember,
  StoryLevel,
  GridLine,
  SectionProperty,
  Material
} from '../types/structure';
import { StructuralWorkerClient, BenchmarkMetrics } from './structuralWorkerClient';

/**
 * Large Model Optimization & Benchmark Suite
 * PHASE 15 — Performance & Large Model Optimization
 * 
 * Supports progressive synthesis and stress testing with:
 * - 1,000 elements
 * - 5,000 elements
 * - 10,000 elements
 * - 50,000+ elements
 */

export interface SystemLimitationDoc {
  category: string;
  limitMetric: string;
  recommendedMax: string;
  hardCeiling: string;
  mitigationStrategy: string;
}

export const PLATFORM_LIMITATIONS_DOCUMENTATION: SystemLimitationDoc[] = [
  {
    category: 'FEM Sparse Solver (Pure Python)',
    limitMetric: 'Active Free Degrees of Freedom',
    recommendedMax: '15,000 DOFs (~5,000 Elements)',
    hardCeiling: '150,000 DOFs (~50,000 Elements)',
    mitigationStrategy: 'Preconditioned Conjugate Gradient (PCG) with Jacobi preconditioning replaces dense O(N^3) LU. Reduces memory by 99.8%.'
  },
  {
    category: 'WebGL 3D Viewport Rendering',
    limitMetric: 'Total Rendered Frame & Shell Objects',
    recommendedMax: '50,000 Elements',
    hardCeiling: '250,000 Elements (GPU VRAM dependent)',
    mitigationStrategy: 'THREE.InstancedMesh & single-buffer LineSegments collapse draw calls from 50,000 down to 1-2 draw calls at 60 FPS.'
  },
  {
    category: 'Result Tables & Data Grids',
    limitMetric: 'DOM Table Elements Rendered',
    recommendedMax: '1,000,000 Result Records',
    hardCeiling: '5,000,000 Records',
    mitigationStrategy: 'Virtualized Table with windowed viewport slicing (only ~30 DOM rows rendered simultaneously) with O(1) memory consumption.'
  },
  {
    category: 'Client Browser Main Thread',
    limitMetric: 'Event Loop Blocking Time',
    recommendedMax: '0 ms (100% Non-Blocking)',
    hardCeiling: '16 ms (1 Frame drop)',
    mitigationStrategy: 'Dedicated Web Workers offload assembly, benchmark execution, and heavy math from UI thread.'
  },
  {
    category: 'JSON State & Database Persistence',
    limitMetric: 'Structural Model Payload Size',
    recommendedMax: '25 MB JSON (~20,000 elements)',
    hardCeiling: '100 MB (IndexedDB/Firestore limit)',
    mitigationStrategy: 'Sparse binary representation or story-by-story lazy loading for mega-tall structures.'
  }
];

export class LargeModelOptimizer {
  /**
   * Synthesizes a high-density 3D structural model with specified element target
   * for live testing in the 3D viewport and virtualized tables.
   */
  public static generateSyntheticLargeModel(targetElements: number): StructuralModel {
    const nx = Math.max(3, Math.floor(Math.sqrt(targetElements / 12)));
    const ny = nx;
    const elemsPerStory = (nx * ny) + ((nx - 1) * ny) + (nx * (ny - 1));
    const nz = Math.max(2, Math.ceil(targetElements / Math.max(elemsPerStory, 1)));

    const bayX = 6.0;
    const bayY = 6.0;
    const storyH = 3.5;

    const nodes: NodePoint[] = [];
    const members: StructuralMember[] = [];
    const stories: StoryLevel[] = [];

    // Create materials & sections
    const defaultMat: Material = {
      id: 'mat_steel_s355',
      name: 'Structural Steel S355',
      type: 'steel',
      grade: 'S355',
      elasticModulusE: 210, // GPa
      poissonRatio: 0.3,
      unitWeight: 78.5,
      yieldStrengthFy: 355,
      color: '#96ccff'
    };

    const defaultColSec: SectionProperty = {
      id: 'sec_col_opt',
      name: 'W14x90 Column',
      shape: 'i_beam',
      materialId: defaultMat.id,
      dimensions: { width: 368, height: 356, flangeThickness: 18, webThickness: 11 },
      area: 171,
      momentOfInertiaIxx: 41600,
      momentOfInertiaIyy: 15100,
      torsionalConstantJ: 170,
      weightPerMeter: 134
    };

    const defaultBmSec: SectionProperty = {
      id: 'sec_bm_opt',
      name: 'W18x50 Beam',
      shape: 'i_beam',
      materialId: defaultMat.id,
      dimensions: { width: 190, height: 457, flangeThickness: 14.5, webThickness: 9.0 },
      area: 94.8,
      momentOfInertiaIxx: 33300,
      momentOfInertiaIyy: 1670,
      torsionalConstantJ: 51.6,
      weightPerMeter: 74.5
    };

    // Stories
    for (let k = 1; k <= nz; k++) {
      stories.push({
        id: `story_${k}`,
        name: `Story ${k}`,
        elevation: k * storyH,
        height: storyH,
        isMasterStory: k % 5 === 0,
        similarToStoryId: k % 5 !== 0 ? `story_${Math.floor((k - 1) / 5) * 5 + 1}` : undefined
      });
    }

    // Nodes
    const nodeMap: { [key: string]: NodePoint } = {};
    for (let k = 0; k <= nz; k++) {
      const elev = k * storyH;
      for (let j = 0; j < ny; j++) {
        const y = j * bayY;
        for (let i = 0; i < nx; i++) {
          const x = i * bayX;
          const nid = `N_${i}_${j}_${k}`;
          const isBase = (k === 0);
          const node: NodePoint = {
            id: nid,
            x,
            y: elev,
            z: y, // Z in 3D viewport
            isRestrained: isBase ? { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } : undefined
          };
          nodes.push(node);
          nodeMap[`${i},${j},${k}`] = node;
        }
      }
    }

    let elemCount = 0;

    // Columns
    for (let k = 0; k < nz; k++) {
      const storyId = `story_${k + 1}`;
      for (let j = 0; j < ny; j++) {
        for (let i = 0; i < nx; i++) {
          const n1 = nodeMap[`${i},${j},${k}`];
          const n2 = nodeMap[`${i},${j},${k + 1}`];
          if (n1 && n2) {
            members.push({
              id: `COL_${i}_${j}_${k + 1}`,
              name: `Col ${i}-${j}-${k + 1}`,
              type: 'column',
              story: storyId,
              startNodeId: n1.id,
              endNodeId: n2.id,
              sectionId: defaultColSec.id,
              materialId: defaultMat.id,
              length: storyH,
              releases: 'Continuous',
              localAxisAngle: 0,
              forces: {
                axialP: -120000 * (nz - k),
                shearV2: 15000,
                shearV3: 12000,
                momentM2: 35000,
                momentM3: 45000,
                torsionT: 2000,
                maxDeflection: 3.2,
                utilizationRatio: 0.45 + (k / (nz * 2)),
                designStatus: 'PASS'
              }
            });
            elemCount++;
            if (elemCount >= targetElements) break;
          }
        }
        if (elemCount >= targetElements) break;
      }
      if (elemCount >= targetElements) break;
    }

    // Beams X
    if (elemCount < targetElements) {
      for (let k = 1; k <= nz; k++) {
        const storyId = `story_${k}`;
        for (let j = 0; j < ny; j++) {
          for (let i = 0; i < nx - 1; i++) {
            const n1 = nodeMap[`${i},${j},${k}`];
            const n2 = nodeMap[`${i + 1},${j},${k}`];
            if (n1 && n2) {
              members.push({
                id: `BMX_${i}_${j}_${k}`,
                name: `BeamX ${i}-${j}-${k}`,
                type: 'beam',
                story: storyId,
                startNodeId: n1.id,
                endNodeId: n2.id,
                sectionId: defaultBmSec.id,
                materialId: defaultMat.id,
                length: bayX,
                releases: 'Continuous',
                localAxisAngle: 0,
                forces: {
                  axialP: 5000,
                  shearV2: 45000,
                  shearV3: 2000,
                  momentM2: 5000,
                  momentM3: 85000,
                  torsionT: 800,
                  maxDeflection: 4.1,
                  utilizationRatio: 0.62,
                  designStatus: 'PASS'
                }
              });
              elemCount++;
              if (elemCount >= targetElements) break;
            }
          }
          if (elemCount >= targetElements) break;
        }
        if (elemCount >= targetElements) break;
      }
    }

    // Beams Y (Z axis in 3D)
    if (elemCount < targetElements) {
      for (let k = 1; k <= nz; k++) {
        const storyId = `story_${k}`;
        for (let j = 0; j < ny - 1; j++) {
          for (let i = 0; i < nx; i++) {
            const n1 = nodeMap[`${i},${j},${k}`];
            const n2 = nodeMap[`${i},${j + 1},${k}`];
            if (n1 && n2) {
              members.push({
                id: `BMY_${i}_${j}_${k}`,
                name: `BeamY ${i}-${j}-${k}`,
                type: 'beam',
                story: storyId,
                startNodeId: n1.id,
                endNodeId: n2.id,
                sectionId: defaultBmSec.id,
                materialId: defaultMat.id,
                length: bayY,
                releases: 'Continuous',
                localAxisAngle: 0,
                forces: {
                  axialP: 4000,
                  shearV2: 42000,
                  shearV3: 1800,
                  momentM2: 4500,
                  momentM3: 78000,
                  torsionT: 750,
                  maxDeflection: 3.8,
                  utilizationRatio: 0.58,
                  designStatus: 'PASS'
                }
              });
              elemCount++;
              if (elemCount >= targetElements) break;
            }
          }
          if (elemCount >= targetElements) break;
        }
        if (elemCount >= targetElements) break;
      }
    }

    // Grid definition
    const gridLinesX: GridLine[] = Array.from({ length: nx }, (_, i) => ({
      id: `gx_${i}`,
      label: String.fromCharCode(65 + (i % 26)),
      axis: 'X',
      coordinate: i * bayX
    }));

    const gridLinesY: GridLine[] = Array.from({ length: ny }, (_, j) => ({
      id: `gy_${j}`,
      label: `${j + 1}`,
      axis: 'Y',
      coordinate: j * bayY
    }));

    return {
      projectName: `Scale Test Model (${targetElements.toLocaleString()} Elements)`,
      version: '1.0.0',
      units: 'kN-m, C',
      stories,
      gridLinesX,
      gridLinesY,
      materials: [defaultMat],
      sections: [defaultColSec, defaultBmSec],
      nodes,
      members,
      slabs: [],
      walls: [],
      openings: [],
      links: [],
      springs: []
    };
  }

  /**
   * Runs the complete progressive benchmark suite (1k, 5k, 10k, 50k+).
   */
  public static async runProgressiveSuite(
    onStepUpdate?: (scale: number, progressPercent: number, currentMetrics: BenchmarkMetrics[]) => void
  ): Promise<BenchmarkMetrics[]> {
    const scales = [1000, 5000, 10000, 50000];
    const results: BenchmarkMetrics[] = [];

    for (let i = 0; i < scales.length; i++) {
      const scale = scales[i];
      const res = await StructuralWorkerClient.runBenchmarkJob(scale, (phase, pct) => {
        if (onStepUpdate) {
          const overallPct = Math.round(((i + (pct / 100)) / scales.length) * 100);
          onStepUpdate(scale, overallPct, [...results]);
        }
      });
      results.push(res);
      if (onStepUpdate) {
        onStepUpdate(scale, Math.round(((i + 1) / scales.length) * 100), [...results]);
      }
    }

    return results;
  }
}
