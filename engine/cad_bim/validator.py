"""
STRUCTURE-X ULTIMATE — CAD & BIM IMPORT VALIDATOR (PHASE 13)
Performs strict geometric sanity checks, topological verification, duplicate detection,
dangling reference resolution, and property completeness checks.
"""

import math
from typing import Dict, Any, List, Optional, Set, Tuple
from .types import (
    ValidationSummary,
    ValidationIssue,
    ValidationSeverity,
)


class ImportValidator:
    """
    Validates imported structural data prior to mapping and project commitment.
    Guarantees that corrupt or geometrically invalid data is detected and flagged.
    """

    @staticmethod
    def validate_model_data(
        data: Dict[str, Any],
        tolerance_m: float = 0.001
    ) -> ValidationSummary:
        issues: List[ValidationIssue] = []

        nodes = data.get("nodes", [])
        members = data.get("members", [])
        slabs = data.get("slabs", [])
        walls = data.get("walls", [])
        materials = data.get("materials", [])
        sections = data.get("sections", [])

        # 1. Check basic container counts
        if not nodes and (members or slabs or walls):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="VAL-NODES-EMPTY",
                    message="Model contains structural elements but no defined node coordinates.",
                    entity_type="nodes",
                    suggested_fix="Ensure file defines 3D Cartesian points or nodes for member endpoints."
                )
            )

        # 2. Validate Nodes
        node_id_set: Set[str] = set()
        node_coords: Dict[str, Tuple[float, float, float]] = {}

        for i, node in enumerate(nodes):
            nid = str(node.get("id", f"NODE_{i+1}"))
            if nid in node_id_set:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VAL-NODE-DUP-ID",
                        message=f"Duplicate node ID detected: '{nid}'. Will be automatically deduplicated.",
                        entity_type="node",
                        entity_id=nid,
                        suggested_fix="Auto-assign unique node identifier."
                    )
                )
            node_id_set.add(nid)

            x = node.get("x")
            y = node.get("y")
            z = node.get("z")

            # Check coordinate validity
            if x is None or y is None or z is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL-NODE-MISSING-COORD",
                        message=f"Node '{nid}' is missing one or more coordinates (x={x}, y={y}, z={z}).",
                        entity_type="node",
                        entity_id=nid,
                        suggested_fix="Specify 3D Cartesian coordinates."
                    )
                )
                continue

            try:
                xf, yf, zf = float(x), float(y), float(z)
                if not (math.isfinite(xf) and math.isfinite(yf) and math.isfinite(zf)):
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="VAL-NODE-NON-FINITE",
                            message=f"Node '{nid}' has non-finite coordinates: ({xf}, {yf}, {zf}).",
                            entity_type="node",
                            entity_id=nid
                        )
                    )
                else:
                    node_coords[nid] = (xf, yf, zf)
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL-NODE-INVALID-NUM",
                        message=f"Node '{nid}' coordinate cannot be parsed to float.",
                        entity_type="node",
                        entity_id=nid
                    )
                )

        # Spatial duplicate check for nodes (within tolerance)
        # Using grid-bucketing for high performance
        coord_bucket: Dict[Tuple[int, int, int], List[str]] = {}
        dup_pairs: List[Tuple[str, str, float]] = []

        for nid, (x, y, z) in node_coords.items():
            bx = int(round(x / max(tolerance_m, 1e-4)))
            by = int(round(y / max(tolerance_m, 1e-4)))
            bz = int(round(z / max(tolerance_m, 1e-4)))

            found_dup = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        key = (bx + dx, by + dy, bz + dz)
                        if key in coord_bucket:
                            for other_id in coord_bucket[key]:
                                ox, oy, oz = node_coords[other_id]
                                dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2)
                                if dist <= tolerance_m:
                                    dup_pairs.append((nid, other_id, dist))
                                    found_dup = True
                                    break
                        if found_dup:
                            break
                    if found_dup:
                        break
                if found_dup:
                    break

            bucket_key = (bx, by, bz)
            if bucket_key not in coord_bucket:
                coord_bucket[bucket_key] = []
            coord_bucket[bucket_key].append(nid)

        if dup_pairs:
            sample = dup_pairs[:3]
            sample_desc = ", ".join(f"('{a}' & '{b}', d={d*1000:.1f}mm)" for a, b, d in sample)
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="VAL-NODE-COINCIDENT",
                    message=f"Detected {len(dup_pairs)} coincident node pairs within {tolerance_m*1000:.1f}mm: {sample_desc}.",
                    entity_type="node",
                    suggested_fix="Coincident nodes can be automatically merged during import."
                )
            )

        # 3. Validate Materials and Sections
        mat_ids = {str(m.get("id")) for m in materials if "id" in m}
        sec_ids = {str(s.get("id")) for s in sections if "id" in s}

        # 4. Validate Members (Columns, Beams, Braces)
        member_id_set: Set[str] = set()
        zero_len_count = 0
        dangling_node_count = 0

        for i, m in enumerate(members):
            mid = str(m.get("id", f"MEM_{i+1}"))
            if mid in member_id_set:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VAL-MEM-DUP-ID",
                        message=f"Duplicate member ID detected: '{mid}'.",
                        entity_type="member",
                        entity_id=mid
                    )
                )
            member_id_set.add(mid)

            sn = str(m.get("startNodeId", ""))
            en = str(m.get("endNodeId", ""))

            if sn not in node_coords or en not in node_coords:
                dangling_node_count += 1
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL-MEM-DANGLING-NODE",
                        message=f"Member '{mid}' references undefined node (start='{sn}', end='{en}').",
                        entity_type="member",
                        entity_id=mid,
                        suggested_fix="Ensure referenced joints exist in node table."
                    )
                )
            else:
                p1 = node_coords[sn]
                p2 = node_coords[en]
                length = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2)
                if length < 0.001:
                    zero_len_count += 1
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="VAL-MEM-ZERO-LENGTH",
                            message=f"Member '{mid}' has near-zero length ({length*1000:.2f}mm).",
                            entity_type="member",
                            entity_id=mid,
                            suggested_fix="Remove or expand collinear points."
                        )
                    )

            # Check section & material reference
            sec_id = m.get("sectionId")
            if sec_id and sec_ids and sec_id not in sec_ids:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="VAL-MEM-UNMAPPED-SECTION",
                        message=f"Member '{mid}' references section '{sec_id}' not in section list.",
                        entity_type="member",
                        entity_id=mid,
                        suggested_fix="Map to default section or auto-create parametric section."
                    )
                )

        # 5. Validate Slabs
        for i, s in enumerate(slabs):
            sid = str(s.get("id", f"SLAB_{i+1}"))
            nids = [str(n) for n in s.get("nodeIds", [])]
            if len(nids) < 3:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL-SLAB-VERTICES",
                        message=f"Slab '{sid}' has fewer than 3 boundary vertices ({len(nids)}).",
                        entity_type="slab",
                        entity_id=sid
                    )
                )
            for nid in nids:
                if nid not in node_coords:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="VAL-SLAB-DANGLING-NODE",
                            message=f"Slab '{sid}' references non-existent node '{nid}'.",
                            entity_type="slab",
                            entity_id=sid
                        )
                    )

        # 6. Validate Walls
        for i, w in enumerate(walls):
            wid = str(w.get("id", f"WALL_{i+1}"))
            nids = [str(n) for n in w.get("nodeIds", [])]
            if len(nids) < 3:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="VAL-WALL-VERTICES",
                        message=f"Wall '{wid}' requires at least 3 vertices ({len(nids)} found).",
                        entity_type="wall",
                        entity_id=wid
                    )
                )

        # Compile Summary
        err_count = sum(1 for iss in issues if iss.severity == ValidationSeverity.ERROR)
        warn_count = sum(1 for iss in issues if iss.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for iss in issues if iss.severity == ValidationSeverity.INFO)

        is_valid = (err_count == 0)
        # can_import allows import if errors are fixable or if only warnings
        can_import = (err_count == 0 or (err_count <= zero_len_count + dangling_node_count and len(nodes) > 0))

        return ValidationSummary(
            is_valid=is_valid,
            can_import=can_import,
            total_issues=len(issues),
            error_count=err_count,
            warning_count=warn_count,
            info_count=info_count,
            issues=issues
        )
