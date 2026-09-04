"""
STRUCTURE-X ULTIMATE — CAD & BIM INTEROP MAPPER (PHASE 13)
Transforms coordinates, maps layers to structural types, standardizes materials/sections,
resolves node coincidences, and performs non-destructive project integration.
"""

import math
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from .types import (
    MappingConfig,
    CoordinateTransform,
    MergeStrategy,
    BoundingBox3D,
    EntityCounts,
    LayerInfo,
    ImportPreviewSummary,
    InteropFormat,
)


class InteropMapper:
    """
    Handles coordinate scaling/offsets, layer-to-type rules, section/material mapping,
    and deduplication for structural CAD/BIM import.
    """

    @staticmethod
    def transform_point(
        x: float,
        y: float,
        z: float,
        transform: CoordinateTransform
    ) -> Tuple[float, float, float]:
        """
        Applies scaling, translation, and axis swapping to 3D Cartesian coordinates.
        """
        # 1. Scale
        xs = x * transform.scale_factor
        ys = y * transform.scale_factor
        zs = z * transform.scale_factor

        # 2. Swap Y and Z if requested (e.g. from Y-up CAD to Z-up BIM/Structural)
        if transform.swap_yz:
            ys, zs = zs, ys

        if transform.invert_z:
            zs = -zs

        # 3. Offsets
        xt = xs + transform.offset_x
        yt = ys + transform.offset_y
        zt = zs + transform.offset_z

        return (round(xt, 5), round(yt, 5), round(zt, 5))

    @staticmethod
    def compute_bounding_box(nodes: List[Dict[str, Any]]) -> BoundingBox3D:
        if not nodes:
            return BoundingBox3D()

        xs = [float(n.get("x", 0.0)) for n in nodes]
        ys = [float(n.get("y", 0.0)) for n in nodes]
        zs = [float(n.get("z", 0.0)) for n in nodes]

        return BoundingBox3D(
            min_x=min(xs), max_x=max(xs),
            min_y=min(ys), max_y=max(ys),
            min_z=min(zs), max_z=max(zs)
        )

    @staticmethod
    def apply_mapping_and_transform(
        raw_data: Dict[str, Any],
        config: MappingConfig
    ) -> Dict[str, Any]:
        """
        Transforms raw imported data into a normalized, fully-mapped StructuralModel dict.
        """
        transformed_data: Dict[str, Any] = {
            "projectName": raw_data.get("projectName", "Imported Model"),
            "version": "5.0.0-PRO",
            "units": raw_data.get("units", "kN-m, C"),
            "stories": list(raw_data.get("stories", [])),
            "gridLinesX": list(raw_data.get("gridLinesX", [])),
            "gridLinesY": list(raw_data.get("gridLinesY", [])),
            "materials": list(raw_data.get("materials", [])),
            "sections": list(raw_data.get("sections", [])),
            "nodes": [],
            "members": [],
            "slabs": [],
            "walls": [],
            "openings": list(raw_data.get("openings", [])),
            "links": list(raw_data.get("links", [])),
            "springs": list(raw_data.get("springs", [])),
            "diaphragms": list(raw_data.get("diaphragms", [])),
            "metadata": dict(raw_data.get("metadata", {}))
        }

        # 1. Transform Nodes and deduplicate within tolerance
        raw_nodes = raw_data.get("nodes", [])
        tol = max(config.tolerance_m, 1e-4)

        # Coordinate bucketing for deduplication
        coord_map: Dict[Tuple[int, int, int], str] = {}
        node_id_remap: Dict[str, str] = {}
        unique_nodes: List[Dict[str, Any]] = []

        for node in raw_nodes:
            old_id = str(node.get("id"))
            try:
                ox = float(node.get("x", 0.0))
                oy = float(node.get("y", 0.0))
                oz = float(node.get("z", 0.0))
            except (ValueError, TypeError):
                continue

            tx, ty, tz = InteropMapper.transform_point(ox, oy, oz, config.coordinate_transform)

            bx = int(round(tx / tol))
            by = int(round(ty / tol))
            bz = int(round(tz / tol))

            # Look for existing coincident node
            matched_id: Optional[str] = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        k = (bx + dx, by + dy, bz + dz)
                        if k in coord_map:
                            cand_id = coord_map[k]
                            # Find cand node coordinates
                            cand_node = next((n for n in unique_nodes if n["id"] == cand_id), None)
                            if cand_node:
                                dist = math.sqrt((tx - cand_node["x"])**2 + (ty - cand_node["y"])**2 + (tz - cand_node["z"])**2)
                                if dist <= tol:
                                    matched_id = cand_id
                                    break
                    if matched_id:
                        break
                if matched_id:
                    break

            if matched_id:
                node_id_remap[old_id] = matched_id
            else:
                new_node = dict(node)
                new_node["x"] = tx
                new_node["y"] = ty
                new_node["z"] = tz
                unique_nodes.append(new_node)
                coord_map[(bx, by, bz)] = old_id
                node_id_remap[old_id] = old_id

        transformed_data["nodes"] = unique_nodes

        # 2. Materials & Sections Normalization
        mat_id_set = {m["id"] for m in transformed_data["materials"]}
        sec_id_set = {s["id"] for s in transformed_data["sections"]}

        # Add default material if missing
        if config.default_material_id not in mat_id_set:
            transformed_data["materials"].append({
                "id": config.default_material_id,
                "name": "Concrete C30/37 (Default)",
                "type": "concrete",
                "grade": "C30/37",
                "elasticModulusE": 33.0,
                "poissonRatio": 0.2,
                "unitWeight": 25.0,
                "compressiveStrengthFc": 30.0,
                "color": "#9ca3af"
            })
            mat_id_set.add(config.default_material_id)

        # Add default section if missing
        if config.default_section_id not in sec_id_set:
            transformed_data["sections"].append({
                "id": config.default_section_id,
                "name": "RC 400x400 mm",
                "shape": "rectangular",
                "materialId": config.default_material_id,
                "dimensions": {
                    "width": 400.0,
                    "height": 400.0
                },
                "area": 1600.0,
                "momentOfInertiaIxx": 213333.3,
                "momentOfInertiaIyy": 213333.3,
                "torsionalConstantJ": 360000.0,
                "weightPerMeter": 100.0
            })
            sec_id_set.add(config.default_section_id)

        # 3. Transform Members (re-link to remapped nodes, map layer to type, map section/material)
        raw_members = raw_data.get("members", [])
        for m in raw_members:
            old_sn = str(m.get("startNodeId", ""))
            old_en = str(m.get("endNodeId", ""))
            new_sn = node_id_remap.get(old_sn, old_sn)
            new_en = node_id_remap.get(old_en, old_en)

            # Skip members whose endpoints collapsed to same node after deduplication
            if new_sn == new_en:
                continue

            new_m = dict(m)
            new_m["startNodeId"] = new_sn
            new_m["endNodeId"] = new_en

            # Layer type mapping
            layer = str(m.get("layer", "")).strip()
            if layer in config.layer_type_map:
                new_m["type"] = config.layer_type_map[layer]
            elif "type" not in new_m or not new_m["type"]:
                # Auto-detect column vs beam based on verticality
                n1 = next((n for n in unique_nodes if n["id"] == new_sn), None)
                n2 = next((n for n in unique_nodes if n["id"] == new_en), None)
                if n1 and n2:
                    dz = abs(n2["z"] - n1["z"])
                    dxy = math.sqrt((n2["x"] - n1["x"])**2 + (n2["y"] - n1["y"])**2)
                    new_m["type"] = "column" if dz > dxy * 1.5 else "beam"
                else:
                    new_m["type"] = "beam"

            # Section mapping
            cur_sec = str(new_m.get("sectionId", ""))
            if cur_sec in config.section_map:
                new_m["sectionId"] = config.section_map[cur_sec]
            elif cur_sec not in sec_id_set:
                new_m["sectionId"] = config.default_section_id

            # Material mapping
            cur_mat = str(new_m.get("materialId", ""))
            if cur_mat in config.material_map:
                new_m["materialId"] = config.material_map[cur_mat]
            elif cur_mat not in mat_id_set:
                new_m["materialId"] = config.default_material_id

            # Recalculate length in target units
            n1 = next((n for n in unique_nodes if n["id"] == new_sn), None)
            n2 = next((n for n in unique_nodes if n["id"] == new_en), None)
            if n1 and n2:
                new_m["length"] = round(math.sqrt((n2["x"] - n1["x"])**2 + (n2["y"] - n1["y"])**2 + (n2["z"] - n1["z"])**2), 4)

            # Preserve properties
            if "releases" not in new_m:
                new_m["releases"] = "Continuous"
            if "localAxisAngle" not in new_m:
                new_m["localAxisAngle"] = 0.0

            transformed_data["members"].append(new_m)

        # 4. Transform Slabs
        raw_slabs = raw_data.get("slabs", [])
        for s in raw_slabs:
            old_nids = [str(nid) for nid in s.get("nodeIds", [])]
            new_nids = [node_id_remap.get(nid, nid) for nid in old_nids]

            # Deduplicate sequential identical nodes
            dedup_nids: List[str] = []
            for nid in new_nids:
                if not dedup_nids or dedup_nids[-1] != nid:
                    dedup_nids.append(nid)
            if len(dedup_nids) > 1 and dedup_nids[0] == dedup_nids[-1]:
                dedup_nids.pop()

            if len(dedup_nids) < 3:
                continue

            new_s = dict(s)
            new_s["nodeIds"] = dedup_nids

            # Material mapping
            cur_mat = str(new_s.get("materialId", ""))
            if cur_mat in config.material_map:
                new_s["materialId"] = config.material_map[cur_mat]
            elif cur_mat not in mat_id_set:
                new_s["materialId"] = config.default_material_id

            if "thickness" not in new_s:
                new_s["thickness"] = 0.20

            transformed_data["slabs"].append(new_s)

        # 5. Transform Walls
        raw_walls = raw_data.get("walls", [])
        for w in raw_walls:
            old_nids = [str(nid) for nid in w.get("nodeIds", [])]
            new_nids = [node_id_remap.get(nid, nid) for nid in old_nids]
            if len(new_nids) >= 3:
                new_w = dict(w)
                new_w["nodeIds"] = new_nids
                cur_mat = str(new_w.get("materialId", ""))
                if cur_mat in config.material_map:
                    new_w["materialId"] = config.material_map[cur_mat]
                elif cur_mat not in mat_id_set:
                    new_w["materialId"] = config.default_material_id
                transformed_data["walls"].append(new_w)

        # 6. Auto-generate stories if model has nodes but no stories
        if not transformed_data["stories"] and transformed_data["nodes"]:
            z_levels = sorted(list({round(n["z"], 2) for n in transformed_data["nodes"] if n["z"] > 0.05}))
            if not z_levels:
                z_levels = [3.5]
            stories = []
            prev_elev = 0.0
            for idx, elev in enumerate(z_levels):
                height = elev - prev_elev
                stories.append({
                    "id": f"STORY_{idx+1}",
                    "name": f"Story {idx+1}",
                    "elevation": elev,
                    "height": round(height, 3)
                })
                prev_elev = elev
            transformed_data["stories"] = stories

        return transformed_data

    @staticmethod
    def merge_into_existing_project(
        existing_project: Dict[str, Any],
        imported_data: Dict[str, Any],
        strategy: MergeStrategy = MergeStrategy.MERGE_APPEND,
        tolerance_m: float = 0.001
    ) -> Dict[str, Any]:
        """
        Safely merges imported data into existing project without corrupting existing data.
        Guarantees existing entities are preserved and non-conflicting IDs are generated.
        """
        if strategy == MergeStrategy.REPLACE:
            # Preserve project-level metadata if requested
            merged = dict(imported_data)
            merged["projectName"] = existing_project.get("projectName", imported_data.get("projectName"))
            return merged

        # Deep clone existing project
        merged = {
            "projectName": existing_project.get("projectName", "Structure-X Project"),
            "version": existing_project.get("version", "5.0.0-PRO"),
            "units": existing_project.get("units", "kN-m, C"),
            "stories": list(existing_project.get("stories", [])),
            "gridLinesX": list(existing_project.get("gridLinesX", [])),
            "gridLinesY": list(existing_project.get("gridLinesY", [])),
            "materials": list(existing_project.get("materials", [])),
            "sections": list(existing_project.get("sections", [])),
            "nodes": list(existing_project.get("nodes", [])),
            "members": list(existing_project.get("members", [])),
            "slabs": list(existing_project.get("slabs", [])),
            "walls": list(existing_project.get("walls", [])),
            "openings": list(existing_project.get("openings", [])),
            "links": list(existing_project.get("links", [])),
            "springs": list(existing_project.get("springs", [])),
            "diaphragms": list(existing_project.get("diaphragms", [])),
            "metadata": dict(existing_project.get("metadata", {}))
        }

        # 1. Existing ID registries
        existing_node_ids = {n["id"] for n in merged["nodes"]}
        existing_member_ids = {m["id"] for m in merged["members"]}
        existing_slab_ids = {s["id"] for s in merged["slabs"]}
        existing_wall_ids = {w["id"] for w in merged["walls"]}
        existing_mat_ids = {m["id"] for m in merged["materials"]}
        existing_sec_ids = {s["id"] for s in merged["sections"]}

        # 2. Merge Materials (append unique)
        for mat in imported_data.get("materials", []):
            if mat["id"] not in existing_mat_ids:
                merged["materials"].append(dict(mat))
                existing_mat_ids.add(mat["id"])

        # 3. Merge Sections (append unique)
        for sec in imported_data.get("sections", []):
            if sec["id"] not in existing_sec_ids:
                merged["sections"].append(dict(sec))
                existing_sec_ids.add(sec["id"])

        # 4. Node Re-mapping & Merging
        imported_node_remap: Dict[str, str] = {}
        for imp_node in imported_data.get("nodes", []):
            old_id = imp_node["id"]
            ix, iy, iz = imp_node["x"], imp_node["y"], imp_node["z"]

            matched_existing: Optional[str] = None
            if strategy == MergeStrategy.MERGE_UPDATE:
                # Find coincident existing node
                for ex_node in merged["nodes"]:
                    dist = math.sqrt((ix - ex_node["x"])**2 + (iy - ex_node["y"])**2 + (iz - ex_node["z"])**2)
                    if dist <= tolerance_m:
                        matched_existing = ex_node["id"]
                        break

            if matched_existing:
                imported_node_remap[old_id] = matched_existing
            else:
                # Assign non-colliding ID if collision occurs
                new_id = old_id
                if new_id in existing_node_ids:
                    count = 1
                    while f"{old_id}_imp{count}" in existing_node_ids:
                        count += 1
                    new_id = f"{old_id}_imp{count}"

                new_node = dict(imp_node)
                new_node["id"] = new_id
                merged["nodes"].append(new_node)
                existing_node_ids.add(new_id)
                imported_node_remap[old_id] = new_id

        # 5. Merge Members
        for imp_mem in imported_data.get("members", []):
            old_mid = imp_mem["id"]
            new_mid = old_mid
            if new_mid in existing_member_ids:
                count = 1
                while f"{old_mid}_imp{count}" in existing_member_ids:
                    count += 1
                new_mid = f"{old_mid}_imp{count}"

            new_mem = dict(imp_mem)
            new_mem["id"] = new_mid
            new_mem["startNodeId"] = imported_node_remap.get(imp_mem["startNodeId"], imp_mem["startNodeId"])
            new_mem["endNodeId"] = imported_node_remap.get(imp_mem["endNodeId"], imp_mem["endNodeId"])

            if new_mem["startNodeId"] != new_mem["endNodeId"]:
                merged["members"].append(new_mem)
                existing_member_ids.add(new_mid)

        # 6. Merge Slabs
        for imp_slab in imported_data.get("slabs", []):
            old_sid = imp_slab["id"]
            new_sid = old_sid
            if new_sid in existing_slab_ids:
                count = 1
                while f"{old_sid}_imp{count}" in existing_slab_ids:
                    count += 1
                new_sid = f"{old_sid}_imp{count}"

            new_slab = dict(imp_slab)
            new_slab["id"] = new_sid
            new_slab["nodeIds"] = [imported_node_remap.get(nid, nid) for nid in imp_slab.get("nodeIds", [])]
            if len(new_slab["nodeIds"]) >= 3:
                merged["slabs"].append(new_slab)
                existing_slab_ids.add(new_sid)

        # 7. Merge Walls
        for imp_wall in imported_data.get("walls", []):
            old_wid = imp_wall["id"]
            new_wid = old_wid
            if new_wid in existing_wall_ids:
                count = 1
                while f"{old_wid}_imp{count}" in existing_wall_ids:
                    count += 1
                new_wid = f"{old_wid}_imp{count}"

            new_wall = dict(imp_wall)
            new_wall["id"] = new_wid
            new_wall["nodeIds"] = [imported_node_remap.get(nid, nid) for nid in imp_wall.get("nodeIds", [])]
            if len(new_wall["nodeIds"]) >= 3:
                merged["walls"].append(new_wall)
                existing_wall_ids.add(new_wid)

        return merged
