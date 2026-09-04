/**
 * Structure-X Ultimate - Core Engineering Types & Data Models
 */

export type ElementType = 'column' | 'beam' | 'brace' | 'slab' | 'wall' | 'opening' | 'link' | 'spring';

export type MaterialType = 'concrete' | 'steel' | 'timber' | 'composite';

export interface Material {
  id: string;
  name: string;
  type: MaterialType;
  grade: string;
  elasticModulusE: number; // in GPa (e.g. 33 for C30/37, 210 for S355)
  poissonRatio: number; // e.g. 0.2 for concrete, 0.3 for steel
  unitWeight: number; // in kN/m3 (e.g. 25 for concrete, 78.5 for steel)
  yieldStrengthFy?: number; // MPa
  compressiveStrengthFc?: number; // MPa
  color: string;
}

export type CrossSectionShape = 'rectangular' | 'circular' | 'i_beam' | 'tee' | 'box' | 'angle' | 'channel' | 'pipe';

export interface SectionProperty {
  id: string;
  name: string;
  shape: CrossSectionShape;
  materialId: string;
  dimensions: {
    width: number; // in mm
    height: number; // in mm
    flangeThickness?: number; // mm
    webThickness?: number; // mm
    diameter?: number; // mm
    wallThickness?: number; // mm
  };
  area: number; // cm2
  momentOfInertiaIxx: number; // cm4
  momentOfInertiaIyy: number; // cm4
  torsionalConstantJ: number; // cm4
  weightPerMeter: number; // kg/m
}

export interface NodePoint {
  id: string;
  name?: string;
  x: number; // meters
  y: number; // meters (height/elevation in Three.js Z or CAD Y)
  z: number; // meters
  isRestrained?: {
    fx: boolean;
    fy: boolean;
    fz: boolean;
    mx: boolean;
    my: boolean;
    mz: boolean;
  };
  springStiffness?: {
    kx?: number; // kN/m
    ky?: number; // kN/m
    kz?: number; // kN/m
    krx?: number; // kN.m/rad
    kry?: number; // kN.m/rad
    krz?: number; // kN.m/rad
  };
  loads?: {
    fx: number; // kN
    fy: number; // kN
    fz: number; // kN
    mx?: number; // kN.m
    my?: number; // kN.m
    mz?: number; // kN.m
  };
}

export type ReleaseType = 'Continuous' | 'Pinned-Pinned' | 'Pinned-Fixed' | 'Fixed-Pinned' | 'Custom';

export interface StructuralMember {
  id: string;
  name: string;
  type: ElementType;
  story: string;
  startNodeId: string;
  endNodeId: string;
  sectionId: string;
  materialId: string;
  length: number; // meters
  releases: ReleaseType;
  localAxisAngle: number; // degrees (beta angle)
  cardinalPoint?: number; // 1 to 9 (default 10 centroid)
  distributedLoad?: number; // kN/m
  // Calculation results
  forces?: {
    axialP: number; // kN (Compression - / Tension +)
    shearV2: number; // kN
    shearV3: number; // kN
    torsionT: number; // kN.m
    momentM2: number; // kN.m
    momentM3: number; // kN.m (Major bending moment)
    maxDeflection: number; // mm
    utilizationRatio: number; // 0.0 - 1.5+ (e.g., 0.68 = 68% capacity)
    designStatus: 'PASS' | 'WARNING' | 'FAIL';
  };
}

export interface SlabElement {
  id: string;
  name: string;
  story: string;
  nodeIds: string[]; // 3+ polygon vertices
  thickness: number; // meters
  materialId: string;
  sectionId?: string;
  loadDead: number; // kN/m2
  loadLive: number; // kN/m2
  diaphragm?: 'rigid' | 'semi-rigid' | 'flexible' | 'none';
  forces?: {
    mxx: number; // kN.m/m
    myy: number; // kN.m/m
    vmax: number; // kN/m
    deflection: number; // mm
    status: 'PASS' | 'WARNING' | 'FAIL';
  };
}

export interface WallElement {
  id: string;
  name: string;
  story: string;
  nodeIds: string[]; // 4 corner nodes
  thickness: number; // meters (e.g. 0.25)
  materialId: string;
  sectionId?: string;
  loadDistributed?: number; // kN/m
  forces?: {
    axialP: number; // kN
    shearV: number; // kN
    momentM: number; // kN.m
    status: 'PASS' | 'WARNING' | 'FAIL';
  };
}

export interface OpeningElement {
  id: string;
  name: string;
  story: string;
  parentType: 'slab' | 'wall';
  parentId: string;
  nodeIds: string[]; // polygon vertices of opening
  width?: number; // meters
  height?: number; // meters
}

