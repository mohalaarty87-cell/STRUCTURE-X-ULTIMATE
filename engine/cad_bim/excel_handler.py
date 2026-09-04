"""
STRUCTURE-X ULTIMATE — EXCEL WORKBOOK HANDLER (PHASE 13)
Multi-sheet spreadsheet importer and exporter for structural BIM data.
Generates and parses standards-compliant Microsoft Excel XML Workbooks (SpreadsheetML)
supporting multi-sheet representations: Project_Info, Nodes, Members, Slabs, Walls, Materials, Sections.
"""

import re
import io
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple, Set


class ExcelHandler:
    """
    Handles multi-sheet Excel workbooks with full preservation of structural entity tables.
    Uses universal Microsoft SpreadsheetML XML (supported by all versions of Excel, Calc, Sheets).
    """

    NS = {
        "ss": "urn:schemas-microsoft-com:office:spreadsheet",
        "o": "urn:schemas-microsoft-com:office:office",
        "x": "urn:schemas-microsoft-com:office:excel",
        "html": "http://www.w3.org/TR/REC-html40"
    }

    @staticmethod
    def parse_excel_xml(content: str) -> Dict[str, Any]:
        """
        Parses an Excel SpreadsheetML XML string into a structural model dictionary.
        """
        try:
            # Strip namespaces and tag/attribute prefixes for simple robust traversal
            clean_xml = re.sub(r'xmlns(:\w+)?="[^"]*"', '', content)
            clean_xml = re.sub(r'(</?|\s)[a-zA-Z0-9_]+:([a-zA-Z0-9_]+)', r'\1\2', clean_xml)
            root = ET.fromstring(clean_xml)
        except Exception:
            # Fallback: if user provided CSV/tab inside excel text
            from .csv_handler import CsvHandler
            return CsvHandler.parse_csv_text(content)

        worksheets: Dict[str, List[List[str]]] = {}

        for ws in root.findall(".//Worksheet"):
            ws_name = ws.attrib.get("Name", "Sheet").upper()
            rows_data: List[List[str]] = []
            table = ws.find("Table")
            if table is not None:
                for row in table.findall("Row"):
                    cell_vals: List[str] = []
                    for cell in row.findall("Cell"):
                        data_el = cell.find("Data")
                        val = data_el.text if (data_el is not None and data_el.text) else ""
                        cell_vals.append(val.strip())
                    if any(cell_vals):
                        rows_data.append(cell_vals)
            worksheets[ws_name] = rows_data

        # Helper to convert sheet rows to list of dicts using first row as headers
        def sheet_to_dicts(sheet_rows: List[List[str]]) -> List[Dict[str, str]]:
            if len(sheet_rows) < 2:
                return []
            headers = [h.strip() for h in sheet_rows[0]]
            records = []
            for r in sheet_rows[1:]:
                rec = {}
                for idx, h in enumerate(headers):
                    val = r[idx] if idx < len(r) else ""
                    rec[h] = val
                records.append(rec)
            return records

        # 1. Parse Nodes
        nodes_sheet = worksheets.get("NODES", [])
        parsed_nodes = []
        for r in sheet_to_dicts(nodes_sheet):
            nid = r.get("id") or r.get("ID") or f"N_{len(parsed_nodes)+1}"
            try:
                x = float(r.get("x", 0.0) or 0.0)
                y = float(r.get("y", 0.0) or 0.0)
                z = float(r.get("z", 0.0) or 0.0)
            except ValueError:
                continue

            restraints = None
            if "restraint_ux" in r or "restraints" in r:
                restraints = {
                    "translationX": r.get("restraint_ux") in ["1", "true", "True"],
                    "translationY": r.get("restraint_uy") in ["1", "true", "True"],
                    "translationZ": r.get("restraint_uz") in ["1", "true", "True"],
                    "rotationX": r.get("restraint_rx") in ["1", "true", "True"],
                    "rotationY": r.get("restraint_ry") in ["1", "true", "True"],
                    "rotationZ": r.get("restraint_rz") in ["1", "true", "True"],
                }

            parsed_nodes.append({
                "id": str(nid),
                "x": x,
                "y": y,
                "z": z,
                "restraints": restraints
            })

        # 2. Parse Members
        members_sheet = worksheets.get("MEMBERS", [])
        parsed_members = []
        for r in sheet_to_dicts(members_sheet):
            mid = r.get("id") or r.get("ID") or f"M_{len(parsed_members)+1}"
            sn = r.get("startNodeId") or r.get("startNode") or ""
            en = r.get("endNodeId") or r.get("endNode") or ""
            mtype = (r.get("type") or "beam").lower()

            parsed_members.append({
                "id": str(mid),
                "name": r.get("name") or str(mid),
                "type": mtype if mtype in ["column", "beam", "brace"] else "beam",
                "story": r.get("story", "Story 1"),
                "startNodeId": str(sn),
                "endNodeId": str(en),
                "sectionId": r.get("sectionId", "SEC-COL-400X400"),
                "materialId": r.get("materialId", "MAT-C30"),
                "releases": r.get("releases", "Continuous"),
                "localAxisAngle": float(r.get("localAxisAngle", 0.0) or 0.0)
            })

        # 3. Parse Slabs
        slabs_sheet = worksheets.get("SLABS", [])
        parsed_slabs = []
        for r in sheet_to_dicts(slabs_sheet):
            sid = r.get("id") or f"SLAB_{len(parsed_slabs)+1}"
            node_str = r.get("nodeIds", "")
            nids = [n.strip() for n in node_str.replace(";", " ").replace(",", " ").split() if n.strip()]
            parsed_slabs.append({
                "id": str(sid),
                "name": r.get("name") or str(sid),
                "story": r.get("story", "Story 1"),
                "nodeIds": nids,
                "thickness": float(r.get("thickness", 0.20) or 0.20),
                "materialId": r.get("materialId", "MAT-C30"),
                "loadDead": float(r.get("loadDead", 2.5) or 2.5),
                "loadLive": float(r.get("loadLive", 3.0) or 3.0),
                "diaphragm": r.get("diaphragm", "rigid")
            })

        # 4. Parse Walls
        walls_sheet = worksheets.get("WALLS", [])
        parsed_walls = []
        for r in sheet_to_dicts(walls_sheet):
            wid = r.get("id") or f"WALL_{len(parsed_walls)+1}"
            node_str = r.get("nodeIds", "")
            nids = [n.strip() for n in node_str.replace(";", " ").replace(",", " ").split() if n.strip()]
            parsed_walls.append({
                "id": str(wid),
                "name": r.get("name") or str(wid),
                "story": r.get("story", "Story 1"),
                "nodeIds": nids,
                "thickness": float(r.get("thickness", 0.25) or 0.25),
                "materialId": r.get("materialId", "MAT-C30")
            })

        # 5. Parse Materials
        materials_sheet = worksheets.get("MATERIALS", [])
        parsed_materials = []
        for r in sheet_to_dicts(materials_sheet):
            mid = r.get("id") or f"MAT_{len(parsed_materials)+1}"
            parsed_materials.append({
                "id": str(mid),
                "name": r.get("name") or str(mid),
                "type": r.get("type", "concrete"),
                "grade": r.get("grade", "C30/37"),
                "elasticModulusE": float(r.get("elasticModulusE", 33.0) or 33.0),
                "poissonRatio": float(r.get("poissonRatio", 0.2) or 0.2),
                "unitWeight": float(r.get("unitWeight", 25.0) or 25.0),
                "compressiveStrengthFc": float(r.get("compressiveStrengthFc", 30.0) or 30.0)
            })

        # 6. Parse Sections
        sections_sheet = worksheets.get("SECTIONS", [])
        parsed_sections = []
        for r in sheet_to_dicts(sections_sheet):
            sec_id = r.get("id") or f"SEC_{len(parsed_sections)+1}"
            w = float(r.get("width", 400.0) or 400.0)
            h = float(r.get("height", 400.0) or 400.0)
            parsed_sections.append({
                "id": str(sec_id),
                "name": r.get("name") or str(sec_id),
                "shape": r.get("shape", "rectangular"),
                "materialId": r.get("materialId", "MAT-C30"),
                "dimensions": {"width": w, "height": h},
                "area": float(r.get("area", 1600.0) or (w * h / 100.0)),
                "momentOfInertiaIxx": float(r.get("momentOfInertiaIxx", 213333.3) or 213333.3),
                "momentOfInertiaIyy": float(r.get("momentOfInertiaIyy", 213333.3) or 213333.3),
                "torsionalConstantJ": float(r.get("torsionalConstantJ", 360000.0) or 360000.0),
                "weightPerMeter": float(r.get("weightPerMeter", 100.0) or 100.0)
            })

        return {
            "projectName": "Excel Imported Model",
            "version": "5.0.0-PRO",
            "units": "kN-m, C",
            "stories": [],
            "materials": parsed_materials or [{
                "id": "MAT-C30",
                "name": "Concrete C30/37",
                "type": "concrete",
                "grade": "C30/37",
                "elasticModulusE": 33.0,
                "poissonRatio": 0.2,
                "unitWeight": 25.0
            }],
            "sections": parsed_sections or [{
                "id": "SEC-COL-400X400",
                "name": "RC 400x400 mm",
                "shape": "rectangular",
                "materialId": "MAT-C30",
                "dimensions": {"width": 400.0, "height": 400.0},
                "area": 1600.0,
                "momentOfInertiaIxx": 213333.3,
                "momentOfInertiaIyy": 213333.3,
                "torsionalConstantJ": 360000.0,
                "weightPerMeter": 100.0
            }],
            "nodes": parsed_nodes,
            "members": parsed_members,
            "slabs": parsed_slabs,
            "walls": parsed_walls
        }

    @staticmethod
    def export_to_excel_xml(model: Dict[str, Any]) -> str:
        """
        Exports full model into an Excel SpreadsheetML XML workbook with 7 formatted worksheets.
        """
        xml_parts: List[str] = []
        xml_parts.append('<?xml version="1.0"?>')
        xml_parts.append('<?mso-application progid="Excel.Sheet"?>')
        xml_parts.append('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"')
        xml_parts.append(' xmlns:o="urn:schemas-microsoft-com:office:office"')
        xml_parts.append(' xmlns:x="urn:schemas-microsoft-com:office:excel"')
        xml_parts.append(' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"')
        xml_parts.append(' xmlns:html="http://www.w3.org/TR/REC-html40">')

        # Styles
        xml_parts.append('<Styles>')
        xml_parts.append(' <Style ss:ID="Header">')
        xml_parts.append('  <Font ss:Bold="1" ss:Color="#FFFFFF"/>')
        xml_parts.append('  <Interior ss:Color="#1E293B" ss:Pattern="Solid"/>')
        xml_parts.append('  <Alignment ss:Horizontal="Center"/>')
        xml_parts.append(' </Style>')
        xml_parts.append(' <Style ss:ID="Data">')
        xml_parts.append('  <Alignment ss:Horizontal="Left"/>')
        xml_parts.append(' </Style>')
        xml_parts.append(' <Style ss:ID="Number">')
        xml_parts.append('  <Alignment ss:Horizontal="Right"/>')
        xml_parts.append(' </Style>')
        xml_parts.append('</Styles>')

        def make_sheet(title: str, headers: List[str], rows: List[List[Any]]):
            xml_parts.append(f'<Worksheet ss:Name="{title}">')
            xml_parts.append(' <Table>')
            # Header row
            xml_parts.append('  <Row>')
            for h in headers:
                xml_parts.append(f'   <Cell ss:StyleID="Header"><Data ss:Type="String">{h}</Data></Cell>')
            xml_parts.append('  </Row>')
            # Data rows
            for r in rows:
                xml_parts.append('  <Row>')
                for cell in r:
                    if isinstance(cell, (int, float)):
                        xml_parts.append(f'   <Cell ss:StyleID="Number"><Data ss:Type="Number">{cell}</Data></Cell>')
                    else:
                        clean_cell = str(cell).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        xml_parts.append(f'   <Cell ss:StyleID="Data"><Data ss:Type="String">{clean_cell}</Data></Cell>')
                xml_parts.append('  </Row>')
            xml_parts.append(' </Table>')
            xml_parts.append('</Worksheet>')

        # 1. Project Info
        make_sheet("PROJECT_INFO",
                   ["Property", "Value"],
                   [
                       ["Project Name", model.get("projectName", "Structure-X Model")],
                       ["Version", model.get("version", "5.0.0-PRO")],
                       ["Units", model.get("units", "kN-m, C")],
                       ["Total Nodes", len(model.get("nodes", []))],
                       ["Total Members", len(model.get("members", []))],
                       ["Total Slabs", len(model.get("slabs", []))],
                       ["Total Walls", len(model.get("walls", []))],
                   ])

        # 2. Nodes
        node_rows = []
        for n in model.get("nodes", []):
            rest = n.get("restraints") or {}
            node_rows.append([
                n.get("id", ""),
                n.get("x", 0.0),
                n.get("y", 0.0),
                n.get("z", 0.0),
                1 if rest.get("translationX") else 0,
                1 if rest.get("translationY") else 0,
                1 if rest.get("translationZ") else 0,
                1 if rest.get("rotationX") else 0,
                1 if rest.get("rotationY") else 0,
                1 if rest.get("rotationZ") else 0
            ])
        make_sheet("NODES",
                   ["id", "x", "y", "z", "restraint_ux", "restraint_uy", "restraint_uz", "restraint_rx", "restraint_ry", "restraint_rz"],
                   node_rows)

        # 3. Members
        mem_rows = []
        for m in model.get("members", []):
            mem_rows.append([
                m.get("id", ""),
                m.get("name", ""),
                m.get("type", "beam"),
                m.get("story", "Story 1"),
                m.get("startNodeId", ""),
                m.get("endNodeId", ""),
                m.get("sectionId", ""),
                m.get("materialId", ""),
                m.get("length", 0.0),
                m.get("releases", "Continuous"),
                m.get("localAxisAngle", 0.0)
            ])
        make_sheet("MEMBERS",
                   ["id", "name", "type", "story", "startNodeId", "endNodeId", "sectionId", "materialId", "length", "releases", "localAxisAngle"],
                   mem_rows)

        # 4. Slabs
        slab_rows = []
        for s in model.get("slabs", []):
            slab_rows.append([
                s.get("id", ""),
                s.get("name", ""),
                s.get("story", "Story 1"),
                ";".join(s.get("nodeIds", [])),
                s.get("thickness", 0.20),
                s.get("materialId", ""),
                s.get("loadDead", 2.5),
                s.get("loadLive", 3.0),
                s.get("diaphragm", "rigid")
            ])
        make_sheet("SLABS",
                   ["id", "name", "story", "nodeIds", "thickness", "materialId", "loadDead", "loadLive", "diaphragm"],
                   slab_rows)

        # 5. Walls
        wall_rows = []
        for w in model.get("walls", []):
            wall_rows.append([
                w.get("id", ""),
                w.get("name", ""),
                w.get("story", "Story 1"),
                ";".join(w.get("nodeIds", [])),
                w.get("thickness", 0.25),
                w.get("materialId", "")
            ])
        make_sheet("WALLS",
                   ["id", "name", "story", "nodeIds", "thickness", "materialId"],
                   wall_rows)

        # 6. Materials
        mat_rows = []
        for m in model.get("materials", []):
            mat_rows.append([
                m.get("id", ""),
                m.get("name", ""),
                m.get("type", "concrete"),
                m.get("grade", ""),
                m.get("elasticModulusE", 33.0),
                m.get("poissonRatio", 0.2),
                m.get("unitWeight", 25.0),
                m.get("compressiveStrengthFc", 30.0)
            ])
        make_sheet("MATERIALS",
                   ["id", "name", "type", "grade", "elasticModulusE", "poissonRatio", "unitWeight", "compressiveStrengthFc"],
                   mat_rows)

        # 7. Sections
        sec_rows = []
        for s in model.get("sections", []):
            dims = s.get("dimensions", {})
            sec_rows.append([
                s.get("id", ""),
                s.get("name", ""),
                s.get("shape", "rectangular"),
                s.get("materialId", ""),
                dims.get("width", 400.0),
                dims.get("height", 400.0),
                s.get("area", 1600.0),
                s.get("momentOfInertiaIxx", 213333.3),
                s.get("momentOfInertiaIyy", 213333.3),
                s.get("torsionalConstantJ", 360000.0),
                s.get("weightPerMeter", 100.0)
            ])
        make_sheet("SECTIONS",
                   ["id", "name", "shape", "materialId", "width", "height", "area", "momentOfInertiaIxx", "momentOfInertiaIyy", "torsionalConstantJ", "weightPerMeter"],
                   sec_rows)

        xml_parts.append('</Workbook>')
        return "\n".join(xml_parts)
