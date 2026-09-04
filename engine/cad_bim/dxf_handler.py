"""
STRUCTURE-X ULTIMATE — DXF IMPORT & EXPORT HANDLER (PHASE 13)
AutoCAD ASCII Drawing Exchange Format (DXF R12 / R2000) parser and generator.
Supports LINE, 3DFACE, POINT, POLYLINE, LWPOLYLINE, TEXT with layer-based classification.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Set
from .types import (
    InteropFormat,
    ImportPreviewSummary,
    EntityCounts,
    BoundingBox3D,
    LayerInfo,
)


class DxfHandler:
    """
    Parses and serializes standard AutoCAD DXF files with full 3D geometry preservation.
    """

    @staticmethod
    def parse_dxf_text(content: str) -> Dict[str, Any]:
        """
        Parses ASCII DXF string using group code / value pairs.
        Extracts LINE, 3DFACE, POINT, POLYLINE, LWPOLYLINE and layers.
        """
        lines = content.splitlines()
        pairs: List[Tuple[int, str]] = []

        # Read group code and value pairs
        i = 0
        n_lines = len(lines)
        while i + 1 < n_lines:
            try:
                code_str = lines[i].strip()
                val_str = lines[i+1].strip()
                if code_str:
                    code = int(code_str)
                    pairs.append((code, val_str))
            except ValueError:
                pass
            i += 2

        # Layer definitions table
        layers_map: Dict[str, Dict[str, Any]] = {}
        in_tables = False
        in_entities = False

        idx = 0
        total_pairs = len(pairs)

        extracted_nodes: List[Dict[str, Any]] = []
        node_lookup: Dict[Tuple[float, float, float], str] = {}
        extracted_members: List[Dict[str, Any]] = []
        extracted_slabs: List[Dict[str, Any]] = []
        extracted_walls: List[Dict[str, Any]] = []

        def get_or_create_node(pt: Tuple[float, float, float]) -> str:
            key = (round(pt[0], 4), round(pt[1], 4), round(pt[2], 4))
            if key in node_lookup:
                return node_lookup[key]
            nid = f"N_DXF_{len(extracted_nodes) + 1}"
            node_lookup[key] = nid
            extracted_nodes.append({
                "id": nid,
                "x": key[0],
                "y": key[1],
                "z": key[2]
            })
            return nid

        # Scan pairs
        while idx < total_pairs:
            code, val = pairs[idx]

            if code == 0 and val == "SECTION":
                idx += 1
                if idx < total_pairs and pairs[idx][0] == 2:
                    sec_name = pairs[idx][1].upper()
                    if sec_name == "TABLES":
                        in_tables = True
                        in_entities = False
                    elif sec_name == "ENTITIES":
                        in_entities = True
                        in_tables = False
                idx += 1
                continue

            elif code == 0 and val == "ENDSEC":
                in_tables = False
                in_entities = False
                idx += 1
                continue

            # Parse Layers in TABLES
            if in_tables and code == 0 and val == "LAYER":
                layer_name = "0"
                color_num = 7
                idx += 1
                while idx < total_pairs and pairs[idx][0] != 0:
                    lcode, lval = pairs[idx]
                    if lcode == 2:
                        layer_name = lval
                    elif lcode == 62:
                        try:
                            color_num = int(lval)
                        except ValueError:
                            pass
                    idx += 1
                layers_map[layer_name] = {"name": layer_name, "color": color_num}
                continue

            # Parse Entities in ENTITIES
            if in_entities and code == 0:
                ent_type = val.upper()
                idx += 1

                # 1. LINE (Frame elements: beams, columns, braces)
                if ent_type == "LINE":
                    layer = "0"
                    x1 = y1 = z1 = 0.0
                    x2 = y2 = z2 = 0.0

                    while idx < total_pairs and pairs[idx][0] != 0:
                        ecode, evalue = pairs[idx]
                        try:
                            if ecode == 8:
                                layer = evalue
                            elif ecode == 10:
                                x1 = float(evalue)
                            elif ecode == 20:
                                y1 = float(evalue)
                            elif ecode == 30:
                                z1 = float(evalue)
                            elif ecode == 11:
                                x2 = float(evalue)
                            elif ecode == 21:
                                y2 = float(evalue)
                            elif ecode == 31:
                                z2 = float(evalue)
                        except ValueError:
                            pass
                        idx += 1

                    # Check length
                    length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
                    if length > 1e-4:
                        sn = get_or_create_node((x1, y1, z1))
                        en = get_or_create_node((x2, y2, z2))

                        # Auto-detect element type from verticality and layer name
                        l_lower = layer.lower()
                        dz = abs(z2 - z1)
                        dxy = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                        if any(k in l_lower for k in ["col", "vert", "pillar"]):
                            elem_type = "column"
                        elif any(k in l_lower for k in ["brace", "diag"]):
                            elem_type = "brace"
                        elif any(k in l_lower for k in ["beam", "girder", "joist"]):
                            elem_type = "beam"
                        else:
                            elem_type = "column" if dz > dxy * 1.5 else "beam"

                        mid = f"M_DXF_{len(extracted_members) + 1}"
                        extracted_members.append({
                            "id": mid,
                            "name": f"{elem_type.upper()}_{len(extracted_members) + 1}",
                            "type": elem_type,
                            "story": "Story 1",
                            "startNodeId": sn,
                            "endNodeId": en,
                            "sectionId": "SEC-COL-400X400",
                            "materialId": "MAT-C30",
                            "length": round(length, 4),
                            "releases": "Continuous",
                            "localAxisAngle": 0.0,
                            "layer": layer
                        })
                    continue

                # 2. 3DFACE (Planar Slabs or Shear Walls)
                elif ent_type == "3DFACE":
                    layer = "0"
                    pts: List[Tuple[float, float, float]] = []
                    coords = {10: 0.0, 20: 0.0, 30: 0.0,
                              11: 0.0, 21: 0.0, 31: 0.0,
                              12: 0.0, 22: 0.0, 32: 0.0,
                              13: 0.0, 23: 0.0, 33: 0.0}

                    while idx < total_pairs and pairs[idx][0] != 0:
                        ecode, evalue = pairs[idx]
                        if ecode == 8:
                            layer = evalue
                        elif ecode in coords:
                            try:
                                coords[ecode] = float(evalue)
                            except ValueError:
                                pass
                        idx += 1

                    p1 = (coords[10], coords[20], coords[30])
                    p2 = (coords[11], coords[21], coords[31])
                    p3 = (coords[12], coords[22], coords[32])
                    p4 = (coords[13], coords[23], coords[33])

                    face_pts = [p1, p2, p3]
                    # Check if 4th vertex is unique or just repeated 3rd vertex
                    if abs(p4[0]-p3[0]) > 1e-4 or abs(p4[1]-p3[1]) > 1e-4 or abs(p4[2]-p3[2]) > 1e-4:
                        face_pts.append(p4)

                    face_node_ids = [get_or_create_node(p) for p in face_pts]

                    # Distinguish Wall vs Slab
                    l_lower = layer.lower()
                    is_wall = any(k in l_lower for k in ["wall", "shear"]) or (abs(p1[2] - p3[2]) > 1.0)

                    if is_wall:
                        wid = f"WALL_DXF_{len(extracted_walls) + 1}"
                        extracted_walls.append({
                            "id": wid,
                            "name": f"WALL_{len(extracted_walls) + 1}",
                            "story": "Story 1",
                            "nodeIds": face_node_ids,
                            "thickness": 0.25,
                            "materialId": "MAT-C30",
                            "layer": layer
                        })
                    else:
                        sid = f"SLAB_DXF_{len(extracted_slabs) + 1}"
                        extracted_slabs.append({
                            "id": sid,
                            "name": f"SLAB_{len(extracted_slabs) + 1}",
                            "story": "Story 1",
                            "nodeIds": face_node_ids,
                            "thickness": 0.20,
                            "materialId": "MAT-C30",
                            "loadDead": 2.5,
                            "loadLive": 3.0,
                            "diaphragm": "rigid",
                            "layer": layer
                        })
                    continue

                # 3. POINT (Joint coordinates)
                elif ent_type == "POINT":
                    layer = "0"
                    px = py = pz = 0.0
                    while idx < total_pairs and pairs[idx][0] != 0:
                        ecode, evalue = pairs[idx]
                        try:
                            if ecode == 8:
                                layer = evalue
                            elif ecode == 10:
                                px = float(evalue)
                            elif ecode == 20:
                                py = float(evalue)
                            elif ecode == 30:
                                pz = float(evalue)
                        except ValueError:
                            pass
                        idx += 1
                    get_or_create_node((px, py, pz))
                    continue

                # 4. POLYLINE / LWPOLYLINE
                elif ent_type in ["LWPOLYLINE", "POLYLINE"]:
                    layer = "0"
                    poly_pts: List[Tuple[float, float, float]] = []
                    cx = cy = cz = 0.0

                    while idx < total_pairs and pairs[idx][0] != 0:
                        ecode, evalue = pairs[idx]
                        try:
                            if ecode == 8:
                                layer = evalue
                            elif ecode == 10:
                                cx = float(evalue)
                            elif ecode == 20:
                                cy = float(evalue)
                                poly_pts.append((cx, cy, cz))
                            elif ecode == 38:
                                cz = float(evalue)
                        except ValueError:
                            pass
                        idx += 1

                    if len(poly_pts) >= 3:
                        poly_nids = [get_or_create_node(p) for p in poly_pts]
                        sid = f"SLAB_DXF_{len(extracted_slabs) + 1}"
                        extracted_slabs.append({
                            "id": sid,
                            "name": f"SLAB_{len(extracted_slabs) + 1}",
                            "story": "Story 1",
                            "nodeIds": poly_nids,
                            "thickness": 0.20,
                            "materialId": "MAT-C30",
                            "layer": layer
                        })
                    continue

            idx += 1

        # Default Materials & Sections
        materials = [{
            "id": "MAT-C30",
            "name": "Concrete C30/37",
            "type": "concrete",
            "grade": "C30/37",
            "elasticModulusE": 33.0,
            "poissonRatio": 0.2,
            "unitWeight": 25.0,
            "color": "#9ca3af"
        }]

        sections = [{
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
        }]

        return {
            "projectName": "DXF Imported Model",
            "version": "5.0.0-PRO",
            "units": "kN-m, C",
            "stories": [],
            "materials": materials,
            "sections": sections,
            "nodes": extracted_nodes,
            "members": extracted_members,
            "slabs": extracted_slabs,
            "walls": extracted_walls,
            "metadata": {
                "layers": list(layers_map.values())
            }
        }

    @staticmethod
    def export_to_dxf(model: Dict[str, Any]) -> str:
        """
        Serializes a StructuralModel into an AutoCAD ASCII DXF (R12/2000 compliant).
        Outputs distinct layers: COLUMNS, BEAMS, BRACES, SLABS, WALLS, JOINTS, TEXT.
        """
        lines: List[str] = []

        def add_code(code: int, value: Any):
            lines.append(str(code))
            lines.append(str(value))

        # 1. HEADER SECTION
        add_code(0, "SECTION")
        add_code(2, "HEADER")
        add_code(9, "$ACADVER")
        add_code(1, "AC1009") # AutoCAD R12 ASCII (maximum compatibility)
        add_code(9, "$INSUNITS")
        add_code(70, 6) # Meters
        add_code(0, "ENDSEC")

        # 2. TABLES SECTION (Layers)
        add_code(0, "SECTION")
        add_code(2, "TABLES")
        add_code(0, "TABLE")
        add_code(2, "LAYER")
        add_code(70, 7)

        # Standard Structural Layers: name, color index
        layer_defs = [
            ("COLUMNS", 4),    # Cyan
            ("BEAMS", 1),      # Red
            ("BRACES", 2),     # Yellow
            ("SLABS", 3),      # Green
            ("WALLS", 6),      # Magenta
            ("JOINTS", 7),     # White
            ("LABELS", 8),     # Gray
        ]

        for lname, color in layer_defs:
            add_code(0, "LAYER")
            add_code(2, lname)
            add_code(70, 0)
            add_code(62, color)
            add_code(6, "CONTINUOUS")

        add_code(0, "ENDTAB")
        add_code(0, "ENDSEC")

        # 3. ENTITIES SECTION
        add_code(0, "SECTION")
        add_code(2, "ENTITIES")

        # Nodes Lookup
        node_map: Dict[str, Tuple[float, float, float]] = {}
        for n in model.get("nodes", []):
            nid = n.get("id")
            x = float(n.get("x", 0.0))
            y = float(n.get("y", 0.0))
            z = float(n.get("z", 0.0))
            node_map[nid] = (x, y, z)

            # Export POINT entity for each joint
            add_code(0, "POINT")
            add_code(8, "JOINTS")
            add_code(10, x)
            add_code(20, y)
            add_code(30, z)

        # Export LINE entities for Members
        for mem in model.get("members", []):
            sn = mem.get("startNodeId")
            en = mem.get("endNodeId")
            if sn not in node_map or en not in node_map:
                continue

            p1 = node_map[sn]
            p2 = node_map[en]
            mtype = mem.get("type", "beam")

            layer_name = "BEAMS"
            if mtype == "column":
                layer_name = "COLUMNS"
            elif mtype == "brace":
                layer_name = "BRACES"

            add_code(0, "LINE")
            add_code(8, layer_name)
            add_code(10, p1[0])
            add_code(20, p1[1])
            add_code(30, p1[2])
            add_code(11, p2[0])
            add_code(21, p2[1])
            add_code(31, p2[2])

            # Member Label at Midpoint
            mid_x = (p1[0] + p2[0]) / 2.0
            mid_y = (p1[1] + p2[1]) / 2.0
            mid_z = (p1[2] + p2[2]) / 2.0
            m_name = mem.get("name", mem.get("id", ""))

            add_code(0, "TEXT")
            add_code(8, "LABELS")
            add_code(10, mid_x)
            add_code(20, mid_y)
            add_code(30, mid_z)
            add_code(40, 0.15) # text height 150mm
            add_code(1, m_name)

        # Export 3DFACE for Slabs
        for slab in model.get("slabs", []):
            nids = slab.get("nodeIds", [])
            valid_pts = [node_map[nid] for nid in nids if nid in node_map]
            if len(valid_pts) >= 3:
                p1 = valid_pts[0]
                p2 = valid_pts[1]
                p3 = valid_pts[2]
                p4 = valid_pts[3] if len(valid_pts) >= 4 else valid_pts[2]

                add_code(0, "3DFACE")
                add_code(8, "SLABS")
                add_code(10, p1[0])
                add_code(20, p1[1])
                add_code(30, p1[2])
                add_code(11, p2[0])
                add_code(21, p2[1])
                add_code(31, p2[2])
                add_code(12, p3[0])
                add_code(22, p3[1])
                add_code(32, p3[2])
                add_code(13, p4[0])
                add_code(23, p4[1])
                add_code(33, p4[2])

        # Export 3DFACE for Walls
        for wall in model.get("walls", []):
            nids = wall.get("nodeIds", [])
            valid_pts = [node_map[nid] for nid in nids if nid in node_map]
            if len(valid_pts) >= 3:
                p1 = valid_pts[0]
                p2 = valid_pts[1]
                p3 = valid_pts[2]
                p4 = valid_pts[3] if len(valid_pts) >= 4 else valid_pts[2]

                add_code(0, "3DFACE")
                add_code(8, "WALLS")
                add_code(10, p1[0])
                add_code(20, p1[1])
                add_code(30, p1[2])
                add_code(11, p2[0])
                add_code(21, p2[1])
                add_code(31, p2[2])
                add_code(12, p3[0])
                add_code(22, p3[1])
                add_code(32, p3[2])
                add_code(13, p4[0])
                add_code(23, p4[1])
                add_code(33, p4[2])

        add_code(0, "ENDSEC")
        add_code(0, "EOF")

        return "\n".join(lines)