export interface LinkElement {
  id: string;
  name: string;
  story?: string;
  startNodeId: string;
  endNodeId: string;
  type: 'linear' | 'gap' | 'hook' | 'damper';
  stiffness: {
    kx: number; // kN/m
    ky: number; // kN/m
    kz: number; // kN/m
    krx?: number; // kN.m/rad
    kry?: number; // kN.m/rad
    krz?: number; // kN.m/rad
  };
}

export interface SpringElement {
  id: string;
  name: string;
  nodeId: string;
  story?: string;
  type: 'ground' | 'line';
  kx: number; // kN/m
  ky: number; // kN/m
  kz: number; // kN/m
  krx?: number; // kN.m/rad
  kry?: number; // kN.m/rad
  krz?: number; // kN.m/rad
}

export interface DiaphragmDefinition {
  id: string;
  name: string;
  story: string;
  type: 'rigid' | 'semi-rigid' | 'flexible';
  centerOfMass?: { x: number; y: number; z: number };
  centerOfRigidity?: { x: number; y: number; z: number };
  nodeIds: string[];
}

export interface StoryLevel {
  id: string;
  name: string;
  elevation: number; // meters
  height: number; // meters
  isMasterStory?: boolean;
  similarToStoryId?: string;
}

export interface GridLine {
  id: string;
  label: string;
  axis: 'X' | 'Y';
  coordinate: number; // meters
}

export interface StructuralModel {
  projectName: string;
  version: string;
  units: 'kN-m, C' | 'N-mm, C' | 'kip-ft, F' | 'kgf-cm, C';
  stories: StoryLevel[];
  gridLinesX: GridLine[];
  gridLinesY: GridLine[];
  materials: Material[];
  sections: SectionProperty[];
  nodes: NodePoint[];
  members: StructuralMember[];
  slabs: SlabElement[];
  walls?: WallElement[];
  openings?: OpeningElement[];
  links?: LinkElement[];
  springs?: SpringElement[];
  diaphragms?: DiaphragmDefinition[];
}

export type ActiveCadTool = 
  | 'select'
  | 'joint'
  | 'beam'
  | 'column'
  | 'brace'
  | 'slab'
  | 'wall'
  | 'opening'
  | 'link'
  | 'spring'
  | 'diaphragm'
  | 'support'
  | 'load'
  | 'measure'
  | 'snap';

export type ViewportMode = '3d' | 'plan' | 'elevation';
export type DisplayMode = 'extruded' | 'wireframe' | 'deformed' | 'bmd' | 'sfd' | 'axial' | 'stress';
export type CameraProjection = 'perspective' | 'orthographic';
export type CameraPreset = 'iso' | 'iso-ne' | 'iso-nw' | 'iso-se' | 'iso-sw' | 'plan' | 'elevation-xz' | 'elevation-yz';

export interface LayerVisibilityState {
  grid: boolean;
  story: boolean;
  frame: boolean;
  shell: boolean;
  wall: boolean;
  load: boolean;
  support: boolean;
  result: boolean;
  selection: boolean;
  annotation: boolean;
}

export const DEFAULT_LAYER_VISIBILITY: LayerVisibilityState = {
  grid: true,
  story: true,
  frame: true,
  shell: true,
  wall: true,
  load: true,
  support: true,
  result: true,
  selection: true,
  annotation: true
};

export interface AnnotationSettings {
  showNodeLabels: boolean;
  showElementLabels: boolean;
  showDimensions: boolean;
  showStoryMarkers: boolean;
  showLocalAxes: boolean;
}

export const DEFAULT_ANNOTATION_SETTINGS: AnnotationSettings = {
  showNodeLabels: false,
  showElementLabels: true,
  showDimensions: true,
  showStoryMarkers: true,
  showLocalAxes: false
};

export interface ConsoleMessage {
  id: string;
  timestamp: string;
  type: 'info' | 'warn' | 'error' | 'success' | 'command';
  text: string;
  source?: string;
}

export interface JointDisplacementResult {
  nodeId: string;
  ux: number; // mm
  uy: number; // mm
  uz: number; // mm
  rx: number; // mrad
  ry: number; // mrad
  rz: number; // mrad
}

export interface JointReactionResult {
  nodeId: string;
  fx: number; // kN
  fy: number; // kN
  fz: number; // kN
  mx: number; // kN.m
  my: number; // kN.m
  mz: number; // kN.m
}

export interface FrameForceResult {
  memberId: string;
  axialP: number; // kN
  shearV2: number; // kN
  shearV3: number; // kN
  torsionT: number; // kN.m
  momentM2: number; // kN.m
  momentM3: number; // kN.m
}

