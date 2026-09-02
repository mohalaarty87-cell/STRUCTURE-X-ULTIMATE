import { StructuralModel, ProjectMetadata } from '../../types/domain';
import { ModelIntegrityValidator } from '../../core/validation/ModelIntegrityValidator';
import { EngineeringError } from '../../core/errors/EngineeringError';
import { logger } from '../../core/logging/Logger';

export interface ProjectSummary {
  id: string;
  name: string;
  code: string;
  engineer: string;
  client: string;
  lastModified: string;
  nodeCount: number;
  memberCount: number;
  slabCount: number;
  units: string;
  designCode: string;
  hasAnalysisResults: boolean;
}

export class ProjectRepository {
  private static instance: ProjectRepository;
  private projects: Map<string, StructuralModel> = new Map();

  private constructor() {
    this.seedDefaultProjects();
  }

  public static getInstance(): ProjectRepository {
    if (!ProjectRepository.instance) {
      ProjectRepository.instance = new ProjectRepository();
    }
    return ProjectRepository.instance;
  }

  public listProjects(): ProjectSummary[] {
    const list: ProjectSummary[] = [];
    this.projects.forEach(model => {
      list.push({
        id: model.metadata.id,
        name: model.projectName,
        code: model.metadata.code,
        engineer: model.metadata.engineer,
        client: model.metadata.client,
        lastModified: model.metadata.lastModified,
        nodeCount: model.nodes.length,
        memberCount: model.members.length,
        slabCount: model.slabs.length,
        units: model.units,
        designCode: model.metadata.designCode,
        hasAnalysisResults: !!model.analysisSummary
      });
    });
    return list;
  }

  public getProject(id: string): StructuralModel {
    const project = this.projects.get(id);
    if (!project) {
      throw new EngineeringError('E6001', { objectId: id });
    }
    return JSON.parse(JSON.stringify(project));
  }

  public saveProject(model: StructuralModel): StructuralModel {
    const validation = ModelIntegrityValidator.validate(model);
    if (!validation.isValid) {
      logger.warn('ProjectRepository', `Saving project "${model.projectName}" with ${validation.totalErrors} validation errors`);
    }

    model.metadata.lastModified = new Date().toISOString();
    model.metadata.revision = (model.metadata.revision || 0) + 1;

    this.projects.set(model.metadata.id, JSON.parse(JSON.stringify(model)));
    logger.info('ProjectRepository', `Saved project "${model.projectName}" (ID: ${model.metadata.id}, Rev: ${model.metadata.revision})`);
    return model;
  }

