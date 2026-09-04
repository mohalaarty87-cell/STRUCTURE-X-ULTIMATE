"""
STRUCTURE-X ULTIMATE — CSV IMPORT & EXPORT HANDLER (PHASE 13)
High-performance delimited tabular importer and exporter.
Supports multi-section structural CSV files (Nodes, Members, Slabs, Walls, Materials, Sections)
with delimiter auto-detection (comma, semicolon, tab).
"""

import csv
import io
from typing import Dict, Any, List, Optional, Tuple, Set


class CsvHandler:
    """
    Parses and serializes structural model entities to and from CSV tabular formats.
    """

    @staticmethod
    def _detect_delimiter(sample_text: str) -> str:
        for line in sample_text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                if "\t" in line:
                    return "\t"
                if ";" in line:
                    return ";"
                if "," in line:
                    return ","
        return ","

    @staticmethod
    def parse_csv_text(content: str) -> Dict[str, Any]:
        """
        Parses a multi-section CSV file containing blocks like:
        # NODES
        id,x,y,z,...
        # MEMBERS
        id,name,type,startNodeId,endNodeId,sectionId,materialId,...
        # SLABS
        ...
        # MATERIALS
        ...
        # SECTIONS
        ...
        """
        lines = content.splitlines()
        delimiter = CsvHandler._detect_delimiter(content)

        current_section = "NODES" # default if no header
        section_lines: Dict[str, List[str]] = {
            "PROJECT": [],
            "NODES": [],
            "MEMBERS": [],
            "SLABS": [],
            "WALLS": [],
            "MATERIALS": [],
            "SECTIONS": []
        }

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            if trimmed.startswith("#") or trimmed.startswith("//"):
                header_title = trimmed.lstrip("#/").strip().upper()
                for key in section_lines.keys():
                    if key in header_title:
                        current_section = key
                        break
                continue

            section_lines[current_section].append(trimmed)

        # Helper to read CSV rows as dicts
        def read_rows(lines_list: List[str]) -> List[Dict[str, str]]:
            if not lines_list:
                return []
            reader = csv.DictReader(io.StringIO("\n".join(lines_list)), delimiter=delimiter)
            return [dict(r) for r in reader if r]

        # 1. Parse Nodes
        parsed_nodes = []
        for r in read_rows(section_lines["NODES"]):
            nid = r.get("id") or r.get("ID") or r.get("node") or r.get("Node") or f"N_{len(parsed_nodes)+1}"
            try:
                x = float(r.get("x") or r.get("X") or 0.0)
                y = float(r.get("y") or r.get("Y") or 0.0)
                z = float(r.get("z") or r.get("Z") or 0.0)
            except ValueError:
                continue

            restraints = None
            if "restraint_ux" in r or "restraints" in r:
                restraints = {
                    "translationX": r.get("restraint_ux", "0") in ["1", "true", "True"],
                    "translationY": r.get("restraint_uy", "0") in ["1", "true", "True"],
                    "translationZ": r.get("restraint_uz", "0") in ["1", "true", "True"],
                    "rotationX": r.get("restraint_rx", "0") in ["1", "true", "True"],
                    "rotationY": r.get("restraint_ry", "0") in ["1", "true", "True"],
                    "rotationZ": r.get("restraint_rz", "0") in ["1", "true", "True"],
                }

            parsed_nodes.append({
                "id": str(nid),
                "x": x,
                "y": y,
                "z": z,
                "restraints": restraints
            })

        # 2. Parse Members
        parsed_members = []
        for r in read_rows(section_lines["MEMBERS"]):
            mid = r.get("id") or r.get("ID") or f"M_{len(parsed_members)+1}"
            sn = r.get("startNodeId") or r.get("startNode") or r.get("nodeI") or r.get("NodeI") or ""
            en = r.get("endNodeId") or r.get("endNode") or r.get("nodeJ") or r.get("NodeJ") or ""
            mtype = (r.get("type") or r.get("Type") or "beam").lower()
            if mtype not in ["column", "beam", "brace"]:
                mtype = "beam"

            parsed_members.append({
                "id": str(mid),
                "name": r.get("name") or str(mid),
                "type": mtype,
                "story": r.get("story", "Story 1"),
                "startNodeId": str(sn),
                "endNodeId": str(en),
                "sectionId": r.get("sectionId", "SEC-COL-400X400"),
                "materialId": r.get("materialId", "MAT-C30"),
                "releases": r.get("releases", "Continuous"),
                "localAxisAngle": float(r.get("localAxisAngle", 0.0) or 0.0)
            })

        # 3. Parse Slabs
        parsed_slabs = []
        for r in read_rows(section_lines["SLABS"]):
            sid = r.get("id") or r.get("ID") or f"SLAB_{len(parsed_slabs)+1}"
            node_str = r.get("nodeIds") or r.get("nodes") or ""
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
        parsed_walls = []
        for r in read_rows(section_lines["WALLS"]):
            wid = r.get("id") or r.get("ID") or f"WALL_{len(parsed_walls)+1}"
            node_str = r.get("nodeIds") or r.get("nodes") or ""
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
        parsed_materials = []
        for r in read_rows(section_lines["MATERIALS"]):
            mid = r.get("id") or r.get("ID") or f"MAT_{len(parsed_materials)+1}"
            mtype = r.get("type", "concrete")
            parsed_materials.append({
                "id": str(mid),
                "name": r.get("name") or str(mid),
                "type": mtype,
                "grade": r.get("grade", "C30/37"),
                "elasticModulusE": float(r.get("elasticModulusE", 33.0) or 33.0),
                "poissonRatio": float(r.get("poissonRatio", 0.2) or 0.2),
                "unitWeight": float(r.get("unitWeight", 25.0) or 25.0),
                "compressiveStrengthFc": float(r.get("compressiveStrengthFc", 30.0) or 30.0)
            })

        # 6. Parse Sections
        parsed_sections = []
        for r in read_rows(section_lines["SECTIONS"]):
            sec_id = r.get("id") or r.get("ID") or f"SEC_{len(parsed_sections)+1}"
            shape = r.get("shape", "rectangular")
            w = float(r.get("width", 400.0) or 400.0)
            h = float(r.get("height", 400.0) or 400.0)
            area = float(r.get("area", 1600.0) or (w * h / 100.0))
            ixx = float(r.get("momentOfInertiaIxx", 213333.3) or 213333.3)
            iyy = float(r.get("momentOfInertiaIyy", 213333.3) or 213333.3)

            parsed_sections.append({
                "id": str(sec_id),
                "name": r.get("name") or str(sec_id),
                "shape": shape,
                "materialId": r.get("materialId", "MAT-C30"),
                "dimensions": {"width": w, "height": h},
                "area": area,
                "momentOfInertiaIxx": ixx,
                "momentOfInertiaIyy": iyy,
                "torsionalConstantJ": float(r.get("torsionalConstantJ", 360000.0) or 360000.0),
                "weightPerMeter": float(r.get("weightPerMeter", 100.0) or 100.0)
            })

        return {
            "projectName": "CSV Imported Model",
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
    def export_to_csv(model: Dict[str, Any], delimiter: str = ",") -> str:
        """
        Exports full structural model into a standardized multi-section CSV string.
        """
        output = io.StringIO()

        # Header
        output.write("# PROJECT\n")
        output.write(f"projectName{delimiter}version{delimiter}units\n")
        output.write(f"{model.get('projectName', 'Model')}{delimiter}{model.get('version', '5.0.0')}{delimiter}{model.get('units', 'kN-m, C')}\n\n")

        # Materials
        output.write("# MATERIALS\n")
        mat_cols = ["id", "name", "type", "grade", "elasticModulusE", "poissonRatio", "unitWeight", "compressiveStrengthFc"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(mat_cols)
        for m in model.get("materials", []):
            writer.writerow([
                m.get("id", ""),
                m.get("name", ""),
                m.get("type", "concrete"),
                m.get("grade", ""),
                m.get("elasticModulusE", 33.0),
                m.get("poissonRatio", 0.2),
                m.get("unitWeight", 25.0),
                m.get("compressiveStrengthFc", 30.0)
            ])
        output.write("\n")

        # Sections
        output.write("# SECTIONS\n")
        sec_cols = ["id", "name", "shape", "materialId", "width", "height", "area", "momentOfInertiaIxx", "momentOfInertiaIyy", "torsionalConstantJ", "weightPerMeter"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(sec_cols)
        for s in model.get("sections", []):
            dims = s.get("dimensions", {})
            writer.writerow([
                s.get("id", ""),
                s.get("name", ""),
                s.get("shape", "rectangular"),
                s.get("materialId", "MAT-C30"),
                dims.get("width", 400.0),
                dims.get("height", 400.0),
                s.get("area", 1600.0),
                s.get("momentOfInertiaIxx", 213333.3),
                s.get("momentOfInertiaIyy", 213333.3),
                s.get("torsionalConstantJ", 360000.0),
                s.get("weightPerMeter", 100.0)
            ])
        output.write("\n")

        # Nodes
        output.write("# NODES\n")
        node_cols = ["id", "x", "y", "z", "restraint_ux", "restraint_uy", "restraint_uz", "restraint_rx", "restraint_ry", "restraint_rz"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(node_cols)
        for n in model.get("nodes", []):
            rest = n.get("restraints") or {}
            writer.writerow([
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
        output.write("\n")

        # Members
        output.write("# MEMBERS\n")
        mem_cols = ["id", "name", "type", "story", "startNodeId", "endNodeId", "sectionId", "materialId", "length", "releases", "localAxisAngle"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(mem_cols)
        for m in model.get("members", []):
            writer.writerow([
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
        output.write("\n")

        # Slabs
        output.write("# SLABS\n")
        slab_cols = ["id", "name", "story", "nodeIds", "thickness", "materialId", "loadDead", "loadLive", "diaphragm"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(slab_cols)
        for s in model.get("slabs", []):
            writer.writerow([
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
        output.write("\n")

        # Walls
        output.write("# WALLS\n")
        wall_cols = ["id", "name", "story", "nodeIds", "thickness", "materialId"]
        writer = csv.writer(output, delimiter=delimiter)
        writer.writerow(wall_cols)
        for w in model.get("walls", []):
            writer.writerow([
                w.get("id", ""),
                w.get("name", ""),
                w.get("story", "Story 1"),
                ";".join(w.get("nodeIds", [])),
                w.get("thickness", 0.25),
                w.get("materialId", "")
            ])

        return output.getvalue()