export interface ShellForceResult {
  shellId: string;
  Nxx: number; // kN/m
  Nyy: number; // kN/m
  Nxy: number; // kN/m
  Mxx: number; // kN.m/m
  Myy: number; // kN.m/m
  Mxy: number; // kN.m/m
  Vxz: number; // kN/m
  Vyz: number; // kN/m
  vonMisesTop: number; // MPa
  vonMisesBot: number; // MPa
}

export interface ModalModeResult {
  modeNumber: number;
  frequency: number; // Hz
  period: number; // s
  eigenvalue: number; // rad^2/s^2
  participationMass: { X: number; Y: number; Z: number }; // tonnes
  participationRatio: { X: number; Y: number; Z: number }; // ratio (0 to 1) or %
  effectiveModalMass: { X: number; Y: number; Z: number }; // tonnes
  cumulativeMassRatio: { X: number; Y: number; Z: number }; // %
  displacements?: Record<string, { ux: number; uy: number; uz: number; rx?: number; ry?: number; rz?: number }>;
}

export interface PDeltaIterationStep {
  iteration: number;
  residualNorm: number;
  displacementNorm: number;
  converged: boolean;
}

export interface PDeltaResultData {
  converged: boolean;
  iterations: number;
  convergenceTolerance: number;
  iterationHistory: PDeltaIterationStep[];
  criticalBucklingFactorLambda: number;
  momentAmplificationB1: number;
  displacementAmplificationRatio: number;
  stabilityState: 'STABLE' | 'MARGINAL' | 'UNSTABLE_BUCKLING';
  linearMaxDisplacement: number; // mm
  secondOrderMaxDisplacement: number; // mm
  linearBaseOverturningMoment: number; // kN.m
  secondOrderBaseOverturningMoment: number; // kN.m
  secondOrderDisplacements: Record<string, JointDisplacementResult>;
  secondOrderReactions: Record<string, JointReactionResult>;
}

export interface StoryResponseData {
  storyIndex: number;
  storyName: string;
  elevation: number; // m
  storyHeight: number; // m
  storyShearX: number; // kN
  storyShearZ: number; // kN
  storyDriftX: number; // mm
  storyDriftZ: number; // mm
  driftRatioX: number;
  driftRatioZ: number;
  displacementX: number; // mm
  displacementZ: number; // mm
  allowableDriftRatio: number; // e.g. 0.02
  driftAcceptableX: boolean;
  driftAcceptableZ: boolean;
}

export interface ModalSpectrumResponseData {
  modeNumber: number;
  period: number; // s
  frequency: number; // Hz
  sa_g: number; // g
  modalBaseShearX: number; // kN
  modalBaseShearZ: number; // kN
  massParticipationX: number; // %
  massParticipationZ: number; // %
  effectiveModalMassX: number; // tonnes
  effectiveModalMassZ: number; // tonnes
}

export interface ResponseSpectrumResultData {
  spectrumDefinition: {
    code: 'ASCE7' | 'EUROCODE8' | 'CUSTOM';
    Ss: number;
    S1: number;
    Fa: number;
    Fv: number;
    TL: number;
    R: number;
    Ie: number;
    dampingRatio: number;
    S_DS: number;
    S_D1: number;
    T0: number;
    Ts: number;
  };
  spectrumCurve: Array<{ period: number; sa: number }>;
  modalCombination: 'CQC' | 'SRSS';
  directionalCombination: 'SRSS' | '100-30';
  baseShearX: number; // kN
  baseShearZ: number; // kN
  totalStructuralWeight: number; // kN
  baseShearRatioX: number; // Vb_X / W
  baseShearRatioZ: number; // Vb_Z / W
  directionalBaseShearSRSS: number; // kN
  directionalBaseShear100_30: number; // kN
  storyResponses: StoryResponseData[];
  modalResponses: ModalSpectrumResponseData[];
  cqcCorrelationMatrix: number[][];
  maxDriftRatioX: number;
  maxDriftRatioZ: number;
  governingDriftStory: number;
  isDriftCompliant: boolean;
}

export interface AnalysisSummary {
  isSolved: boolean;
  totalNodes: number;
  totalEquations: number;
  maxDisplacement: number; // mm
  criticalMemberId: string;
  maxUtilization: number;
  fundamentalPeriodT1: number; // seconds
  totalMass: number; // tonnes
  executionTimeMs?: number;
  warnings: string[];
  errors: string[];
  modes?: ModalModeResult[];
  jointDisplacements?: Record<string, JointDisplacementResult>;
  jointReactions?: Record<string, JointReactionResult>;
  frameForces?: Record<string, FrameForceResult>;
  shellForces?: Record<string, ShellForceResult>;
  totalEffectiveMass?: { X: number; Y: number; Z: number };
  pDelta?: PDeltaResultData;
  responseSpectrum?: ResponseSpectrumResultData;
}
