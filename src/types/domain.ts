import { StandardUnitSystemCode } from '../core/units/unitSystem';

export type DesignCodeStandard = 'EUROCODE' | 'ACI_318' | 'AISC_360' | 'BS_8110' | 'IS_456';

export interface ProjectMetadata {
  id: string;
  name: string;
  code: string;
  engineer: string;
  client: string;
  dateCreated: string;
  lastModified: string;
  revision: number;
  description: string;
  units: StandardUnitSystemCode;
  designCode: DesignCodeStandard;
  schemaVersion: string;
}

export interface RestraintDOFs {
  ux: boolean; // Translational X
  uy: boolean; // Translational Y
  uz: boolean; // Translational Z
  rx: boolean; // Rotational X
  ry: boolean; // Rotational Y
  rz: boolean; // Rotational Z
}

export interface NodePoint {
  id: string;
  name: string;
  x: number; // meters (base)
  y: number; // meters (base)
  z: number; // meters (base)
  isRestrained: boolean;
  restraints: RestraintDOFs;
  springStiffness?: {
    kx?: number; // kN/m
    ky?: number;
    kz?: number;
    krx?: number; // kN.m/rad
    kry?: number;
    krz?: number;
  };
  loads?: {
    loadPatternId: string;
    fx: number; // kN
    fy: number; // kN
    fz: number; // kN
    mx: number; // kN.m
    my: number; // kN.m
    mz: number; // kN.m
  }[];
}

export type CrossSectionShape = 
  | 'rectangular' 
  | 'i_beam' 
  | 'circular' 
  | 'tee' 
  | 'channel' 
  | 'box' 
  | 'pipe';

export interface SectionDimensions {
  width: number; // mm
  height: number; // mm
  flangeThickness?: number; // mm
  webThickness?: number; // mm
  diameter?: number; // mm
  wallThickness?: number; // mm
}

export interface SectionProperty {
  id: string;
  name: string;
  shape: CrossSectionShape;
  materialId: string;
  dimensions: SectionDimensions;
  area: number; // cm2
  momentOfInertiaIxx: number; // cm4
  momentOfInertiaIyy: number; // cm4
  torsionalConstantJ: number; // cm4
  weightPerMeter: number; // kg/m
}

export type MaterialType = 'concrete' | 'steel' | 'rebar' | 'timber' | 'masonry';

export interface MaterialDefinition {
  id: string;
  name: string;
  grade: string;
  type: MaterialType;
  elasticModulusE: number; // GPa
  poissonRatio: number; // dimensionless (e.g. 0.2)
  unitWeight: number; // kN/m3
  compressiveStrengthFc?: number; // MPa (for concrete)
  yieldStrengthFy?: number; // MPa (for steel/rebar)
  ultimateStrengthFu?: number; // MPa
  color: string;
}

export interface MemberEndReleases {
  start: {
    fx: boolean; // Axial release
    fy: boolean; // Shear Y release
    fz: boolean; // Shear Z release
    mx: boolean; // Torsion release
    my: boolean; // Minor moment release (hinge)
    mz: boolean; // Major moment release (hinge)
  };
  end: {
    fx: boolean;
    fy: boolean;
    fz: boolean;
    mx: boolean;
    my: boolean;
    mz: boolean;
  };
}

export interface MemberLoad {
  loadPatternId: string;
  type: 'uniform' | 'point' | 'trapezoidal';
  direction: 'global_z' | 'global_y' | 'global_x' | 'local_2' | 'local_3';
  magnitude: number; // kN/m or kN
  distanceFromStart?: number; // meters (for point loads)
}

export interface InternalMemberForces {
  axialP: number; // kN (Compression positive or negative according to sign convention)
  shearV2: number; // kN (Major shear)
  shearV3: number; // kN (Minor shear)
  torsionT: number; // kN.m
  momentM2: number; // kN.m (Minor moment)
  momentM3: number; // kN.m (Major moment)
  maxDeflection: number; // mm
  utilizationRatio: number; // 0.0 - 1.0+ (Demand / Capacity)
}

export type FrameMemberType = 'column' | 'beam' | 'brace';

export interface FrameMember {
  id: string;
  name: string;
  type: FrameMemberType;
  startNodeId: string;
  endNodeId: string;
  sectionId: string;
  materialId: string;
  length: number; // meters
  rotationAngleDeg: number; // beta angle (0 - 360 deg)
  cardinalPoint: number; // 1 to 9 insertion point (default 10: Centroid)
  story: string;
  releases?: MemberEndReleases;
  loads?: MemberLoad[];
  forces?: InternalMemberForces;
}

export interface PlanarSlab {
  id: string;
  name: string;
  type: 'slab' | 'wall' | 'opening';
  thickness: number; // mm
  sectionId: string;
  materialId: string;
  nodeIds: string[]; // Ordered polygon vertices
  story: string;
  elevationZ: number; // meters
  area: number; // m2
  diaphragm: 'rigid' | 'semi-rigid' | 'flexible' | 'none';
  loads?: {
    loadPatternId: string;
    uniformLoad: number; // kN/m2
  }[];
}

export interface GridLine {
  id: string;
  label: string;
  coordinate: number; // meters
  visible: boolean;
}

export interface GridSystem {
  id: string;
  name: string;
  originX: number;
  originY: number;
  rotationAngleDeg: number;
  xGrids: GridLine[];
  yGrids: GridLine[];
}

export interface StoryLevel {
  id: string;
  name: string;
  elevationZ: number; // meters
  height: number; // meters
  isMasterStory: boolean;
  similarToStoryId?: string;
  color?: string;
}

export type LoadPatternType = 'DEAD' | 'SUPER_DEAD' | 'LIVE' | 'WIND' | 'SEISMIC' | 'SNOW' | 'THERMAL';

export interface LoadPattern {
  id: string;
  name: string;
  type: LoadPatternType;
  selfWeightMultiplier: number; // e.g. 1.0 for DL, 0.0 for LL
}

export interface LoadCombinationFactor {
  loadPatternId: string;
  factor: number;
}

export interface LoadCombination {
  id: string;
  name: string;
  type: 'LINEAR_ADD' | 'ENVELOPE' | 'ABSOLUTE_ADD';
  factors: LoadCombinationFactor[];
  designType: 'STRENGTH' | 'SERVICEABILITY';
}

export interface AnalysisSummary {
  maxDisplacement: number; // mm
  maxDisplacementNodeId: string;
  fundamentalPeriodT1: number; // seconds
  fundamentalPeriodT2: number;
  fundamentalPeriodT3: number;
  totalMass: number; // Tonnes
  baseShearX: number; // kN
  baseShearY: number; // kN
  maxUtilization: number;
  criticalMemberId: string;
  timestamp: string;
  status: 'SOLVED' | 'UNSOLVED' | 'FAILED';
}

export interface StructuralModel {
  projectName: string;
  version: string;
  units: StandardUnitSystemCode;
  metadata: ProjectMetadata;
  stories: StoryLevel[];
  gridSystem: GridSystem;
  materials: MaterialDefinition[];
  sections: SectionProperty[];
  nodes: NodePoint[];
  members: FrameMember[];
  slabs: PlanarSlab[];
  loadPatterns: LoadPattern[];
  loadCombinations: LoadCombination[];
  analysisSummary?: AnalysisSummary;
}
