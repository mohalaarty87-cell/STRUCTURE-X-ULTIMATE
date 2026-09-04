"""
STRUCTURE-X ULTIMATE — PROFESSIONAL ENGINEERING REPORTING ENGINE (PHASE 14)
Data types, schemas, and enumeration models for comprehensive calculation sheets
and code-compliant engineering reports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class DesignStatus(Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class ReportExportFormat(Enum):
    PDF = "PDF"
    HTML = "HTML"
    EXCEL = "EXCEL"
    CSV = "CSV"


@dataclass
class ProjectInfo:
    projectName: str = "Structure-X High-Rise Tower"
    projectNumber: str = "SX-2026-088"
    clientName: str = "Global Infrastructure Partners"
    engineerName: str = "Lead Structural PE / SE"
    checkerName: str = "Principal Engineer"
    date: str = "2026-09-04"
    revision: str = "Rev 0 - Issued for Construction"
    softwareName: str = "Structure-X Ultimate v5.0-PRO"
    structureType: str = "Multi-Story Dual System (RC Shear Wall + Frame)"
    buildingOccupancy: str = "Category III - Commercial / High Occupancy"
    location: str = "Seismic Zone 4 / High Wind Region"
    jobDescription: str = "Full 3D Finite Element and Code Design Report"


@dataclass
class UnitsConfig:
    force: str = "kN"
    lengthLarge: str = "m"
    lengthSmall: str = "mm"
    moment: str = "kN.m"
    stress: str = "MPa (N/mm²)"
    density: str = "kN/m³"
    mass: str = "tonne"
    angle: str = "deg"
    temperature: str = "°C"


@dataclass
class DesignCodesConfig:
    concreteCode: str = "Eurocode 2 (EN 1992-1-1:2004) / ACI 318-19"
    steelCode: str = "AISC 360-16 / Eurocode 3 (EN 1993-1-1:2005)"
    seismicCode: str = "ASCE 7-16 / Eurocode 8 (EN 1998-1:2004)"
    windCode: str = "ASCE 7-16 / Eurocode 1 (EN 1991-1-4:2005)"
    combinationsCode: str = "ASCE 7-16 Section 2.3 & Eurocode 0 (EN 1990)"


@dataclass
class StoryReportItem:
    storyId: str
    name: str
    elevation: float  # m
    height: float  # m
    diaphragmType: str = "Rigid Diaphragm"
    storyMass: float = 85.0  # tonnes
    driftLimit: float = 0.020  # 2.0%


@dataclass
class GridReportItem:
    gridId: str
    axis: str  # 'X' or 'Y'
    label: str
    coordinate: float  # m


@dataclass
class MaterialReportItem:
    materialId: str
    name: str
    matType: str  # concrete, steel, rebar
    grade: str
    elasticModulusE: float  # GPa
    poissonRatio: float
    unitWeight: float  # kN/m3
    f_c_or_f_y: float  # MPa (fc' for concrete, fy for steel)
    ultimateStrength: Optional[float] = None  # Fu for steel or fctm for concrete


@dataclass
class SectionReportItem:
    sectionId: str
    name: str
    shape: str
    materialName: str
    area: float  # cm2
    momentOfInertiaIxx: float  # cm4
    momentOfInertiaIyy: float  # cm4
    torsionalConstantJ: float  # cm4
    dimensionsDesc: str
    weightPerMeter: float  # kg/m


@dataclass
class GeometrySummary:
    totalNodes: int
    totalMembers: int
    totalColumns: int
    totalBeams: int
    totalBraces: int
    totalSlabs: int
    totalWalls: int
    boundingSpanX: float  # m
    boundingSpanY: float  # m
    totalHeight: float  # m
    totalGrossFloorArea: float  # m2


@dataclass
class LoadItem:
    loadId: str
    targetType: str  # Node, Member, Slab, Wall
    targetId: str
    loadCase: str
    type: str  # Point, Distributed, Surface
    magnitude: str  # e.g., "-45.0 kN", "24.0 kN/m", "3.5 kN/m²"


@dataclass
class LoadCaseItem:
    caseId: str
    name: str
    category: str  # Dead, Live, Wind, Seismic, Snow
    selfWeightMultiplier: float = 0.0
    description: str = ""


@dataclass
class LoadCombinationItem:
    comboId: str
    name: str
    limitState: str  # ULS (Strength) or SLS (Serviceability)
    factors: Dict[str, float] = field(default_factory=dict)
    formula: str = ""


@dataclass
class AnalysisSettingsReport:
    solverType: str = "3D Direct Stiffness FEM (6 DOF / Joint)"
    geometricNonlinearity: str = "P-Delta Second-Order Geometric Stiffness"
    eigenvalueAlgorithm: str = "Subspace Iteration / Accelerated Lanczos"
    convergenceTolerance: float = 1e-5
    maxPDeltaIterations: int = 25
    diaphragmConstraint: str = "Rigid In-Plane Constraint at Story Levels"
    slabMeshing: str = "DKT Thin Shell / Mindlin-Reissner Thick Shell"


@dataclass
class ModalResultItem:
    modeNumber: int
    period: float  # s
    frequency: float  # Hz
    eigenvalue: float  # rad^2/s^2
    massRatioX: float  # %
    massRatioY: float  # %
    massRatioZ: float  # %
    cumulativeMassX: float  # %
    cumulativeMassY: float  # %
    dominantDirection: str  # Translation X, Translation Y, Torsion Z


@dataclass
class SeismicResultReport:
    code: str = "ASCE 7-16 Equivalent Lateral Force & RSA"
    ss: float = 1.25  # g
    s1: float = 0.45  # g
    sds: float = 0.833  # g
    sd1: float = 0.450  # g
    rFactor: float = 6.0  # Response modification coefficient
    importanceFactorIe: float = 1.25
    baseShearVx: float = 540.2  # kN
    baseShearVy: float = 512.6  # kN
    totalWeightW: float = 6850.0  # kN
    baseShearRatioVxW: float = 0.0788
    baseShearRatioVyW: float = 0.0748
    modalCombinationRule: str = "CQC (Complete Quadratic Combination)"
    directionalRule: str = "SRSS / 100% + 30% Orthogonal"


@dataclass
class WindResultReport:
    code: str = "ASCE 7-16 Chapter 27 (MWFRS)"
    basicWindSpeed: float = 42.0  # m/s (approx 94 mph)
    exposureCategory: str = "Category B (Suburban / Built-up)"
    topographicFactorKzt: float = 1.0
    gustFactorG: float = 0.85
    baseOverturningMomentX: float = 4320.0  # kN.m
    baseOverturningMomentY: float = 3890.0  # kN.m
    totalWindBaseShearX: float = 318.5  # kN
    totalWindBaseShearY: float = 295.4  # kN


@dataclass
class StoryDriftItem:
    storyName: str
    elevation: float  # m
    storyHeight: float  # m
    driftX: float  # mm
    driftY: float  # mm
    driftRatioX: float  # Δ/h
    driftRatioY: float
    allowableDriftRatio: float = 0.020  # 2.0%
    status: DesignStatus = DesignStatus.PASS


@dataclass
class StoryShearItem:
    storyName: str
    elevation: float
    shearVx: float  # kN
    shearVy: float  # kN
    cumulativeOverturningMomentX: float  # kN.m
    cumulativeOverturningMomentY: float  # kN.m


@dataclass
class ReactionReportItem:
    nodeId: str
    coordinates: str  # (X, Y, Z) in m
    fx: float  # kN
    fy: float  # kN (Vertical)
    fz: float  # kN
    mx: float  # kN.m
    my: float  # kN.m
    mz: float  # kN.m
    loadCombo: str = "1.2D + 1.6L"


@dataclass
class MemberForceItem:
    memberId: str
    name: str
    memberType: str
    sectionName: str
    length: float  # m
    station: float  # m
    axialP: float  # kN
    shearV2: float  # kN
    shearV3: float  # kN
    torsionT: float  # kN.m
    momentM2: float  # kN.m
    momentM3: float  # kN.m
    utilizationRatio: float
    status: DesignStatus


@dataclass
class ConcreteDesignItem:
    elementId: str
    name: str
    elementType: str  # Beam or Column
    sectionDesc: str
    governingCombo: str
    axialPu: float  # kN
    momentMu: float  # kN.m
    momentCapacityPhiMn: float  # kN.m
    requiredFlexureRebarAs: float  # mm2
    providedRebarDesc: str  # e.g. "4-T25 (1964 mm²)"
    shearVu: float  # kN
    shearCapacityPhiVn: float  # kN
    providedShearLinks: str  # e.g. "T10 @ 150 mm c/c"
    dcRatio: float
    status: DesignStatus
    codeRef: str = "ACI 318-19 §9.5 / EC2 §6.1"


@dataclass
class SteelDesignItem:
    elementId: str
    name: str
    elementType: str  # Beam, Column, Brace
    profileName: str
    steelGrade: str
    governingCombo: str
    slendernessKLr: float
    axialDemandPu: float  # kN
    axialCapacityPhiPn: float  # kN
    momentDemandMu: float  # kN.m
    momentCapacityPhiMn: float  # kN.m
    shearDemandVu: float  # kN
    shearCapacityPhiVn: float  # kN
    interactionRatio: float  # e.g. Pu/(phi Pn) + 8/9*(Mu/(phi Mn))
    status: DesignStatus
    governingClause: str = "AISC 360-16 Eq. H1-1a / EN 1993-1-1 §6.3.3"


@dataclass
class WallDesignItem:
    wallId: str
    name: str
    story: str
    thickness: float  # mm
    length: float  # m
    axialDemandPu: float  # kN
    inPlaneShearVu: float  # kN
    shearCapacityPhiVn: float  # kN
    overturningMomentMu: float  # kN.m
    verticalRebarRatio: float  # % (e.g. 0.45%)
    boundaryElementRequired: bool
    dcRatio: float
    status: DesignStatus
    codeRef: str = "ACI 318-19 §18.10 / EC2 §5.4.3"


@dataclass
class SlabDesignItem:
    slabId: str
    name: str
    story: str
    thickness: float  # mm
    momentMxx: float  # kN.m/m
    momentMyy: float  # kN.m/m
    topMeshProvided: str  # e.g. "T12 @ 150 mm (754 mm²/m)"
    bottomMeshProvided: str
    punchingShearStress: float  # MPa
    punchingShearCapacity: float  # MPa
    maxDeflectionMm: float  # mm
    allowableDeflectionMm: float  # mm (e.g. L/250 = 24.0 mm)
    dcRatio: float
    status: DesignStatus
    codeRef: str = "ACI 318-19 §8.4 / EC2 §6.4"


@dataclass
class CalculationDetailItem:
    calcId: str
    title: str
    elementTarget: str
    designStandard: str
    demandExpression: str
    capacityExpression: str
    intermediateCalculations: List[str]
    governingRatio: float
    marginPct: float
    status: DesignStatus


@dataclass
class WarningItem:
    code: str
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    location: str
    description: str
    recommendation: str


@dataclass
class LimitationItem:
    category: str
    assumption: str
    applicabilityRange: str
    mitigationOrGuidance: str


@dataclass
class ProfessionalEngineeringReport:
    projectInfo: ProjectInfo
    units: UnitsConfig
    designCodes: DesignCodesConfig
    stories: List[StoryReportItem]
    grids: List[GridReportItem]
    materials: List[MaterialReportItem]
    sections: List[SectionReportItem]
    geometry: GeometrySummary
    loads: List[LoadItem]
    loadCases: List[LoadCaseItem]
    loadCombinations: List[LoadCombinationItem]
    analysisSettings: AnalysisSettingsReport
    modalResults: List[ModalResultItem]
    seismicResults: SeismicResultReport
    windResults: WindResultReport
    storyDrifts: List[StoryDriftItem]
    storyShears: List[StoryShearItem]
    reactions: List[ReactionReportItem]
    memberForces: List[MemberForceItem]
    concreteDesign: List[ConcreteDesignItem]
    steelDesign: List[SteelDesignItem]
    wallDesign: List[WallDesignItem]
    slabDesign: List[SlabDesignItem]
    calculationDetails: List[CalculationDetailItem]
    warnings: List[WarningItem]
    limitations: List[LimitationItem]
    overallStatus: DesignStatus = DesignStatus.PASS
