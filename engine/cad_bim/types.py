"""
STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY TYPES (PHASE 13)
Unified data structures, schemas, and enums for IFC, DXF, CSV, Excel, and JSON
interoperability with full metadata and geometry preservation.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field


class InteropFormat(str, Enum):
    IFC = "IFC"
    DXF = "DXF"
    CSV = "CSV"
    EXCEL = "EXCEL"
    JSON = "JSON"


class MergeStrategy(str, Enum):
    REPLACE = "REPLACE"          # Replace current model completely (with safety backup)
    MERGE_APPEND = "MERGE_APPEND" # Append new elements, preserve existing, re-ID if needed
    MERGE_UPDATE = "MERGE_UPDATE" # Merge coincident nodes within tolerance, update modified elements


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    message: str
    entity_type: str
    entity_id: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationSummary:
    is_valid: bool = True
    can_import: bool = True
    total_issues: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class BoundingBox3D:
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    min_z: float = 0.0
    max_z: float = 0.0

    @property
    def span_x(self) -> float:
        return self.max_x - self.min_x

    @property
    def span_y(self) -> float:
        return self.max_y - self.min_y

    @property
    def span_z(self) -> float:
        return self.max_z - self.min_z


@dataclass
class EntityCounts:
    nodes: int = 0
    columns: int = 0
    beams: int = 0
    braces: int = 0
    slabs: int = 0
    walls: int = 0
    openings: int = 0
    materials: int = 0
    sections: int = 0
    stories: int = 0
    layers: int = 0

    @property
    def total_members(self) -> int:
        return self.columns + self.beams + self.braces

    @property
    def total_entities(self) -> int:
        return (
            self.nodes
            + self.columns
            + self.beams
            + self.braces
            + self.slabs
            + self.walls
            + self.openings
        )


@dataclass
class LayerInfo:
    name: str
    color: str = "#96ccff"
    entity_count: int = 0
    detected_type: str = "member"  # member, slab, wall, node, unknown


@dataclass
class ImportPreviewSummary:
    format_type: InteropFormat
    source_name: str
    file_size_bytes: int = 0
    detected_units: str = "kN-m, C"
    counts: EntityCounts = field(default_factory=EntityCounts)
    bounding_box: BoundingBox3D = field(default_factory=BoundingBox3D)
    layers: List[LayerInfo] = field(default_factory=list)
    materials_found: List[str] = field(default_factory=list)
    sections_found: List[str] = field(default_factory=list)
    stories_detected: List[str] = field(default_factory=list)
    sample_nodes: List[Dict[str, Any]] = field(default_factory=list)
    sample_members: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CoordinateTransform:
    scale_factor: float = 1.0       # e.g., 0.001 for mm -> m, 0.0254 for in -> m
    offset_x: float = 0.0           # Translation dx in target meters
    offset_y: float = 0.0           # Translation dy in target meters
    offset_z: float = 0.0           # Translation dz in target meters
    swap_yz: bool = False           # Swap Y and Z (e.g. Y-up CAD to Z-up BIM)
    invert_z: bool = False          # Invert elevation


@dataclass
class MappingConfig:
    coordinate_transform: CoordinateTransform = field(default_factory=CoordinateTransform)
    layer_type_map: Dict[str, str] = field(default_factory=dict)       # layer_name -> "column"|"beam"|"brace"|"slab"|"wall"
    material_map: Dict[str, str] = field(default_factory=dict)         # external_name -> internal_material_id
    section_map: Dict[str, str] = field(default_factory=dict)           # external_name -> internal_section_id
    default_material_id: str = "MAT-C30"
    default_section_id: str = "SEC-COL-400X400"
    merge_strategy: MergeStrategy = MergeStrategy.REPLACE
    tolerance_m: float = 0.001       # 1 mm tolerance for duplicate node merging


@dataclass
class PreservationMetadata:
    original_format: InteropFormat
    original_guid_map: Dict[str, str] = field(default_factory=dict)  # internal_id -> original IFC GUID / handle
    custom_properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    layers_preserved: List[str] = field(default_factory=list)
    source_units: str = "m"
    exported_at: Optional[str] = None
    imported_at: Optional[str] = None


@dataclass
class InteropResult:
    success: bool
    format_type: InteropFormat
    message: str
    preview: Optional[ImportPreviewSummary] = None
    validation: Optional[ValidationSummary] = None
    data: Optional[Dict[str, Any]] = None  # Full structural model dict or export content
    file_content: Optional[str] = None     # String content for exported files
    metadata: Optional[PreservationMetadata] = None
