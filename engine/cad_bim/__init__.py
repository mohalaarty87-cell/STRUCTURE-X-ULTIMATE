"""
STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY MODULE (PHASE 13)
"""

from .types import (
    InteropFormat,
    MergeStrategy,
    ValidationSeverity,
    ValidationIssue,
    ValidationSummary,
    BoundingBox3D,
    EntityCounts,
    LayerInfo,
    ImportPreviewSummary,
    CoordinateTransform,
    MappingConfig,
    PreservationMetadata,
    InteropResult,
)
from .validator import ImportValidator
from .mapper import InteropMapper
from .ifc_handler import IfcHandler
from .dxf_handler import DxfHandler
from .csv_handler import CsvHandler
from .excel_handler import ExcelHandler
from .json_handler import JsonHandler
from .engine import CadBimInteropEngine

__all__ = [
    "InteropFormat",
    "MergeStrategy",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationSummary",
    "BoundingBox3D",
    "EntityCounts",
    "LayerInfo",
    "ImportPreviewSummary",
    "CoordinateTransform",
    "MappingConfig",
    "PreservationMetadata",
    "InteropResult",
    "ImportValidator",
    "InteropMapper",
    "IfcHandler",
    "DxfHandler",
    "CsvHandler",
    "ExcelHandler",
    "JsonHandler",
    "CadBimInteropEngine",
]