  public createProject(metadataPartial: Partial<ProjectMetadata>, initialModel?: Partial<StructuralModel>): StructuralModel {
    const id = `PRJ-${Date.now()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    const now = new Date().toISOString();

    const metadata: ProjectMetadata = {
      id,
      name: metadataPartial.name || 'New Structural Project',
      code: metadataPartial.code || 'STR-001',
      engineer: metadataPartial.engineer || 'Lead Structural Engineer',
      client: metadataPartial.client || 'Structural Client Corp',
      dateCreated: now,
      lastModified: now,
      revision: 1,
      description: metadataPartial.description || '3D Building structural analysis & design model',
      units: metadataPartial.units || 'kN-m, C',
      designCode: metadataPartial.designCode || 'EUROCODE',
      schemaVersion: '4.2.0'
    };

    const newModel: StructuralModel = {
      projectName: metadata.name,
      version: '4.2.0',
      units: metadata.units,
      metadata,
      stories: initialModel?.stories || [
        { id: 'ST-00', name: 'Base', elevationZ: 0, height: 0, isMasterStory: false },
        { id: 'ST-01', name: 'Story 1', elevationZ: 3.5, height: 3.5, isMasterStory: true, color: '#3b82f6' }
      ],
      gridSystem: initialModel?.gridSystem || {
        id: 'GRID-1',
        name: 'Cartesian Grid System',
        originX: 0,
        originY: 0,
        rotationAngleDeg: 0,
        xGrids: [
          { id: 'GX-1', label: '1', coordinate: 0, visible: true },
          { id: 'GX-2', label: '2', coordinate: 6.0, visible: true }
        ],
        yGrids: [
          { id: 'GY-A', label: 'A', coordinate: 0, visible: true },
          { id: 'GY-B', label: 'B', coordinate: 6.0, visible: true }
        ]
      },
      materials: initialModel?.materials || [
        {
          id: 'MAT-C30',
          name: 'Concrete C30/37',
          grade: 'C30/37',
          type: 'concrete',
          elasticModulusE: 33.0, // GPa
          poissonRatio: 0.2,
          unitWeight: 25.0, // kN/m3
          compressiveStrengthFc: 30.0,
          color: '#94a3b8'
        },
        {
          id: 'MAT-S355',
          name: 'Structural Steel S355',
          grade: 'S355',
          type: 'steel',
          elasticModulusE: 210.0, // GPa
          poissonRatio: 0.3,
          unitWeight: 78.5,
          yieldStrengthFy: 355.0,
          ultimateStrengthFu: 510.0,
          color: '#38bdf8'
        }
      ],
      sections: initialModel?.sections || [
        {
          id: 'SEC-COL-400',
          name: 'Col 400x400 RC',
          shape: 'rectangular',
          materialId: 'MAT-C30',
          dimensions: { width: 400, height: 400 },
          area: 1600, // cm2
          momentOfInertiaIxx: 213333.3, // cm4
          momentOfInertiaIyy: 213333.3,
          torsionalConstantJ: 360000.0,
          weightPerMeter: 400.0
        },
        {
          id: 'SEC-BM-300x600',
          name: 'Beam 300x600 RC',
          shape: 'rectangular',
          materialId: 'MAT-C30',
          dimensions: { width: 300, height: 600 },
          area: 1800,
          momentOfInertiaIxx: 540000.0,
          momentOfInertiaIyy: 135000.0,
          torsionalConstantJ: 350000.0,
          weightPerMeter: 450.0
        }
      ],
      nodes: initialModel?.nodes || [],
      members: initialModel?.members || [],
      slabs: initialModel?.slabs || [],
      loadPatterns: initialModel?.loadPatterns || [
        { id: 'LP-DL', name: 'Dead Load (Self-Weight)', type: 'DEAD', selfWeightMultiplier: 1.0 },
        { id: 'LP-LL', name: 'Live Load (Occupancy)', type: 'LIVE', selfWeightMultiplier: 0.0 }
      ],
      loadCombinations: initialModel?.loadCombinations || [
        {
          id: 'LC-ULS-1',
          name: '1.35 DL + 1.50 LL (Eurocode ULS)',
          type: 'LINEAR_ADD',
          factors: [
            { loadPatternId: 'LP-DL', factor: 1.35 },
            { loadPatternId: 'LP-LL', factor: 1.50 }
          ],
          designType: 'STRENGTH'
        },
        {
          id: 'LC-SLS-1',
          name: '1.00 DL + 1.00 LL (Eurocode SLS)',
          type: 'LINEAR_ADD',
          factors: [
            { loadPatternId: 'LP-DL', factor: 1.0 },
            { loadPatternId: 'LP-LL', factor: 1.0 }
          ],
          designType: 'SERVICEABILITY'
        }
      ]
    };

    this.projects.set(id, newModel);
    logger.info('ProjectRepository', `Created new project "${metadata.name}" with ID: ${id}`);
    return newModel;
  }

  public deleteProject(id: string): boolean {
    if (!this.projects.has(id)) {
      throw new EngineeringError('E6001', { objectId: id });
    }
    const res = this.projects.delete(id);
    logger.info('ProjectRepository', `Deleted project with ID: ${id}`);
    return res;
  }

  private seedDefaultProjects(): void {
    // Seed 2-Story RC Building Benchmark Model
    const benchmarkModel: StructuralModel = {
      projectName: '2-Story RC Building (Benchmark)',
      version: '4.2.0',
      units: 'kN-m, C',
      metadata: {
        id: 'PRJ-BENCHMARK-01',
        name: '2-Story RC Building (Benchmark)',
        code: 'RC-BLDG-2S',
        engineer: 'Structural-X Lead Systems',
        client: 'Standard Benchmark Suite',
        dateCreated: new Date().toISOString(),
        lastModified: new Date().toISOString(),
        revision: 1,
        description: '2-Story Reinforced Concrete 3D Frame Benchmark with rigid floor diaphragms',
        units: 'kN-m, C',
        designCode: 'EUROCODE',
        schemaVersion: '4.2.0'
      },
      stories: [
        { id: 'ST-00', name: 'Base', elevationZ: 0, height: 0, isMasterStory: false },
        { id: 'ST-01', name: 'Level 1', elevationZ: 3.5, height: 3.5, isMasterStory: true, color: '#3b82f6' },
        { id: 'ST-02', name: 'Roof', elevationZ: 7.0, height: 3.5, isMasterStory: false, color: '#6366f1' }
      ],
      gridSystem: {
        id: 'GRID-1',
        name: 'Structural Grid',
        originX: 0,
        originY: 0,
        rotationAngleDeg: 0,
        xGrids: [
          { id: 'GX-1', label: '1', coordinate: 0, visible: true },
          { id: 'GX-2', label: '2', coordinate: 6.0, visible: true }
        ],
        yGrids: [
          { id: 'GY-A', label: 'A', coordinate: 0, visible: true },
          { id: 'GY-B', label: 'B', coordinate: 6.0, visible: true }
        ]
      },
      materials: [
        {
          id: 'MAT-C30',
          name: 'Concrete C30/37',
          grade: 'C30/37',
          type: 'concrete',
          elasticModulusE: 33.0,
          poissonRatio: 0.2,
          unitWeight: 25.0,
          compressiveStrengthFc: 30.0,
          color: '#94a3b8'
        }
      ],
      sections: [
        {
          id: 'SEC-COL-400',
          name: 'C400x400 RC Column',
          shape: 'rectangular',
          materialId: 'MAT-C30',
          dimensions: { width: 400, height: 400 },
          area: 1600,
          momentOfInertiaIxx: 213333.3,
          momentOfInertiaIyy: 213333.3,
          torsionalConstantJ: 360000.0,
          weightPerMeter: 400.0
        },
        {
          id: 'SEC-BM-300x600',
          name: 'B300x600 RC Beam',
          shape: 'rectangular',
          materialId: 'MAT-C30',
          dimensions: { width: 300, height: 600 },
          area: 1800,
          momentOfInertiaIxx: 540000.0,
          momentOfInertiaIyy: 135000.0,
          torsionalConstantJ: 350000.0,
          weightPerMeter: 450.0
        }
      ],
      nodes: [
        // Base nodes (restrained)
        { id: 'N1', name: 'N1', x: 0, y: 0, z: 0, isRestrained: true, restraints: { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true } },
        { id: 'N2', name: 'N2', x: 6, y: 0, z: 0, isRestrained: true, restraints: { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true } },
        { id: 'N3', name: 'N3', x: 6, y: 6, z: 0, isRestrained: true, restraints: { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true } },
        { id: 'N4', name: 'N4', x: 0, y: 6, z: 0, isRestrained: true, restraints: { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true } },

        // Level 1 nodes
        { id: 'N5', name: 'N5', x: 0, y: 0, z: 3.5, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N6', name: 'N6', x: 6, y: 0, z: 3.5, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N7', name: 'N7', x: 6, y: 6, z: 3.5, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N8', name: 'N8', x: 0, y: 6, z: 3.5, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },

        // Roof nodes
        { id: 'N9', name: 'N9', x: 0, y: 0, z: 7.0, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N10', name: 'N10', x: 6, y: 0, z: 7.0, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N11', name: 'N11', x: 6, y: 6, z: 7.0, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } },
        { id: 'N12', name: 'N12', x: 0, y: 6, z: 7.0, isRestrained: false, restraints: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false } }
      ],
      members: [
        // Level 1 Columns
        { id: 'COL-1', name: 'C1', type: 'column', startNodeId: 'N1', endNodeId: 'N5', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1' },
        { id: 'COL-2', name: 'C2', type: 'column', startNodeId: 'N2', endNodeId: 'N6', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1' },
        { id: 'COL-3', name: 'C3', type: 'column', startNodeId: 'N3', endNodeId: 'N7', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1' },
        { id: 'COL-4', name: 'C4', type: 'column', startNodeId: 'N4', endNodeId: 'N8', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1' },

        // Level 1 Beams
        { id: 'BM-1', name: 'B1', type: 'beam', startNodeId: 'N5', endNodeId: 'N6', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 18.0 }] },
        { id: 'BM-2', name: 'B2', type: 'beam', startNodeId: 'N6', endNodeId: 'N7', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 18.0 }] },
        { id: 'BM-3', name: 'B3', type: 'beam', startNodeId: 'N7', endNodeId: 'N8', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 18.0 }] },
        { id: 'BM-4', name: 'B4', type: 'beam', startNodeId: 'N8', endNodeId: 'N5', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Story 1', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 18.0 }] },

        // Roof Columns
        { id: 'COL-5', name: 'C5', type: 'column', startNodeId: 'N5', endNodeId: 'N9', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof' },
        { id: 'COL-6', name: 'C6', type: 'column', startNodeId: 'N6', endNodeId: 'N10', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof' },
        { id: 'COL-7', name: 'C7', type: 'column', startNodeId: 'N7', endNodeId: 'N11', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof' },
        { id: 'COL-8', name: 'C8', type: 'column', startNodeId: 'N8', endNodeId: 'N12', sectionId: 'SEC-COL-400', materialId: 'MAT-C30', length: 3.5, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof' },

        // Roof Beams
        { id: 'BM-5', name: 'B5', type: 'beam', startNodeId: 'N9', endNodeId: 'N10', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 14.0 }] },
        { id: 'BM-6', name: 'B6', type: 'beam', startNodeId: 'N10', endNodeId: 'N11', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 14.0 }] },
        { id: 'BM-7', name: 'B7', type: 'beam', startNodeId: 'N11', endNodeId: 'N12', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 14.0 }] },
        { id: 'BM-8', name: 'B8', type: 'beam', startNodeId: 'N12', endNodeId: 'N9', sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', length: 6.0, rotationAngleDeg: 0, cardinalPoint: 10, story: 'Roof', loads: [{ loadPatternId: 'LP-DL', type: 'uniform', direction: 'global_z', magnitude: 14.0 }] }
      ],
      slabs: [
        {
          id: 'SLAB-L1',
          name: 'Level 1 RC Slab (200mm)',
          type: 'slab',
          thickness: 200,
          sectionId: 'SEC-SLAB-200',
          materialId: 'MAT-C30',
          nodeIds: ['N5', 'N6', 'N7', 'N8'],
          story: 'Story 1',
          elevationZ: 3.5,
          area: 36.0,
          diaphragm: 'rigid',
          loads: [{ loadPatternId: 'LP-LL', uniformLoad: 3.0 }]
        },
        {
          id: 'SLAB-ROOF',
          name: 'Roof RC Slab (180mm)',
          type: 'slab',
          thickness: 180,
          sectionId: 'SEC-SLAB-180',
          materialId: 'MAT-C30',
          nodeIds: ['N9', 'N10', 'N11', 'N12'],
          story: 'Roof',
          elevationZ: 7.0,
          area: 36.0,
          diaphragm: 'rigid',
          loads: [{ loadPatternId: 'LP-LL', uniformLoad: 1.5 }]
        }
      ],
      loadPatterns: [
        { id: 'LP-DL', name: 'Dead Load (Self-Weight + Finishes)', type: 'DEAD', selfWeightMultiplier: 1.0 },
        { id: 'LP-LL', name: 'Live Load (Imposed Occupancy)', type: 'LIVE', selfWeightMultiplier: 0.0 }
      ],
      loadCombinations: [
        {
          id: 'LC-ULS-1',
          name: '1.35 DL + 1.50 LL (Eurocode ULS Fundamental)',
          type: 'LINEAR_ADD',
          factors: [
            { loadPatternId: 'LP-DL', factor: 1.35 },
            { loadPatternId: 'LP-LL', factor: 1.50 }
          ],
          designType: 'STRENGTH'
        }
      ]
    };

    this.projects.set(benchmarkModel.metadata.id, benchmarkModel);
  }
}

export const projectRepository = ProjectRepository.getInstance();
