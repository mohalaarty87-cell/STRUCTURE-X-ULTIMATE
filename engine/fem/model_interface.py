"""
Model Interface and Serialization Bridge
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
"""

from typing import Dict, Any, List, Optional
import json

from .materials import Material
from .sections import CrossSection
from .solver_core import FEMSolver3D, AnalysisResult


class ModelInterface:
    """
    Parses structural model definitions from JSON / Dict formats,
    configures FEMSolver3D, runs analysis, and serializes results.
    """

    @staticmethod
    def build_solver_from_dict(data: Dict[str, Any]) -> FEMSolver3D:
        solver = FEMSolver3D(name=data.get("projectName", "Structural Model"))

        # 1. Materials
        materials_data = data.get("materials", [])
        for mat_d in materials_data:
            mat = Material(
                id=mat_d.get("id", f"MAT-{len(solver.materials)}"),
                name=mat_d.get("name", "Material"),
                elastic_modulus=float(mat_d.get("elasticModulus", mat_d.get("E", 30.0e9))),
                poisson_ratio=float(mat_d.get("poissonRatio", mat_d.get("nu", 0.20))),
                density=float(mat_d.get("density", mat_d.get("rho", 2500.0)))
            )
            solver.add_material(mat)

        # Fallback material if empty
        if not solver.materials:
            solver.add_material(Material.concrete_c30("MAT-DEFAULT"))

        # 2. Sections
        sections_data = data.get("sections", [])
        for sec_d in sections_data:
            # Check if dimensions are provided
            w = float(sec_d.get("width", sec_d.get("b", 0.3)))
            h = float(sec_d.get("depth", sec_d.get("height", sec_d.get("h", 0.5))))
            
            area = float(sec_d.get("area", sec_d.get("A", w * h)))
            iz = float(sec_d.get("momentOfInertiaZ", sec_d.get("Iz", sec_d.get("Ixx", (w * h**3) / 12.0))))
            iy = float(sec_d.get("momentOfInertiaY", sec_d.get("Iy", sec_d.get("Iyy", (h * w**3) / 12.0))))
            j = float(sec_d.get("torsionalConstant", sec_d.get("J", iz + iy)))
            
            sec = CrossSection(
                id=sec_d.get("id", f"SEC-{len(solver.sections)}"),
                name=sec_d.get("name", "Section"),
                area=area,
                iz=iz,
                iy=iy,
                torsion_j=j,
                depth=h,
                width=w
            )
            solver.add_section(sec)

        # Fallback section if empty
        if not solver.sections:
            solver.add_section(CrossSection.rectangular("SEC-DEFAULT", "300x500 RC", 0.3, 0.5))

        # 3. Nodes
        nodes_data = data.get("nodes", [])
        for n_d in nodes_data:
            node_id = str(n_d["id"])
            x = float(n_d.get("x", 0.0))
            y = float(n_d.get("y", 0.0))
            z = float(n_d.get("z", 0.0))
            solver.add_node(node_id, x, y, z)

            # Restraints
            restr = n_d.get("restraints", n_d.get("isRestrained", {}))
            if isinstance(restr, dict):
                solver.set_support(
                    node_id,
                    ux=bool(restr.get("ux", restr.get("fx", False))),
                    uy=bool(restr.get("uy", restr.get("fy", False))),
                    uz=bool(restr.get("uz", restr.get("fz", False))),
                    rx=bool(restr.get("rx", restr.get("mx", False))),
                    ry=bool(restr.get("ry", restr.get("my", False))),
                    rz=bool(restr.get("rz", restr.get("mz", False)))
                )
            elif isinstance(restr, bool) and restr:
                # Fixed default
                solver.set_support(node_id, ux=True, uy=True, uz=True, rx=True, ry=True, rz=True)

            # Springs
            springs = n_d.get("springStiffness", {})
            if isinstance(springs, dict):
                solver.add_grounded_spring(
                    node_id,
                    kx=float(springs.get("kx", 0.0)),
                    ky=float(springs.get("ky", 0.0)),
                    kz=float(springs.get("kz", 0.0)),
                    krx=float(springs.get("krx", 0.0)),
                    kry=float(springs.get("kry", 0.0)),
                    krz=float(springs.get("krz", 0.0))
                )

            # Nodal Loads
            n_loads = n_d.get("loads", {})
            if isinstance(n_loads, dict):
                solver.add_nodal_load(
                    node_id,
                    fx=float(n_loads.get("fx", 0.0)),
                    fy=float(n_loads.get("fy", 0.0)),
                    fz=float(n_loads.get("fz", 0.0)),
                    mx=float(n_loads.get("mx", 0.0)),
                    my=float(n_loads.get("my", 0.0)),
                    mz=float(n_loads.get("mz", 0.0))
                )

        # 4. Elements / Members
        members_data = data.get("members", [])
        default_mat = list(solver.materials.values())[0]
        default_sec = list(solver.sections.values())[0]

        for m_d in members_data:
            elem_id = str(m_d["id"])
            s_node = str(m_d["startNodeId"])
            e_node = str(m_d["endNodeId"])
            
            mat = solver.materials.get(m_d.get("materialId", ""), default_mat)
            sec = solver.sections.get(m_d.get("sectionId", ""), default_sec)
            rot = float(m_d.get("rotationAngleDeg", m_d.get("localAxisAngle", 0.0)))
            
            releases = m_d.get("releases", {})
            rel_start = {}
            rel_end = {}
            if isinstance(releases, dict):
                rel_start = releases.get("start", {})
                rel_end = releases.get("end", {})
            elif isinstance(releases, str) and releases == "Pinned-Pinned":
                rel_start = {"my": True, "mz": True}
                rel_end = {"my": True, "mz": True}

            solver.add_element(
                element_id=elem_id,
                start_node_id=s_node,
                end_node_id=e_node,
                material=mat,
                section=sec,
                rotation_angle_deg=rot,
                release_start=rel_start,
                release_end=rel_end
            )

        # 5. Member Distributed Loads
        member_loads_data = data.get("memberLoads", data.get("lineLoads", []))
        for ml in member_loads_data:
            elem_id = ml.get("memberId", ml.get("elementId"))
            if elem_id in solver.elements:
                solver.add_member_load(
                    element_id=elem_id,
                    load_type=ml.get("type", "uniform"),
                    direction=ml.get("direction", "global_Y"),
                    w1=float(ml.get("w1", ml.get("magnitude", 0.0))),
                    w2=float(ml.get("w2", ml.get("magnitude", 0.0))),
                    dist_a=float(ml.get("distA", 0.0)),
                    dist_b=float(ml.get("distB", 0.0))
                )

        # 5b. Temperature loads on members
        temp_loads_data = data.get("temperatureLoads", [])
        for tl in temp_loads_data:
            elem_id = tl.get("memberId", tl.get("elementId"))
            if elem_id in solver.elements:
                solver.elements[elem_id].add_load(
                    MemberLoad(
                        load_type="temperature",
                        direction="local_x",
                        delta_t_uniform=float(tl.get("deltaT", tl.get("uniform", 0.0))),
                        delta_t_gradient_y=float(tl.get("gradientY", 0.0)),
                        delta_t_gradient_z=float(tl.get("gradientZ", 0.0)),
                        thermal_alpha=float(tl.get("alpha", 1.0e-5))
                    )
                )

        # 6. Openings dictionary
        openings_by_parent: Dict[str, List[List[Tuple[float, float, float]]]] = {}
        openings_data = data.get("openings", [])
        for op_d in openings_data:
            p_id = str(op_d.get("parentId", ""))
            op_node_ids = op_d.get("nodeIds", [])
            op_coords = []
            for nid in op_node_ids:
                if nid in solver.dof_system.nodes:
                    op_coords.append(solver.dof_system.nodes[nid])
            if len(op_coords) >= 3:
                openings_by_parent.setdefault(p_id, []).append(op_coords)

        # 7. Slabs (Planar Area Shell Elements)
        slabs_data = data.get("slabs", [])
        mesh_target_size = float(data.get("meshSize", data.get("targetMeshSize", 1.0)))

        for slab_d in slabs_data:
            slab_id = str(slab_d["id"])
            node_ids = slab_d.get("nodeIds", [])
            if len(node_ids) == 4:
                coords = [solver.dof_system.nodes[nid] for nid in node_ids if nid in solver.dof_system.nodes]
                if len(coords) == 4:
                    mat = solver.materials.get(slab_d.get("materialId", ""), default_mat)
                    thickness = float(slab_d.get("thickness", 0.20))
                    slab_mesh_size = float(slab_d.get("meshSize", mesh_target_size))
                    op_list = openings_by_parent.get(slab_id, [])

                    meshed = solver.mesh_and_add_area_entity(
                        entity_id=slab_id,
                        corner_coords=coords,
                        material=mat,
                        thickness=thickness,
                        target_mesh_size=slab_mesh_size,
                        openings=op_list,
                        entity_type="slab",
                        node_id_prefix=f"N_{slab_id}"
                    )

                    # Dead / Live surface loads on slab
                    dead_load = float(slab_d.get("loadDead", 0.0)) * 1000.0 # kN/m2 -> N/m2
                    live_load = float(slab_d.get("loadLive", 0.0)) * 1000.0
                    tot_gravity = -(dead_load + live_load)
                    if abs(tot_gravity) > 1e-6:
                        for elem in meshed.elements:
                            solver.add_shell_load(
                                element_id=elem.element_id,
                                load_type='gravity',
                                direction='global_Y',
                                magnitude=tot_gravity
                            )

        # 8. Shear Walls (Vertical Area Shell Elements)
        walls_data = data.get("walls", [])
        for wall_d in walls_data:
            wall_id = str(wall_d["id"])
            node_ids = wall_d.get("nodeIds", [])
            if len(node_ids) == 4:
                coords = [solver.dof_system.nodes[nid] for nid in node_ids if nid in solver.dof_system.nodes]
                if len(coords) == 4:
                    mat = solver.materials.get(wall_d.get("materialId", ""), default_mat)
                    thickness = float(wall_d.get("thickness", 0.25))
                    wall_mesh_size = float(wall_d.get("meshSize", mesh_target_size))
                    op_list = openings_by_parent.get(wall_id, [])

                    solver.mesh_and_add_area_entity(
                        entity_id=wall_id,
                        corner_coords=coords,
                        material=mat,
                        thickness=thickness,
                        target_mesh_size=wall_mesh_size,
                        openings=op_list,
                        entity_type="wall",
                        node_id_prefix=f"N_{wall_id}"
                    )

        # 9. Direct Shell Surface Loads / Area Loads
        shell_loads_data = data.get("shellLoads", data.get("areaLoads", []))
        for sl in shell_loads_data:
            elem_id = sl.get("elementId", sl.get("shellId"))
            if elem_id in solver.shell_elements:
                solver.add_shell_load(
                    element_id=elem_id,
                    load_type=sl.get("type", "uniform"),
                    direction=sl.get("direction", "local_z"),
                    magnitude=float(sl.get("magnitude", 0.0))
                )

        # 10. Load Engine Patterns & Combinations configuration
        patterns_data = data.get("loadPatterns", [])
        for p_d in patterns_data:
            p_id = p_d.get("id", "DEAD")
            p_type_str = p_d.get("type", "DEAD").upper()
            sw_mult = float(p_d.get("selfWeightMultiplier", 1.0 if p_type_str == "DEAD" else 0.0))
            solver.load_engine.create_load_pattern(p_id, p_type_str, sw_mult, p_d.get("description", ""))

        combinations_data = data.get("loadCombinations", [])
        for c_d in combinations_data:
            solver.load_engine.create_load_combination(
                comb_id=c_d.get("id", f"COMB_{len(solver.load_engine.combinations)+1}"),
                name=c_d.get("name", "Combination"),
                case_factors=c_d.get("factors", {}),
                comb_type=c_d.get("type", "linear_add")
            )

        return solver

    @staticmethod
    def result_to_dict(res: AnalysisResult) -> Dict[str, Any]:
        """Serializes AnalysisResult into JSON-serializable dictionary."""
        eq_data = {
            "totalAppliedForces": res.total_applied_forces,
            "totalReactions": res.total_reactions,
            "error": res.equilibrium_error
        }
        if res.equilibrium_check:
            eq_data.update({
                "percentErrorForce": res.equilibrium_check.percent_error_force,
                "percentErrorMoment": res.equilibrium_check.percent_error_moment,
                "isEquilibrated": res.equilibrium_check.is_equilibrated
            })

        return {
            "success": res.success,
            "summary": {
                "numNodes": res.num_nodes,
                "numElements": res.num_elements,
                "numFrameElements": res.num_frame_elements,
                "numShellElements": res.num_shell_elements,
                "numDofs": res.num_dofs,
                "numFreeDofs": res.num_free_dofs,
                "solverMode": res.solver_mode,
                "executionTimeMs": res.execution_time_ms
            },
            "displacements": {
                nid: {
                    "ux": d.ux, "uy": d.uy, "uz": d.uz,
                    "rx": d.rx, "ry": d.ry, "rz": d.rz
                }
                for nid, d in res.displacements.items()
            },
            "reactions": {
                nid: {
                    "fx": r.fx, "fy": r.fy, "fz": r.fz,
                    "mx": r.mx, "my": r.my, "mz": r.mz
                }
                for nid, r in res.reactions.items()
            },
            "memberForces": {
                eid: {
                    "stations": mf.stations,
                    "N": mf.N,
                    "V2": mf.V2,
                    "V3": mf.V3,
                    "T": mf.T,
                    "M2": mf.M2,
                    "M3": mf.M3
                }
                for eid, mf in res.member_forces.items()
            },
            "shellStresses": {
                eid: {
                    "Nxx": s.Nxx, "Nyy": s.Nyy, "Nxy": s.Nxy,
                    "Mxx": s.Mxx, "Myy": s.Myy, "Mxy": s.Mxy,
                    "Vx": s.Vx, "Vy": s.Vy,
                    "sigmaTop": {"xx": s.sigma_top_xx, "yy": s.sigma_top_yy, "xy": s.tau_top_xy, "s1": s.sigma_1_top, "s2": s.sigma_2_top, "vm": s.von_mises_top},
                    "sigmaMid": {"xx": s.sigma_mid_xx, "yy": s.sigma_mid_yy, "xy": s.tau_mid_xy},
                    "sigmaBot": {"xx": s.sigma_bot_xx, "yy": s.sigma_bot_yy, "xy": s.tau_bot_xy, "s1": s.sigma_1_bot, "s2": s.sigma_2_bot, "vm": s.von_mises_bot},
                    "vonMisesMax": s.von_mises_max
                }
                for eid, s in res.shell_stresses.items()
            },
            "equilibrium": eq_data
        }
