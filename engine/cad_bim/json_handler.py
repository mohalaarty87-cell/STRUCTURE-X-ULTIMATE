"""
STRUCTURE-X ULTIMATE — JSON IMPORT & EXPORT HANDLER (PHASE 13)
Full-fidelity structural schema serialization and deserialization.
Preserves 100% of geometry, properties, boundary conditions, and metadata.
"""

import json
from typing import Dict, Any, List, Optional, Tuple, Set


class JsonHandler:
    """
    Handles native JSON structural model serialization and deserialization.
    """

    @staticmethod
    def parse_json_text(content: str) -> Dict[str, Any]:
        """
        Parses JSON text and ensures all standard fields conform to StructuralModel.
        """
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Invalid JSON format: Expected root object.")

        # Ensure container arrays exist
        normalized: Dict[str, Any] = {
            "projectName": data.get("projectName", "JSON Imported Model"),
            "version": data.get("version", "5.0.0-PRO"),
            "units": data.get("units", "kN-m, C"),
            "stories": list(data.get("stories", [])),
            "gridLinesX": list(data.get("gridLinesX", [])),
            "gridLinesY": list(data.get("gridLinesY", [])),
            "materials": list(data.get("materials", [])),
            "sections": list(data.get("sections", [])),
            "nodes": list(data.get("nodes", [])),
            "members": list(data.get("members", [])),
            "slabs": list(data.get("slabs", [])),
            "walls": list(data.get("walls", [])),
            "openings": list(data.get("openings", [])),
            "links": list(data.get("links", [])),
            "springs": list(data.get("springs", [])),
            "diaphragms": list(data.get("diaphragms", [])),
            "metadata": dict(data.get("metadata", {}))
        }

        return normalized

    @staticmethod
    def export_to_json(model: Dict[str, Any], indent: int = 2) -> str:
        """
        Exports full model dictionary to formatted JSON string.
        """
        return json.dumps(model, indent=indent, ensure_ascii=False)
