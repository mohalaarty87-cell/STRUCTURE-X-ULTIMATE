"""
3D Finite Element Analysis Direct Stiffness Solver
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import time
import math

from .dof_system import NodeDOFSystem
from .materials import Material
from .sections import CrossSection
from .frame_element_3d import FrameElement3D, MemberLoad, MemberInternalForces
from .shell_element_3d import ShellElement3D, ShellSurfaceLoad, ShellStressResult
from .meshing import ShellMeshGenerator, MeshedAreaEntity, MeshQualityReport
from .load_engine import LoadEngine, StaticEquilibriumCheck, MassSummary, LoadPatternType
from .matrix_ops import (
    create_zero_matrix,
    solve_linear_system,
    solve_sparse_system,
    matrix_vector_multiply,
    matrix_transpose
)

try:
    import numpy as np
    import scipy.sparse as sps
    import scipy.sparse.linalg as spla
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class NodalDisplacement:
    ux: float = 0.0
    uy: float = 0.0
    uz: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0


@dataclass
class NodalReaction:
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0


@dataclass
class AnalysisResult:
    """Complete results package returned by FEMSolver3D."""
    success: bool
    num_nodes: int
    num_elements: int
    num_dofs: int
    num_free_dofs: int
    displacements: Dict[str, NodalDisplacement]
    reactions: Dict[str, NodalReaction]
    member_forces: Dict[str, MemberInternalForces]
    total_applied_forces: Dict[str, float]
    total_reactions: Dict[str, float]
    equilibrium_error: Dict[str, float]
    solver_mode: str
    execution_time_ms: float
    num_frame_elements: int = 0
    num_shell_elements: int = 0
    shell_stresses: Dict[str, ShellStressResult] = field(default_factory=dict)
    meshed_entities: Dict[str, MeshedAreaEntity] = field(default_factory=dict)
    equilibrium_check: Optional[StaticEquilibriumCheck] = None
    mass_summary: Optional[MassSummary] = None
    case_results: Dict[str, Any] = field(default_factory=dict)
    combination_results: Dict[str, Any] = field(default_factory=dict)
    message: str = "Analysis solved successfully."


class FEMSolver3D:
    """
    Direct Stiffness Method 3D Frame & Shell Finite Element Solver.
    """

    def __init__(self, name: str = "STRUCTURE-X 3D Solver"):
        self.name = name
        self.dof_system = NodeDOFSystem()
        self.materials: Dict[str, Material] = {}
        self.sections: Dict[str, CrossSection] = {}
        self.elements: Dict[str, FrameElement3D] = {}
        self.shell_elements: Dict[str, ShellElement3D] = {}
        self.meshed_entities: Dict[str, MeshedAreaEntity] = {}
        
        # Load Engine instance
        self.load_engine = LoadEngine()
        
        # Nodal point loads: node_id -> [fx, fy, fz, mx, my, mz]
        self.nodal_loads: Dict[str, List[float]] = {}

    def add_node(self, node_id: str, x: float, y: float, z: float) -> int:
        return self.dof_system.add_node(node_id, x, y, z)

    def set_support(
        self,
        node_id: str,
        ux: bool = False,
        uy: bool = False,
        uz: bool = False,
        rx: bool = False,
        ry: bool = False,
        rz: bool = False
    ):
        self.dof_system.set_restraint(node_id, ux, uy, uz, rx, ry, rz)

    def set_prescribed_displacement(self, node_id: str, dof_index: int, value: float):
        self.dof_system.set_prescribed_displacement(node_id, dof_index, value)

    def add_grounded_spring(
        self,
        node_id: str,
        kx: float = 0.0,
        ky: float = 0.0,
        kz: float = 0.0,
        krx: float = 0.0,
        kry: float = 0.0,
        krz: float = 0.0
    ):
        self.dof_system.add_grounded_spring(node_id, kx, ky, kz, krx, kry, krz)

    def add_material(self, material: Material):
        self.materials[material.id] = material

    def add_section(self, section: CrossSection):
        self.sections[section.id] = section

    def add_element(
        self,
        element_id: str,
        start_node_id: str,
        end_node_id: str,
        material: Material,
        section: CrossSection,
        rotation_angle_deg: float = 0.0,
        release_start: Optional[Dict[str, bool]] = None,
        release_end: Optional[Dict[str, bool]] = None,
        include_shear_deformation: bool = True
    ) -> FrameElement3D:
        if start_node_id not in self.dof_system.nodes:
            raise ValueError(f"Start node '{start_node_id}' not defined.")
        if end_node_id not in self.dof_system.nodes:
            raise ValueError(f"End node '{end_node_id}' not defined.")

        elem = FrameElement3D(
            element_id=element_id,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            start_coords=self.dof_system.nodes[start_node_id],
            end_coords=self.dof_system.nodes[end_node_id],
            material=material,
            section=section,
            rotation_angle_deg=rotation_angle_deg,
            release_start=release_start,
            release_end=release_end,
            include_shear_deformation=include_shear_deformation
        )
        self.elements[element_id] = elem
        return elem

    def add_nodal_load(
        self,
        node_id: str,
        fx: float = 0.0,
        fy: float = 0.0,
        fz: float = 0.0,
        mx: float = 0.0,
        my: float = 0.0,
        mz: float = 0.0
    ):
        if node_id not in self.nodal_loads:
            self.nodal_loads[node_id] = [0.0] * 6
        self.nodal_loads[node_id][0] += float(fx)
        self.nodal_loads[node_id][1] += float(fy)
        self.nodal_loads[node_id][2] += float(fz)
        self.nodal_loads[node_id][3] += float(mx)
        self.nodal_loads[node_id][4] += float(my)
        self.nodal_loads[node_id][5] += float(mz)

    def add_member_load(
        self,
        element_id: str,
        load_type: str = 'uniform',
        direction: str = 'local_y',
        w1: float = 0.0,
        w2: float = 0.0,
        dist_a: float = 0.0,
        dist_b: float = 0.0
    ):
        if element_id not in self.elements:
            raise ValueError(f"Element '{element_id}' does not exist.")
        load = MemberLoad(
            load_type=load_type,
            direction=direction,
            w1=float(w1),
            w2=float(w2),
            dist_a=float(dist_a),
            dist_b=float(dist_b)
        )
        self.elements[element_id].add_load(load)

    def add_shell_element(
        self,
        element_id: str,
        node_ids: List[str],
        material: Material,
        thickness: float,
        parent_entity_id: Optional[str] = None,
        parent_entity_type: str = "slab"
    ) -> ShellElement3D:
        """Adds an individual 3-node or 4-node 3D flat shell element."""
        for nid in node_ids:
            if nid not in self.dof_system.nodes:
                raise ValueError(f"Node '{nid}' not found in DOF system.")

        coords = [self.dof_system.nodes[nid] for nid in node_ids]
        shell_elem = ShellElement3D(
            element_id=element_id,
            node_ids=node_ids,
            node_coords=coords,
            material=material,
            thickness=thickness,
            parent_entity_id=parent_entity_id,
            parent_entity_type=parent_entity_type
        )
        self.shell_elements[element_id] = shell_elem
        return shell_elem

    def mesh_and_add_area_entity(
        self,
        entity_id: str,
        corner_coords: List[Tuple[float, float, float]],
        material: Material,
        thickness: float,
        target_mesh_size: float = 0.5,
        openings: Optional[List[List[Tuple[float, float, float]]]] = None,
        entity_type: str = "slab",
        node_id_prefix: Optional[str] = None
    ) -> MeshedAreaEntity:
        """
        Meshes a slab or shear wall entity into 2D Shell elements,
        registers generated mesh nodes and shell elements in the solver.
        """
        meshed = ShellMeshGenerator.mesh_planar_quad_area(
            entity_id=entity_id,
            corner_coords=corner_coords,
            material=material,
            thickness=thickness,
            target_mesh_size=target_mesh_size,
            openings=openings,
            entity_type=entity_type,
            node_id_prefix=node_id_prefix
        )

        # Register nodes with automatic co-located node merging
        node_id_remap = {}
        for nid, (x, y, z) in meshed.nodes.items():
            matched_id = None
            for exist_id, (ex, ey, ez) in self.dof_system.nodes.items():
                dist = math.sqrt((x - ex) ** 2 + (y - ey) ** 2 + (z - ez) ** 2)
                if dist < 1e-4:
                    matched_id = exist_id
                    break
            if matched_id is not None:
                node_id_remap[nid] = matched_id
            else:
                self.add_node(nid, x, y, z)
                node_id_remap[nid] = nid

        # Register shell elements with remapped node IDs
        for elem in meshed.elements:
            elem.node_ids = [node_id_remap.get(nd_id, nd_id) for nd_id in elem.node_ids]
            self.shell_elements[elem.element_id] = elem

        self.meshed_entities[entity_id] = meshed
        return meshed

    def add_shell_load(
        self,
        element_id: str,
        load_type: str = 'uniform',
        direction: str = 'local_z',
        magnitude: float = 0.0
    ):
        """Adds a distributed surface load or pressure to a shell element."""
        if element_id not in self.shell_elements:
            raise ValueError(f"Shell element '{element_id}' does not exist.")
        load = ShellSurfaceLoad(load_type=load_type, direction=direction, magnitude=float(magnitude))
        self.shell_elements[element_id].add_load(load)

    def solve(self, num_stations: int = 11) -> AnalysisResult:
        """
        Executes complete direct stiffness FEA solution for 3D Frames and Shells.
        """
        start_time = time.perf_counter()
        total_dofs = self.dof_system.total_dofs
        if total_dofs == 0:
            raise ValueError("No nodes or DOFs defined in model.")

        # 1. Partition DOFs
        free_dofs, restrained_dofs = self.dof_system.partition_dofs()
        if len(free_dofs) == 0:
            raise ValueError("All degrees of freedom are restrained; no free system to solve.")

        # 2. Assemble Master Sparse Stiffness Matrix K
        # Dictionary of Keys (DOK) sparse representation
        dok_K: Dict[Tuple[int, int], float] = {}

        # 2a. Assemble Frame 1D Elements
        for elem_id, elem in self.elements.items():
            k_elem_global = elem.get_global_stiffness_matrix()
            elem_dofs = self.dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)

            for i in range(12):
                row = elem_dofs[i]
                for j in range(12):
                    col = elem_dofs[j]
                    val = k_elem_global[i][j]
                    if abs(val) > 1e-18:
                        key = (row, col)
                        dok_K[key] = dok_K.get(key, 0.0) + val

        # 2b. Assemble Shell 2D Elements
        for elem_id, elem in self.shell_elements.items():
            k_shell_global = elem.get_global_stiffness_matrix()
            shell_dofs = self.dof_system.get_shell_element_dof_indices(elem.node_ids)
            n_dofs = len(shell_dofs)

            for i in range(n_dofs):
                row = shell_dofs[i]
                for j in range(n_dofs):
                    col = shell_dofs[j]
                    val = k_shell_global[i][j]
                    if abs(val) > 1e-18:
                        key = (row, col)
                        dok_K[key] = dok_K.get(key, 0.0) + val

        # 3. Add Grounded Spring Stiffness terms to diagonals
        for node_id, springs in self.dof_system.grounded_springs.items():
            base_dof = self.dof_system.node_indices[node_id] * 6
            for dof_idx, k_val in springs.items():
                g_dof = base_dof + dof_idx
                dok_K[(g_dof, g_dof)] = dok_K.get((g_dof, g_dof), 0.0) + k_val

        # 4. Assemble Global Force Vector P_global
        P_global = [0.0] * total_dofs

        # Add Direct Nodal Point Loads
        for node_id, loads in self.nodal_loads.items():
            base_dof = self.dof_system.node_indices[node_id] * 6
            for d in range(6):
                P_global[base_dof + d] += loads[d]

        # Add Equivalent Nodal Forces from Member Distributed Loads
        for elem_id, elem in self.elements.items():
            if elem.loads:
                _, p_elem_global = elem.compute_equivalent_nodal_loads()
                elem_dofs = self.dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
                for i in range(12):
                    P_global[elem_dofs[i]] += p_elem_global[i]

        # Add Equivalent Nodal Forces from Shell Distributed Surface Loads
        for elem_id, elem in self.shell_elements.items():
            if elem.loads:
                _, p_shell_global = elem.compute_equivalent_nodal_loads()
                shell_dofs = self.dof_system.get_shell_element_dof_indices(elem.node_ids)
                for i in range(len(shell_dofs)):
                    P_global[shell_dofs[i]] += p_shell_global[i]

        # 5. Extract Partitioned Subvectors
        # P_f: Free load vector
        P_f = [P_global[dof] for dof in free_dofs]

        # Prescribed displacement vector u_r
        u_r = [0.0] * len(restrained_dofs)
        for idx, r_dof in enumerate(restrained_dofs):
            node_idx = r_dof // 6
            dof_local = r_dof % 6
            node_id = self.dof_system.node_order[node_idx]
            if node_id in self.dof_system.prescribed_displacements:
                if dof_local in self.dof_system.prescribed_displacements[node_id]:
                    u_r[idx] = self.dof_system.prescribed_displacements[node_id][dof_local]

        # Account for non-zero prescribed displacements: P_f_eff = P_f - K_fr * u_r
        if any(abs(v) > 1e-15 for v in u_r):
            for i_idx, f_dof in enumerate(free_dofs):
                for j_idx, r_dof in enumerate(restrained_dofs):
                    val = dok_K.get((f_dof, r_dof), 0.0)
                    if abs(val) > 1e-18:
                        P_f[i_idx] -= val * u_r[j_idx]

        # 6. Solve K_ff * u_f = P_f_eff
        u_f = solve_sparse_system(dok_K, free_dofs, P_f)

        # 7. Reconstruct Full Global Displacement Vector U (total_dofs x 1)
        U_full = [0.0] * total_dofs
        for idx, dof in enumerate(free_dofs):
            U_full[dof] = u_f[idx]
        for idx, dof in enumerate(restrained_dofs):
            U_full[dof] = u_r[idx]

        # 8. Compute Reactions: R = K_global * U_full - P_global
        R_full = [0.0] * total_dofs
        for (i, j), k_val in dok_K.items():
            R_full[i] += k_val * U_full[j]
        
        for d in range(total_dofs):
            R_full[d] -= P_global[d]

        # 9. Format Displacements and Reactions dictionaries
        displacements: Dict[str, NodalDisplacement] = {}
        reactions: Dict[str, NodalReaction] = {}

        for node_id in self.dof_system.node_order:
            b_dof = self.dof_system.node_indices[node_id] * 6
            displacements[node_id] = NodalDisplacement(
                ux=U_full[b_dof + 0],
                uy=U_full[b_dof + 1],
                uz=U_full[b_dof + 2],
                rx=U_full[b_dof + 3],
                ry=U_full[b_dof + 4],
                rz=U_full[b_dof + 5]
            )
            # Only report reaction if restrained or with spring
            restr = self.dof_system.restraints.get(node_id, {})
            springs = self.dof_system.grounded_springs.get(node_id, {})
            
            reactions[node_id] = NodalReaction(
                fx=R_full[b_dof + 0] if (restr.get(0, False) or 0 in springs) else 0.0,
                fy=R_full[b_dof + 1] if (restr.get(1, False) or 1 in springs) else 0.0,
                fz=R_full[b_dof + 2] if (restr.get(2, False) or 2 in springs) else 0.0,
                mx=R_full[b_dof + 3] if (restr.get(3, False) or 3 in springs) else 0.0,
                my=R_full[b_dof + 4] if (restr.get(4, False) or 4 in springs) else 0.0,
                mz=R_full[b_dof + 5] if (restr.get(5, False) or 5 in springs) else 0.0
            )

        # 10. Recover Member Internal Forces & Moments
        member_forces: Dict[str, MemberInternalForces] = {}
        for elem_id, elem in self.elements.items():
            elem_dofs = self.dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
            u_elem = [U_full[d] for d in elem_dofs]
            m_forces = elem.recover_internal_forces(u_elem, num_stations=num_stations)
            member_forces[elem_id] = m_forces

        # 10b. Recover Shell Element Internal Forces & Stresses
        shell_stresses: Dict[str, ShellStressResult] = {}
        for elem_id, elem in self.shell_elements.items():
            shell_dofs = self.dof_system.get_shell_element_dof_indices(elem.node_ids)
            u_shell = [U_full[d] for d in shell_dofs]
            s_stress = elem.recover_stresses_and_forces(u_shell)
            shell_stresses[elem_id] = s_stress

        # 11. Full 6-DOF Static Equilibrium Verification (summing forces & moments about origin [0,0,0])
        total_applied = {"FX": 0.0, "FY": 0.0, "FZ": 0.0, "MX": 0.0, "MY": 0.0, "MZ": 0.0}
        
        # Nodal loads contribution
        for node_id, loads in self.nodal_loads.items():
            fx, fy, fz, mx, my, mz = loads
            total_applied["FX"] += fx
            total_applied["FY"] += fy
            total_applied["FZ"] += fz
            total_applied["MX"] += mx
            total_applied["MY"] += my
            total_applied["MZ"] += mz
            # Moment from force r x F
            x, y, z = self.dof_system.nodes[node_id]
            total_applied["MX"] += (y * fz - z * fy)
            total_applied["MY"] += (z * fx - x * fz)
            total_applied["MZ"] += (x * fy - y * fx)

        # Member loads contribution to total applied loads
        for elem_id, elem in self.elements.items():
            x_m = 0.5 * (elem.start_coords[0] + elem.end_coords[0])
            y_m = 0.5 * (elem.start_coords[1] + elem.end_coords[1])
            z_m = 0.5 * (elem.start_coords[2] + elem.end_coords[2])
            for load in elem.loads:
                fx_elem, fy_elem, fz_elem = 0.0, 0.0, 0.0
                if load.load_type in ('uniform', 'trapezoidal', 'triangular'):
                    avg_w = 0.5 * (load.w1 + load.w2) if load.load_type in ('trapezoidal', 'triangular') else load.w1
                    tot_w = avg_w * elem.length
                    if load.direction == 'global_X': fx_elem = tot_w
                    elif load.direction == 'global_Y': fy_elem = tot_w
                    elif load.direction == 'global_Z': fz_elem = tot_w
                elif load.load_type == 'point':
                    if load.direction == 'global_X': fx_elem = load.w1
                    elif load.direction == 'global_Y': fy_elem = load.w1
                    elif load.direction == 'global_Z': fz_elem = load.w1
                
                total_applied["FX"] += fx_elem
                total_applied["FY"] += fy_elem
                total_applied["FZ"] += fz_elem
                total_applied["MX"] += (y_m * fz_elem - z_m * fy_elem)
                total_applied["MY"] += (z_m * fx_elem - x_m * fz_elem)
                total_applied["MZ"] += (x_m * fy_elem - y_m * fx_elem)

        # Shell loads contribution to total applied loads
        for elem_id, elem in self.shell_elements.items():
            cx = sum(c[0] for c in elem.node_coords) / len(elem.node_coords)
            cy = sum(c[1] for c in elem.node_coords) / len(elem.node_coords)
            cz = sum(c[2] for c in elem.node_coords) / len(elem.node_coords)
            for load in elem.loads:
                A = elem.area
                mag = load.magnitude
                fx_sh, fy_sh, fz_sh = 0.0, 0.0, 0.0
                if load.direction == 'global_X': fx_sh = mag * A
                elif load.direction == 'global_Y': fy_sh = mag * A
                elif load.direction == 'global_Z': fz_sh = mag * A
                elif load.direction == 'local_z':
                    _, _, z_ax = elem.local_axes
                    fx_sh = mag * A * z_ax[0]
                    fy_sh = mag * A * z_ax[1]
                    fz_sh = mag * A * z_ax[2]

                total_applied["FX"] += fx_sh
                total_applied["FY"] += fy_sh
                total_applied["FZ"] += fz_sh
                total_applied["MX"] += (cy * fz_sh - cz * fy_sh)
                total_applied["MY"] += (cz * fx_sh - cx * fz_sh)
                total_applied["MZ"] += (cx * fy_sh - cy * fx_sh)

        total_rx = {"FX": 0.0, "FY": 0.0, "FZ": 0.0, "MX": 0.0, "MY": 0.0, "MZ": 0.0}
        for node_id, r in reactions.items():
            total_rx["FX"] += r.fx
            total_rx["FY"] += r.fy
            total_rx["FZ"] += r.fz
            total_rx["MX"] += r.mx
            total_rx["MY"] += r.my
            total_rx["MZ"] += r.mz
            x, y, z = self.dof_system.nodes[node_id]
            total_rx["MX"] += (y * r.fz - z * r.fy)
            total_rx["MY"] += (z * r.fx - x * r.fz)
            total_rx["MZ"] += (x * r.fy - y * r.fx)

        eq_error = {
            "FX": abs(total_applied["FX"] + total_rx["FX"]),
            "FY": abs(total_applied["FY"] + total_rx["FY"]),
            "FZ": abs(total_applied["FZ"] + total_rx["FZ"]),
            "MX": abs(total_applied["MX"] + total_rx["MX"]),
            "MY": abs(total_applied["MY"] + total_rx["MY"]),
            "MZ": abs(total_applied["MZ"] + total_rx["MZ"])
        }

        # Equilibrium percentage error (relative to peak applied force/moment)
        ref_force = max(1.0, max(abs(total_applied["FX"]), abs(total_applied["FY"]), abs(total_applied["FZ"])))
        ref_moment = max(1.0, max(abs(total_applied["MX"]), abs(total_applied["MY"]), abs(total_applied["MZ"])))
        pct_err_force = (max(eq_error["FX"], eq_error["FY"], eq_error["FZ"]) / ref_force) * 100.0
        pct_err_moment = (max(eq_error["MX"], eq_error["MY"], eq_error["MZ"]) / ref_moment) * 100.0
        is_equilibrated = (pct_err_force < 0.1) and (pct_err_moment < 0.1)

        eq_check = StaticEquilibriumCheck(
            case_id="ACTIVE_CASE",
            total_applied_fx=total_applied["FX"],
            total_applied_fy=total_applied["FY"],
            total_applied_fz=total_applied["FZ"],
            total_applied_mx=total_applied["MX"],
            total_applied_my=total_applied["MY"],
            total_applied_mz=total_applied["MZ"],
            total_reaction_fx=total_rx["FX"],
            total_reaction_fy=total_rx["FY"],
            total_reaction_fz=total_rx["FZ"],
            total_reaction_mx=total_rx["MX"],
            total_reaction_my=total_rx["MY"],
            total_reaction_mz=total_rx["MZ"],
            delta_fx=eq_error["FX"],
            delta_fy=eq_error["FY"],
            delta_fz=eq_error["FZ"],
            delta_mx=eq_error["MX"],
            delta_my=eq_error["MY"],
            delta_mz=eq_error["MZ"],
            percent_error_force=pct_err_force,
            percent_error_moment=pct_err_moment,
            is_equilibrated=is_equilibrated
        )

        exec_time = (time.perf_counter() - start_time) * 1000.0

        return AnalysisResult(
            success=True,
            num_nodes=self.dof_system.total_nodes,
            num_elements=len(self.elements) + len(self.shell_elements),
            num_dofs=total_dofs,
            num_free_dofs=len(free_dofs),
            displacements=displacements,
            reactions=reactions,
            member_forces=member_forces,
            total_applied_forces=total_applied,
            total_reactions=total_rx,
            equilibrium_error=eq_error,
            equilibrium_check=eq_check,
            solver_mode="Sparse SciPy/SuperLU" if HAS_SCIPY else "Direct Matrix Engine",
            execution_time_ms=round(exec_time, 2),
            num_frame_elements=len(self.elements),
            num_shell_elements=len(self.shell_elements),
            shell_stresses=shell_stresses,
            meshed_entities=self.meshed_entities
        )

    def calculate_mass_source(self) -> MassSummary:
        """Computes structural mass distribution across nodes and stories."""
        nodes = self.dof_system.nodes
        return self.load_engine.calculate_mass_source(
            nodes=nodes,
            frame_elements=self.elements,
            shell_elements=self.shell_elements,
            materials=self.materials,
            sections=self.sections
        )
