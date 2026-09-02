import { z } from 'zod';

export const RestraintDOFsSchema = z.object({
  ux: z.boolean(),
  uy: z.boolean(),
  uz: z.boolean(),
  rx: z.boolean(),
  ry: z.boolean(),
  rz: z.boolean()
});

export const NodePointSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  x: z.number(),
  y: z.number(),
  z: z.number(),
  isRestrained: z.boolean(),
  restraints: RestraintDOFsSchema,
  springStiffness: z.object({
    kx: z.number().optional(),
    ky: z.number().optional(),
    kz: z.number().optional(),
    krx: z.number().optional(),
    kry: z.number().optional(),
    krz: z.number().optional()
  }).optional(),
  loads: z.array(z.object({
    loadPatternId: z.string(),
    fx: z.number(),
    fy: z.number(),
    fz: z.number(),
    mx: z.number(),
    my: z.number(),
    mz: z.number()
  })).optional()
});

export const SectionPropertySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  shape: z.enum(['rectangular', 'i_beam', 'circular', 'tee', 'channel', 'box', 'pipe']),
  materialId: z.string().min(1),
  dimensions: z.object({
    width: z.number().positive(),
    height: z.number().positive(),
    flangeThickness: z.number().positive().optional(),
    webThickness: z.number().positive().optional(),
    diameter: z.number().positive().optional(),
    wallThickness: z.number().positive().optional()
  }),
  area: z.number().positive(),
  momentOfInertiaIxx: z.number().positive(),
  momentOfInertiaIyy: z.number().positive(),
  torsionalConstantJ: z.number().positive(),
  weightPerMeter: z.number().nonnegative()
});

export const MaterialDefinitionSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  grade: z.string(),
  type: z.enum(['concrete', 'steel', 'rebar', 'timber', 'masonry']),
  elasticModulusE: z.number().positive(),
  poissonRatio: z.number().min(0).max(0.5),
  unitWeight: z.number().positive(),
  compressiveStrengthFc: z.number().positive().optional(),
  yieldStrengthFy: z.number().positive().optional(),
  ultimateStrengthFu: z.number().positive().optional(),
  color: z.string()
});

export const FrameMemberSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  type: z.enum(['column', 'beam', 'brace']),
  startNodeId: z.string().min(1),
  endNodeId: z.string().min(1),
  sectionId: z.string().min(1),
  materialId: z.string().min(1),
  length: z.number().positive(),
  rotationAngleDeg: z.number(),
  cardinalPoint: z.number().int().min(1).max(10),
  story: z.string(),
  releases: z.object({
    start: z.object({
      fx: z.boolean(), fy: z.boolean(), fz: z.boolean(),
      mx: z.boolean(), my: z.boolean(), mz: z.boolean()
    }),
    end: z.object({
      fx: z.boolean(), fy: z.boolean(), fz: z.boolean(),
      mx: z.boolean(), my: z.boolean(), mz: z.boolean()
    })
  }).optional(),
  loads: z.array(z.any()).optional(),
  forces: z.any().optional()
});

export const PlanarSlabSchema = z.object({
  id: z.string().min(1),
  name: z.string(),
  type: z.enum(['slab', 'wall', 'opening']),
  thickness: z.number().positive(),
  sectionId: z.string(),
  materialId: z.string(),
  nodeIds: z.array(z.string()).min(3),
  story: z.string(),
  elevationZ: z.number(),
  area: z.number().positive(),
  diaphragm: z.enum(['rigid', 'semi-rigid', 'flexible', 'none']),
  loads: z.array(z.any()).optional()
});

export const StructuralModelSchema = z.object({
  projectName: z.string().min(1),
  version: z.string(),
  units: z.enum(['kN-m, C', 'N-mm, C', 'kip-ft, F', 'kip-in, F', 'kgf-cm, C']),
  metadata: z.object({
    id: z.string(),
    name: z.string(),
    code: z.string(),
    engineer: z.string(),
    client: z.string(),
    dateCreated: z.string(),
    lastModified: z.string(),
    revision: z.number(),
    description: z.string(),
    units: z.enum(['kN-m, C', 'N-mm, C', 'kip-ft, F', 'kip-in, F', 'kgf-cm, C']),
    designCode: z.enum(['EUROCODE', 'ACI_318', 'AISC_360', 'BS_8110', 'IS_456']),
    schemaVersion: z.string()
  }),
  stories: z.array(z.object({
    id: z.string(),
    name: z.string(),
    elevationZ: z.number(),
    height: z.number(),
    isMasterStory: z.boolean(),
    similarToStoryId: z.string().optional(),
    color: z.string().optional()
  })),
  gridSystem: z.object({
    id: z.string(),
    name: z.string(),
    originX: z.number(),
    originY: z.number(),
    rotationAngleDeg: z.number(),
    xGrids: z.array(z.object({
      id: z.string(),
      label: z.string(),
      coordinate: z.number(),
      visible: z.boolean()
    })),
    yGrids: z.array(z.object({
      id: z.string(),
      label: z.string(),
      coordinate: z.number(),
      visible: z.boolean()
    }))
  }),
  materials: z.array(MaterialDefinitionSchema),
  sections: z.array(SectionPropertySchema),
  nodes: z.array(NodePointSchema),
  members: z.array(FrameMemberSchema),
  slabs: z.array(PlanarSlabSchema),
  loadPatterns: z.array(z.object({
    id: z.string(),
    name: z.string(),
    type: z.enum(['DEAD', 'SUPER_DEAD', 'LIVE', 'WIND', 'SEISMIC', 'SNOW', 'THERMAL']),
    selfWeightMultiplier: z.number()
  })),
  loadCombinations: z.array(z.object({
    id: z.string(),
    name: z.string(),
    type: z.enum(['LINEAR_ADD', 'ENVELOPE', 'ABSOLUTE_ADD']),
    factors: z.array(z.object({
      loadPatternId: z.string(),
      factor: z.number()
    })),
    designType: z.enum(['STRENGTH', 'SERVICEABILITY'])
  })),
  analysisSummary: z.any().optional()
});
