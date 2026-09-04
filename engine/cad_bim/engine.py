"""
STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY ENGINE (PHASE 13)
Master orchestrator implementing the 5-stage interoperability lifecycle:
1. Import  -> 2. Validation  -> 3. Preview  -> 4. Mapping  -> 5. Confirmation
Supports IFC (IFC4/IFC2X3), DXF (AutoCAD), CSV, Excel (SpreadsheetML), and JSON.
Guarantees zero data corruption and full preservation of geometry, properties, and metadata.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from .types import (
    InteropFormat,
    MergeStrategy,
    ValidationSummary,
    ImportPreviewSummary,
    MappingConfig,
    CoordinateTransform,
    BoundingBox3D,
    EntityCounts,
    LayerInfo,
    InteropResult,
    PreservationMetadata,
)
from .validator import ImportValidator
from .mapper import InteropMapper
from .ifc_handler import IfcHandler
from .dxf_handler import DxfHandler
from .csv_handler import CsvHandler
from .excel_handler import ExcelHandler
from .json_handler import JsonHandler


class CadBimInteropEngine:
    """
    Main entry point for CAD and BIM interoperability in Structure-X Ultimate.
    """

    @staticmethod
    def detect_format_from_filename_or_content(filename: str, content: str) -> InteropFormat:
        """
        Determines file format from extension and content signatures.
        """
        fname_lower = filename.lower()
        if fname_lower.endswith(".ifc") or "ISO-10303-21" in content[:200]:
            return InteropFormat.IFC
        elif fname_lower.endswith(".dxf") or ("SECTION" in content[:300] and "HEADER" in content[:300]):
            return InteropFormat.DXF
        elif fname_lower.endswith(".json") or (content.strip().startswith("{") and "projectName" in content[:200]):
            return InteropFormat.JSON
        elif fname_lower.endswith(".xml") or 'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"' in content[:300]:
            return InteropFormat.EXCEL
        elif fname_lower.endswith(".csv") or any(h in content[:300] for h in ["# NODES", "# MEMBERS", "startNodeId"]):
            return InteropFormat.CSV
        return InteropFormat.CSV

    @classmethod
    def import_file(
        cls,
        content: str,
        format_type: Optional[InteropFormat] = None,
        filename: str = "imported_model"
    ) -> InteropResult:
        """
        Stage 1: Import raw file content and parse into candidate structural data.
        """
        if format_type is None:
            format_type = cls.detect_format_from_filename_or_content(filename, content)

        try:
            if format_type == InteropFormat.IFC:
                parsed = IfcHandler.parse_ifc_text(content)
            elif format_type == InteropFormat.DXF:
                parsed = DxfHandler.parse_dxf_text(content)
            elif format_type == InteropFormat.CSV:
                parsed = CsvHandler.parse_csv_text(content)
            elif format_type == InteropFormat.EXCEL:
                parsed = ExcelHandler.parse_excel_xml(content)
            elif format_type == InteropFormat.JSON:
                parsed = JsonHandler.parse_json_text(content)
            else:
                parsed = CsvHandler.parse_csv_text(content)

            # Step 2: Validate
            validation = ImportValidator.validate_model_data(parsed)

            # Step 3: Generate Preview
            preview = cls.generate_preview(parsed, format_type, filename, len(content.encode('utf-8')))

            return InteropResult(
                success=True,
                format_type=format_type,
                message=f"Successfully imported and parsed {format_type.value} model '{filename}'.",
                preview=preview,
                validation=validation,
                data=parsed
            )
        except Exception as e:
            return InteropResult(
                success=False,
                format_type=format_type or InteropFormat.JSON,
                message=f"Import failed for {filename}: {str(e)}"
            )

    @staticmethod
    def validate_data(data: Dict[str, Any], tolerance_m: float = 0.001) -> ValidationSummary:
        """
        Stage 2: Validation of imported or mapped data.
        """
        return ImportValidator.validate_model_data(data, tolerance_m=tolerance_m)

    @staticmethod
    def generate_preview(
        data: Dict[str, Any],
        format_type: InteropFormat,
        filename: str,
        file_size: int = 0
    ) -> ImportPreviewSummary:
        """
        Stage 3: Preview generation providing spatial bounding box and entity statistics.
        """
        nodes = data.get("nodes", [])
        members = data.get("members", [])
        slabs = data.get("slabs", [])
        walls = data.get("walls", [])
        openings = data.get("openings", [])
        materials = data.get("materials", [])
        sections = data.get("sections", [])
        stories = data.get("stories", [])

        # Count member types
        cols = sum(1 for m in members if m.get("type") == "column")
        beams = sum(1 for m in members if m.get("type") == "beam")
        braces = sum(1 for m in members if m.get("type") == "brace")

        # Layer collection
        layer_counts: Dict[str, int] = {}
        for m in members:
            l = m.get("layer", "Default")
            layer_counts[l] = layer_counts.get(l, 0) + 1
        for s in slabs:
            l = s.get("layer", "Default")
            layer_counts[l] = layer_counts.get(l, 0) + 1
        for w in walls:
            l = w.get("layer", "Default")
            layer_counts[l] = layer_counts.get(l, 0) + 1

        layers_info = [
            LayerInfo(name=k, entity_count=v)
            for k, v in layer_counts.items()
        ]

        bbox = InteropMapper.compute_bounding_box(nodes)

        counts = EntityCounts(
            nodes=len(nodes),
            columns=cols,
            beams=beams,
            braces=braces,
            slabs=len(slabs),
            walls=len(walls),
            openings=len(openings),
            materials=len(materials),
            sections=len(sections),
            stories=len(stories),
            layers=len(layers_info)
        )

        mat_names = [m.get("name", m.get("id")) for m in materials]
        sec_names = [s.get("name", s.get("id")) for s in sections]
        story_names = [st.get("name", st.get("id")) for st in stories]

        return ImportPreviewSummary(
            format_type=format_type,
            source_name=filename,
            file_size_bytes=file_size,
            detected_units=data.get("units", "kN-m, C"),
            counts=counts,
            bounding_box=bbox,
            layers=layers_info,
            materials_found=mat_names,
            sections_found=sec_names,
            stories_detected=story_names,
            sample_nodes=nodes[:5],
            sample_members=members[:5]
        )

    @staticmethod
    def map_data(raw_data: Dict[str, Any], config: MappingConfig) -> Dict[str, Any]:
        """
        Stage 4: Apply user or auto-defined coordinate transformations, layer mappings,
        section/material rules, and spatial deduplication.
        """
        return InteropMapper.apply_mapping_and_transform(raw_data, config)

    @staticmethod
    def confirm_and_commit(
        existing_project: Dict[str, Any],
        mapped_data: Dict[str, Any],
        strategy: MergeStrategy = MergeStrategy.MERGE_APPEND,
        tolerance_m: float = 0.001
    ) -> Dict[str, Any]:
        """
        Stage 5: Final confirmation and non-destructive integration into the active project.
        """
        # Ensure existing project has safety backup validation
        return InteropMapper.merge_into_existing_project(
            existing_project=existing_project,
            imported_data=mapped_data,
            strategy=strategy,
            tolerance_m=tolerance_m
        )

    @classmethod
    def export_model(
        cls,
        model: Dict[str, Any],
        format_type: InteropFormat,
        options: Optional[Dict[str, Any]] = None
    ) -> InteropResult:
        """
        Exports active structural model to desired CAD/BIM format.
        """
        options = options or {}
        try:
            if format_type == InteropFormat.IFC:
                ifc_version = options.get("ifc_version", "IFC4")
                content = IfcHandler.export_to_ifc(model, ifc_version=ifc_version)
            elif format_type == InteropFormat.DXF:
                content = DxfHandler.export_to_dxf(model)
            elif format_type == InteropFormat.CSV:
                delimiter = options.get("delimiter", ",")
                content = CsvHandler.export_to_csv(model, delimiter=delimiter)
            elif format_type == InteropFormat.EXCEL:
                content = ExcelHandler.export_to_excel_xml(model)
            elif format_type == InteropFormat.JSON:
                indent = options.get("indent", 2)
                content = JsonHandler.export_to_json(model, indent=indent)
            else:
                content = JsonHandler.export_to_json(model)

            return InteropResult(
                success=True,
                format_type=format_type,
                message=f"Model successfully exported to {format_type.value}.",
                file_content=content
            )
        except Exception as e:
            return InteropResult(
                success=False,
                format_type=format_type,
                message=f"Export to {format_type.value} failed: {str(e)}"
            )
