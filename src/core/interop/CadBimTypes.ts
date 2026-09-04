/**
 * STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY TYPES (PHASE 13)
 */

export type InteropFormat = 'IFC' | 'DXF' | 'CSV' | 'EXCEL' | 'JSON';

export type MergeStrategy = 'REPLACE' | 'MERGE_APPEND' | 'MERGE_UPDATE';

export type ValidationSeverity = 'INFO' | 'WARNING' | 'ERROR';

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: string;
  message: string;
  entityType: string;
  entityId?: string;
  suggestedFix?: string;
}

export interface ValidationSummary {
  isValid: boolean;
  canImport: boolean;
  totalIssues: number;
  errorCount: number;
  warningCount: number;
  infoCount: number;
  issues: ValidationIssue[];
}

export interface BoundingBox3D {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
  spanX: number;
  spanY: number;
  spanZ: number;
}

export interface EntityCounts {
  nodes: number;
  columns: number;
  beams: number;
  braces: number;
  slabs: number;
  walls: number;
  openings: number;
  materials: number;
  sections: number;
  stories: number;
  layers: number;
  totalMembers: number;
  totalEntities: number;
}

export interface LayerInfo {
  name: string;
  color?: string;
  entityCount: number;
  detectedType: 'column' | 'beam' | 'brace' | 'slab' | 'wall' | 'node' | 'unknown';
}

export interface ImportPreviewSummary {
  formatType: InteropFormat;
  sourceName: string;
  fileSizeBytes: number;
  detectedUnits: string;
  counts: EntityCounts;
  boundingBox: BoundingBox3D;
  layers: LayerInfo[];
  materialsFound: string[];
  sectionsFound: string[];
  storiesDetected: string[];
  sampleNodes: Array<{ id: string; x: number; y: number; z: number }>;
  sampleMembers: Array<{ id: string; name: string; type: string; startNodeId: string; endNodeId: string }>;
}

export interface CoordinateTransform {
  scaleFactor: number; // e.g. 0.001 for mm -> m
  offsetX: number;
  offsetY: number;
  offsetZ: number;
  swapYZ: boolean;
  invertZ: boolean;
}

export interface MappingConfig {
  coordinateTransform: CoordinateTransform;
  layerTypeMap: Record<string, 'column' | 'beam' | 'brace' | 'slab' | 'wall'>;
  materialMap: Record<string, string>;
  sectionMap: Record<string, string>;
  defaultMaterialId: string;
  defaultSectionId: string;
  mergeStrategy: MergeStrategy;
  toleranceM: number;
}

export interface InteropResult<T = any> {
  success: boolean;
  formatType: InteropFormat;
  message: string;
  preview?: ImportPreviewSummary;
  validation?: ValidationSummary;
  data?: T;
  fileContent?: string;
}
