export enum ErrorSeverity {
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL'
}

export enum ErrorCategory {
  GEOMETRY_TOPOLOGY = 'GEOMETRY_TOPOLOGY',
  SECTION_MATERIAL = 'SECTION_MATERIAL',
  BOUNDARY_STABILITY = 'BOUNDARY_STABILITY',
  LOADS_COMBINATIONS = 'LOADS_COMBINATIONS',
  MODEL_SCHEMA = 'MODEL_SCHEMA',
  UNITS_SYSTEM = 'UNITS_SYSTEM',
  API_SYSTEM = 'API_SYSTEM',
  DATABASE_IO = 'DATABASE_IO'
}

export interface ErrorDefinition {
  code: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  title: string;
  messageTemplate: string;
  remedySuggestion: string;
}

export const ERROR_DEFINITIONS: Record<string, ErrorDefinition> = {
  // Geometry & Topology (E1000 - E1999)
  E1001: {
    code: 'E1001',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.WARNING,
    title: 'Orphan Node Detected',
    messageTemplate: 'Node "{objectId}" is isolated and not connected to any structural elements.',
    remedySuggestion: 'Connect the node to a frame member/slab or delete the unused node.'
  },
  E1002: {
    code: 'E1002',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Zero Length Element',
    messageTemplate: 'Frame member "{objectId}" has identical start and end node coordinates.',
    remedySuggestion: 'Specify distinct start and end nodes with non-zero length.'
  },
  E1003: {
    code: 'E1003',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Coincident Nodes',
    messageTemplate: 'Nodes "{objectId}" and "{targetId}" share the exact same spatial coordinates within tolerance.',
    remedySuggestion: 'Merge coincident nodes using the CAD merge tool to ensure structural continuity.'
  },
  E1004: {
    code: 'E1004',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Invalid Polygon Boundary',
    messageTemplate: 'Slab "{objectId}" has fewer than 3 boundary vertices or has self-intersecting edges.',
    remedySuggestion: 'Ensure the slab polygon has at least 3 non-collinear vertices with a closed boundary.'
  },
  E1005: {
    code: 'E1005',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Duplicate Structural Element',
    messageTemplate: 'Multiple frame members or elements connect the exact same joints ("{objectId}" and "{targetId}").',
    remedySuggestion: 'Delete or merge the redundant overlapping duplicate element.'
  },
  E1006: {
    code: 'E1006',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Disconnected / Dangling Element',
    messageTemplate: 'Element "{objectId}" references non-existent node ID "{targetId}".',
    remedySuggestion: 'Connect the element to valid nodes or delete dangling member references.'
  },
  E1007: {
    code: 'E1007',
    category: ErrorCategory.GEOMETRY_TOPOLOGY,
    severity: ErrorSeverity.ERROR,
    title: 'Degenerate Geometry',
    messageTemplate: 'Element/Polygon "{objectId}" has degenerate geometry (collinear points, non-planar vertices, or zero area: {details}).',
    remedySuggestion: 'Correct vertex coordinates to form valid planar geometric boundaries.'
  },

  // Section & Material Properties (E2000 - E2999)
  E2001: {
    code: 'E2001',
    category: ErrorCategory.SECTION_MATERIAL,
    severity: ErrorSeverity.ERROR,
    title: 'Unassigned Section Property',
    messageTemplate: 'Frame member "{objectId}" references missing or unassigned section property ID "{targetId}".',
    remedySuggestion: 'Assign a valid cross-section property from the Section Definition catalog.'
  },
  E2002: {
    code: 'E2002',
    category: ErrorCategory.SECTION_MATERIAL,
    severity: ErrorSeverity.ERROR,
    title: 'Unassigned Material Property',
    messageTemplate: 'Section "{objectId}" references missing or unassigned material ID "{targetId}".',
    remedySuggestion: 'Assign a valid material (e.g. Concrete C30/37 or Steel S355).'
  },
  E2003: {
    code: 'E2003',
    category: ErrorCategory.SECTION_MATERIAL,
    severity: ErrorSeverity.CRITICAL,
    title: 'Zero Moment of Inertia or Area',
    messageTemplate: 'Section "{objectId}" has non-positive area ({area}) or moment of inertia ({Ixx}).',
    remedySuggestion: 'Check section dimensions to ensure geometric properties are positive numbers.'
  },

  // Boundary Conditions & Stability (E3000 - E3999)
  E3001: {
    code: 'E3001',
    category: ErrorCategory.BOUNDARY_STABILITY,
    severity: ErrorSeverity.CRITICAL,
    title: 'No Base Support Restraints',
    messageTemplate: 'The structural model does not contain any fixed or pinned ground boundary restraints.',
    remedySuggestion: 'Assign support restraints (e.g., Fixed base, Pinned base) to ground-level foundation nodes.'
  },
  E3002: {
    code: 'E3002',
    category: ErrorCategory.BOUNDARY_STABILITY,
    severity: ErrorSeverity.ERROR,
    title: 'Potential Rigid Body Mechanism',
    messageTemplate: 'Node "{objectId}" has all connected members with moment releases, creating a local hinge mechanism.',
    remedySuggestion: 'Inspect member end releases to ensure joints maintain rotational or translational equilibrium.'
  },

  // Loads & Combinations (E4000 - E4999)
  E4001: {
    code: 'E4001',
    category: ErrorCategory.LOADS_COMBINATIONS,
    severity: ErrorSeverity.WARNING,
    title: 'No Load Patterns Defined',
    messageTemplate: 'The model has no active load patterns (Dead Load, Live Load, Wind, Seismic).',
    remedySuggestion: 'Define at least one load pattern and apply nodal or member loads.'
  },
  E4002: {
    code: 'E4002',
    category: ErrorCategory.LOADS_COMBINATIONS,
    severity: ErrorSeverity.ERROR,
    title: 'Empty Load Combination',
    messageTemplate: 'Load combination "{objectId}" does not include any load pattern factors.',
    remedySuggestion: 'Add load cases with non-zero load factors (e.g. 1.2 DL + 1.6 LL).'
  },

  // Schema & Serialization (E5000 - E5999)
  E5001: {
    code: 'E5001',
    category: ErrorCategory.MODEL_SCHEMA,
    severity: ErrorSeverity.ERROR,
    title: 'Model Schema Validation Failure',
    messageTemplate: 'Structural model schema validation failed: {details}.',
    remedySuggestion: 'Review JSON payload structure against StructuralModel schema definition.'
  },
  E5002: {
    code: 'E5002',
    category: ErrorCategory.MODEL_SCHEMA,
    severity: ErrorSeverity.ERROR,
    title: 'Unsupported Schema Version',
    messageTemplate: 'Model version "{details}" is not supported by current engine (Supported: <= 4.2.0).',
    remedySuggestion: 'Migrate the model using the schema migration utility.'
  },

  // API & Database (E6000 - E6999)
  E6001: {
    code: 'E6001',
    category: ErrorCategory.DATABASE_IO,
    severity: ErrorSeverity.ERROR,
    title: 'Project Not Found',
    messageTemplate: 'Project with ID "{objectId}" does not exist in repository.',
    remedySuggestion: 'Verify project ID or create a new project.'
  }
};
