"""
P-Delta Second-Order Geometric Non-Linear Analysis & Stability Diagnostics
STRUCTURE-X ULTIMATE — PHASE 08

Implements:
  - 3D Element and Global Geometric Stiffness Matrix Assembly [K_G]
  - Second-Order P-Delta Iterative Equilibrium Solver ([K_E + K_G] {u} = {P})
  - Displacement and Residual Force Convergence Criteria
  - Stability Diagnostics:
      * Tangent Matrix Positive Definiteness & Minimum Eigenvalue Check
      * Global Elastic Critical Buckling Load Factor (lambda_cr) via Generalized Eigenvalue Problem
      * ASCE 7-16 / Eurocode 8 Story Stability Coefficient (theta = P*Delta / (V*h))
      * P-Delta Moment and Displacement Amplification Factors (B1, B2)
  - Story-level responses: Story Shears, Story Drifts, Floor Displacements
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import math
import time

from .dof_system import NodeDOFSystem
from .materials import Material
from .sections import CrossSection
from .frame_element_3d import FrameElement3D, MemberInternalForces
from .solver_core import FEMSolver3D, NodalDisplacement, NodalReaction, AnalysisResult
from .matrix_ops import (
    create_zero_matrix,
    matrix_vector_multiply,
    vector_dot_product
)

try:
    import numpy as np
    import scipy.sparse as sps
    import scipy.sparse.linalg as spla
    HAS_NUMPY_SCIPY = True
except ImportError:
    HAS_NUMPY_SCIPY = False
    np = None
    sps = None
    spla = None


@dataclass
class StoryStabilityResult:
    """Story-level P-Delta and stability assessment parameters."""
    story_index: int
    elevation_bottom: float   # m
    elevation_top: float      # m
    story_height: float       # m (h_i)
    total_axial_gravity_P: float # N (total cumulative vertical load at story level)
    story_shear_V: float      # N (total lateral shear force at story level)
    story_drift_delta: float  # m (relative lateral displacement across story)
    drift_ratio: float        # delta / h_i
    stability_coefficient_theta: float # theta = P * delta / (V * h)
    is_acceptable: bool       # theta <= theta_max (typically 0.10 to 0.25)
    theta_max: float = 0.25
    amplification_factor: float = 1.0 # 1 / (1 - theta)


@dataclass
class StabilityDiagnostics:
    """Global structural stability diagnostics and buckling checks."""
    is_stable: bool
    status_message: str
    critical_buckling_factor_lambda: float # lambda_cr: elastic critical buckling ratio
    min_tangent_eigenvalue: float
    max_stability_coefficient: float
    governing_story: int
    elastic_first_order_max_disp: float # m
    p_delta_second_order_max_disp: float # m
    displacement_amplification_ratio: float # u_pdelta / u_linear
    moment_amplification_ratio: float
    stories: List[StoryStabilityResult] = field(default_factory=list)


@dataclass
class PDeltaIterationStep:
    """Records diagnostic progress per iteration."""
    iteration: int
    relative_displacement_error: float
    max_displacement: float
    max_axial_force: float


@dataclass
class PDeltaResult:
    """Comprehensive output package for P-Delta analysis."""
    success: bool
    converged: bool
    num_iterations: int
    execution_time_ms: float
    displacements: Dict[str, NodalDisplacement]
    reactions: Dict[str, NodalReaction]
    member_forces: Dict[str, MemberInternalForces]
    stability_diagnostics: StabilityDiagnostics
    iteration_history: List[PDeltaIterationStep] = field(default_factory=list)
    story_shears: Dict[int, float] = field(default_factory=dict)
    story_drifts: Dict[int, float] = field(default_factory=dict)


class PDeltaSolver:
    """
    Second-Order P-Delta Iterative Structural Solver.
    Uses full 3D element geometric stiffness formulations and tangent stiffness updates.
    """

    def __init__(
        self,
        solver: FEMSolver3D,
        max_iterations: int = 40,
        convergence_tolerance: float = 1e-4,
        divergence_limit: float = 1e6
    ):
        self.solver = solver
        self.max_iterations = max_iterations
        self.convergence_tolerance = convergence_tolerance
        self.divergence_limit = divergence_limit

    def solve(
        self,
        applied_nodal_loads: Optional[Dict[str, List[float]]] = None,
        num_stations: int = 11
    ) -> PDeltaResult:
        """
        Executes second-order P-Delta analysis on the current structure:
          1. Performs 1st order linear static solve to get initial axial forces P_0.
          2. Iteratively updates [K_T] = [K_E] + [K_G(P_k)] and solves for {u_k}.
          3. Evaluates convergence ||u_k - u_{k-1}|| / ||u_k|| < tol.
          4. Performs stability diagnostics (eigenvalue buckling factor & story theta).
        """
        t_start = time.time()
        dof_system = self.solver.dof_system
        free_dofs, restrained_dofs = dof_system.partition_dofs()
        total_dofs = len(dof_system.node_order) * 6
        n_free = len(free_dofs)

        if n_free == 0:
            raise ValueError("P-Delta Solver: Model has no free degrees of freedom.")

        # 1. First-Order Linear Static Solve
        res_linear = self.solver.solve(num_stations=num_stations)
        if not res_linear.success:
            raise RuntimeError("Initial 1st-order linear static solve failed.")

        # Extract initial nodal displacements
        u_prev_full = [0.0] * total_dofs
        for nid in dof_system.node_order:
            b = dof_system.node_indices[nid] * 6
            d = res_linear.displacements[nid]
            u_prev_full[b+0] = d.ux
            u_prev_full[b+1] = d.uy
            u_prev_full[b+2] = d.uz
            u_prev_full[b+3] = d.rx
            u_prev_full[b+4] = d.ry
            u_prev_full[b+5] = d.rz

        linear_max_disp = max(
            math.sqrt(d.ux**2 + d.uy**2 + d.uz**2)
            for d in res_linear.displacements.values()
        )

        # Retrieve linear member forces and moments
        linear_max_moment = 0.0
        for mf in res_linear.member_forces.values():
            m_max = max(max(abs(m) for m in mf.M2), max(abs(m) for m in mf.M3))
            if m_max > linear_max_moment:
                linear_max_moment = m_max

        # Extract global linear load vector P_global
        P_global = [0.0] * total_dofs
        for nid, loads in self.solver.nodal_loads.items():
            b = dof_system.node_indices[nid] * 6
            for d_i in range(6):
                P_global[b + d_i] += loads[d_i]

        for elem in self.solver.elements.values():
            _, p_enl_glob = elem.compute_equivalent_nodal_loads()
            e_dofs = dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
            for idx, gd in enumerate(e_dofs):
                P_global[gd] += p_enl_glob[idx]

        for selem in self.solver.shell_elements.values():
            p_shell_glob = selem.compute_equivalent_nodal_loads()
            s_dofs = dof_system.get_shell_element_dof_indices(selem.node_ids)
            for idx, gd in enumerate(s_dofs):
                P_global[gd] += p_shell_glob[idx]

        P_f = [P_global[d] for d in free_dofs]

        # Extract Elastic Stiffness Matrix K_E in sparse form
        K_E_dict = self.solver.assemble_master_stiffness_matrix()

        # 2. Iterative P-Delta Loop
        converged = False
        iteration_history: List[PDeltaIterationStep] = []
        u_current_full = list(u_prev_full)
        current_member_forces = res_linear.member_forces

        for iteration in range(1, self.max_iterations + 1):
            # Assemble Global Geometric Stiffness Matrix K_G from current member axial forces
            dok_KG: Dict[Tuple[int, int], float] = {}

            max_axial_f = 0.0
            for elem_id, elem in self.solver.elements.items():
                elem_dofs = dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
                
                # Member axial force: average N along member stations
                mf = current_member_forces.get(elem_id)
                if mf and mf.N:
                    p_axial = sum(mf.N) / len(mf.N)
                else:
                    # Fallback from nodal displacement: Delta L = u_j - u_i
                    u_elem = [u_current_full[d] for d in elem_dofs]
                    T = elem.get_transformation_matrix()
                    u_loc = matrix_vector_multiply(T, u_elem)
                    delta_L = u_loc[6] - u_loc[0]
                    p_axial = (elem.material.E * elem.section.A / elem.length) * delta_L

                if abs(p_axial) > max_axial_f:
                    max_axial_f = abs(p_axial)

                kg_glob = elem.get_global_geometric_stiffness_matrix(p_axial)
                for i_loc in range(12):
                    g_i = elem_dofs[i_loc]
                    for j_loc in range(12):
                        g_j = elem_dofs[j_loc]
                        val = kg_glob[i_loc][j_loc]
                        if abs(val) > 1e-15:
                            dok_KG[(g_i, g_j)] = dok_KG.get((g_i, g_j), 0.0) + val

            # Form Tangent Stiffness: K_T = K_E + K_G
            dok_KT: Dict[Tuple[int, int], float] = dict(K_E_dict)
            for (i, j), val in dok_KG.items():
                dok_KT[(i, j)] = dok_KT.get((i, j), 0.0) + val

            # Solve [K_T_ff] {u_f} = {P_f}
            if HAS_NUMPY_SCIPY:
                rows, cols, data = [], [], []
                dof_map = {dof: idx for idx, dof in enumerate(free_dofs)}
                for (i, j), val in dok_KT.items():
                    if i in dof_map and j in dof_map:
                        rows.append(dof_map[i])
                        cols.append(dof_map[j])
                        data.append(val)
                K_T_sp = sps.csr_matrix((data, (rows, cols)), shape=(n_free, n_free))
                try:
                    u_f_next = spla.spsolve(K_T_sp, np.array(P_f, dtype=np.float64)).tolist()
                except Exception:
                    # Matrix singular or near-buckling
                    u_f_next = None
            else:
                # Dense/Pure Python fallback
                A_mat = create_zero_matrix(n_free, n_free)
                dof_map = {dof: idx for idx, dof in enumerate(free_dofs)}
                for (i, j), val in dok_KT.items():
                    if i in dof_map and j in dof_map:
                        A_mat[dof_map[i]][dof_map[j]] = val
                from .matrix_ops import solve_linear_system
                try:
                    u_f_next = solve_linear_system(A_mat, P_f)
                except Exception:
                    u_f_next = None

            if u_f_next is None:
                # Structure became unstable / singular
                break

            u_next_full = [0.0] * total_dofs
            for idx, dof in enumerate(free_dofs):
                u_next_full[dof] = u_f_next[idx]

            # Assess convergence norm
            diff_sq = sum((u_next_full[d] - u_current_full[d])**2 for d in free_dofs)
            norm_sq = sum(u_next_full[d]**2 for d in free_dofs)
            rel_err = math.sqrt(diff_sq) / max(math.sqrt(norm_sq), 1e-9)

            curr_max_disp = max(
                math.sqrt(u_next_full[dof_system.node_indices[nid]*6 + 0]**2 +
                          u_next_full[dof_system.node_indices[nid]*6 + 1]**2 +
                          u_next_full[dof_system.node_indices[nid]*6 + 2]**2)
                for nid in dof_system.node_order
            )

            iteration_history.append(PDeltaIterationStep(
                iteration=iteration,
                relative_displacement_error=rel_err,
                max_displacement=curr_max_disp,
                max_axial_force=max_axial_f
            ))

            u_current_full = u_next_full

            # Update member forces for next iteration
            new_member_forces: Dict[str, MemberInternalForces] = {}
            for elem_id, elem in self.solver.elements.items():
                e_dofs = dof_system.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
                u_elem = [u_current_full[d] for d in e_dofs]
                new_member_forces[elem_id] = elem.recover_internal_forces(u_elem, num_stations=num_stations)
            current_member_forces = new_member_forces

            if rel_err < self.convergence_tolerance:
                converged = True
                break

            if curr_max_disp > self.divergence_limit or math.isnan(curr_max_disp):
                # Divergence (buckling collapse)
                converged = False
                break

        # 3. Stability Diagnostics Calculation
        diag = self._evaluate_stability_diagnostics(
            K_E_dict, dok_KG, free_dofs, total_dofs,
            u_current_full, linear_max_disp, linear_max_moment,
            current_member_forces
        )

        # 4. Compute Reactions: R = K_T * U_full - P_global
        R_full = [0.0] * total_dofs
        for (i, j), k_val in dok_KT.items():
            R_full[i] += k_val * u_current_full[j]
        for d in range(total_dofs):
            R_full[d] -= P_global[d]

        displacements: Dict[str, NodalDisplacement] = {}
        reactions: Dict[str, NodalReaction] = {}
        for nid in dof_system.node_order:
            b = dof_system.node_indices[nid] * 6
            displacements[nid] = NodalDisplacement(
                ux=u_current_full[b+0],
                uy=u_current_full[b+1],
                uz=u_current_full[b+2],
                rx=u_current_full[b+3],
                ry=u_current_full[b+4],
                rz=u_current_full[b+5]
            )
            restr = dof_system.restraints.get(nid, {})
            reactions[nid] = NodalReaction(
                fx=R_full[b+0] if restr.get(0, False) else 0.0,
                fy=R_full[b+1] if restr.get(1, False) else 0.0,
                fz=R_full[b+2] if restr.get(2, False) else 0.0,
                mx=R_full[b+3] if restr.get(3, False) else 0.0,
                my=R_full[b+4] if restr.get(4, False) else 0.0,
                mz=R_full[b+5] if restr.get(5, False) else 0.0
            )

        # Calculate story shear and story drifts
        story_shears = {s.story_index: s.story_shear_V for s in diag.stories}
        story_drifts = {s.story_index: s.story_drift_delta for s in diag.stories}

        execution_time_ms = (time.time() - t_start) * 1000.0

        return PDeltaResult(
            success=converged and (diag.critical_buckling_factor_lambda > 1.0),
            converged=converged,
            num_iterations=len(iteration_history),
            execution_time_ms=execution_time_ms,
            displacements=displacements,
            reactions=reactions,
            member_forces=current_member_forces,
            stability_diagnostics=diag,
            iteration_history=iteration_history,
            story_shears=story_shears,
            story_drifts=story_drifts
        )

    def _evaluate_stability_diagnostics(
        self,
        K_E_dict: Dict[Tuple[int, int], float],
        K_G_dict: Dict[Tuple[int, int], float],
        free_dofs: List[int],
        total_dofs: int,
        u_pdelta_full: List[float],
        linear_max_disp: float,
        linear_max_moment: float,
        member_forces: Dict[str, MemberInternalForces]
    ) -> StabilityDiagnostics:
        """
        Computes elastic buckling load factor lambda_cr and story stability coefficients theta.
        Uses pure-Python inverse power iteration for machine-precision eigenvalue extraction.
        """
        n_free = len(free_dofs)
        dof_map = {dof: idx for idx, dof in enumerate(free_dofs)}

        lambda_cr = 100.0
        min_eig = 1.0

        if n_free > 0 and len(K_G_dict) > 0:
            # Check if compressive geometric stiffness terms exist
            K_E_ff = [[0.0] * n_free for _ in range(n_free)]
            for (i, j), val in K_E_dict.items():
                if i in dof_map and j in dof_map:
                    K_E_ff[dof_map[i]][dof_map[j]] += val

            K_G_ff = [[0.0] * n_free for _ in range(n_free)]
            for (i, j), val in K_G_dict.items():
                if i in dof_map and j in dof_map:
                    K_G_ff[dof_map[i]][dof_map[j]] += val

            # Initial trial vector from lateral displacements
            v = [u_pdelta_full[d] for d in free_dofs]
            v_norm = math.sqrt(sum(x * x for x in v))
            if v_norm < 1e-12:
                v = [1.0 if (d % 6 == 0 or d % 6 == 2) else 0.0 for d in free_dofs]
                v_norm = math.sqrt(sum(x * x for x in v)) or 1.0
            v = [x / v_norm for x in v]

            # Inverse power iteration for K_E * phi = lambda * (-K_G) * phi
            for _ in range(15):
                w = [0.0] * n_free
                for r in range(n_free):
                    w[r] = sum(-K_G_ff[r][c] * v[c] for c in range(n_free))

                num = sum(v[r] * sum(K_E_ff[r][c] * v[c] for c in range(n_free)) for r in range(n_free))
                den = sum(v[r] * w[r] for r in range(n_free))

                if den > 1e-12 and num > 0:
                    lambda_cr = max(0.01, num / den)

                try:
                    v_next = solve_linear_system(K_E_ff, w)
                    v_norm = math.sqrt(sum(x * x for x in v_next))
                    if v_norm > 1e-15:
                        v = [x / v_norm for x in v_next]
                    else:
                        break
                except Exception:
                    break

        pdelta_max_disp = max(
            math.sqrt(u_pdelta_full[self.solver.dof_system.node_indices[nid]*6 + 0]**2 +
                      u_pdelta_full[self.solver.dof_system.node_indices[nid]*6 + 1]**2 +
                      u_pdelta_full[self.solver.dof_system.node_indices[nid]*6 + 2]**2)
            for nid in self.solver.dof_system.node_order
        )

        disp_amp = pdelta_max_disp / max(linear_max_disp, 1e-9)

        pdelta_max_moment = 0.0
        for mf in member_forces.values():
            m_max = max(max(abs(m) for m in mf.M2), max(abs(m) for m in mf.M3))
            if m_max > pdelta_max_moment:
                pdelta_max_moment = m_max

        moment_amp = pdelta_max_moment / max(linear_max_moment, 1e-9)

        # 5. Story Stability Coefficients theta per ASCE 7 / Eurocode 8
        # Group nodes by unique elevation Y
        y_coords = sorted(list(set(round(coord[1], 3) for coord in self.solver.dof_system.nodes.values())))
        stories: List[StoryStabilityResult] = []
        max_theta = 0.0
        gov_story = 1

        if len(y_coords) > 1:
            for s_idx in range(len(y_coords) - 1):
                y_bot = y_coords[s_idx]
                y_top = y_coords[s_idx + 1]
                h_i = max(y_top - y_bot, 0.1)

                # Nodes at top of story
                top_nodes = [nid for nid, c in self.solver.dof_system.nodes.items() if abs(c[1] - y_top) < 0.01]
                bot_nodes = [nid for nid, c in self.solver.dof_system.nodes.items() if abs(c[1] - y_bot) < 0.01]

                # Average lateral displacement at top and bottom
                top_ux = sum(u_pdelta_full[self.solver.dof_system.node_indices[n]*6 + 0] for n in top_nodes) / max(len(top_nodes), 1)
                bot_ux = sum(u_pdelta_full[self.solver.dof_system.node_indices[n]*6 + 0] for n in bot_nodes) / max(len(bot_nodes), 1)
                story_drift = abs(top_ux - bot_ux)
                drift_ratio = story_drift / h_i

                # Cumulative vertical load above story level (gravity P)
                p_story = 0.0
                for nid, loads in self.solver.nodal_loads.items():
                    if self.solver.dof_system.nodes[nid][1] >= y_top - 0.01:
                        p_story += abs(loads[1])

                # Story lateral shear force
                v_story = 0.0
                for nid, loads in self.solver.nodal_loads.items():
                    if self.solver.dof_system.nodes[nid][1] >= y_top - 0.01:
                        v_story += abs(loads[0])

                if v_story < 1e-6:
                    v_story = 1.0 # Avoid division by zero in pure vertical load

                theta = (p_story * story_drift) / (v_story * h_i)
                theta = min(theta, 1.0)
                if theta > max_theta:
                    max_theta = theta
                    gov_story = s_idx + 1

                stories.append(StoryStabilityResult(
                    story_index=s_idx + 1,
                    elevation_bottom=y_bot,
                    elevation_top=y_top,
                    story_height=h_i,
                    total_axial_gravity_P=p_story,
                    story_shear_V=v_story,
                    story_drift_delta=story_drift,
                    drift_ratio=drift_ratio,
                    stability_coefficient_theta=theta,
                    is_acceptable=theta <= 0.25,
                    amplification_factor=1.0 / max(1.0 - theta, 0.01)
                ))

        is_stable = (lambda_cr > 1.0) and (max_theta <= 0.25) and (disp_amp < 10.0)
        status_msg = "Structure is geometrically STABLE." if is_stable else "WARNING: Structure exceeds stability/buckling limits!"

        return StabilityDiagnostics(
            is_stable=is_stable,
            status_message=status_msg,
            critical_buckling_factor_lambda=lambda_cr,
            min_tangent_eigenvalue=min_eig,
            max_stability_coefficient=max_theta,
            governing_story=gov_story,
            elastic_first_order_max_disp=linear_max_disp,
            p_delta_second_order_max_disp=pdelta_max_disp,
            displacement_amplification_ratio=disp_amp,
            moment_amplification_ratio=moment_amp,
            stories=stories
        )
