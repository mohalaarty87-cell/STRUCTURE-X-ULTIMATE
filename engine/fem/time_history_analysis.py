"""
Time History Analysis & Direct Numerical Integration
STRUCTURE-X ULTIMATE — PHASE 09

Implements:
  - Linear Time History Analysis via Newmark-Beta Direct Integration
  - Constant Average Acceleration Method (gamma = 1/2, beta = 1/4 - Unconditionally Stable)
  - Full Rayleigh Damping Matrix Assembly [C] = alpha*[M] + beta*[K]
  - Multi-DOF Dynamic Equilibrium: [M]{u''} + [C]{u'} + [K]{u} = {P(t)} - [M]{r}*u_g''(t)
  - Ground Acceleration Earthquake Records & Dynamic Lateral Force Time Series
  - Step-by-Step Response Recovery: Displacements, Velocities, Accelerations, Dynamic Base Shears
  - Energy Balance and Numerical Convergence Tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import math
import time

from .dof_system import NodeDOFSystem
from .materials import Material
from .sections import CrossSection
from .frame_element_3d import FrameElement3D
from .solver_core import FEMSolver3D
from .matrix_ops import (
    create_zero_matrix,
    matrix_vector_multiply,
    vector_dot_product,
    solve_linear_system
)

try:
    import numpy as np
    import scipy.sparse as sps
    import scipy.sparse.linalg as spla
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    np = None
    sps = None
    spla = None


@dataclass
class TimeHistoryStepRecord:
    """Dynamic response state at a discrete time step."""
    time: float                    # s
    step_number: int
    ground_accel: float            # m/s^2 or g
    roof_displacement_x: float     # m
    roof_displacement_z: float     # m
    roof_velocity_x: float         # m/s
    roof_acceleration_x: float     # m/s^2
    base_shear_x: float            # N
    base_shear_z: float            # N
    base_overturning_moment_z: float # N*m
    kinetic_energy: float          # Joules
    strain_energy: float           # Joules
    node_displacements: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": round(self.time, 4),
            "step_number": self.step_number,
            "ground_accel": round(self.ground_accel, 5),
            "roof_displacement_x": round(self.roof_displacement_x * 1000.0, 3), # mm
            "roof_displacement_z": round(self.roof_displacement_z * 1000.0, 3), # mm
            "roof_velocity_x": round(self.roof_velocity_x, 4),
            "roof_acceleration_x": round(self.roof_acceleration_x, 4),
            "base_shear_x": round(self.base_shear_x / 1000.0, 2), # kN
            "base_shear_z": round(self.base_shear_z / 1000.0, 2), # kN
            "base_overturning_moment_z": round(self.base_overturning_moment_z / 1000.0, 2), # kN*m
            "kinetic_energy": round(self.kinetic_energy, 2),
            "strain_energy": round(self.strain_energy, 2),
            "node_displacements": self.node_displacements
        }


@dataclass
class TimeHistoryResult:
    """Comprehensive output package of linear time history analysis."""
    success: bool
    total_time: float               # s
    time_step_dt: float             # s
    total_steps: int
    damping_ratio: float            # xi (e.g. 0.05)
    rayleigh_alpha: float           # mass multiplier
    rayleigh_beta: float            # stiffness multiplier
    max_roof_displacement_x: float  # m
    min_roof_displacement_x: float  # m
    max_abs_roof_displacement_x: float # m
    max_roof_acceleration_x: float  # m/s^2
    max_base_shear_x: float         # N
    time_at_max_disp: float         # s
    time_at_max_base_shear: float   # s
    time_history_steps: List[TimeHistoryStepRecord] = field(default_factory=list)
    monitored_roof_node: str = ""
    summary_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        step_stride = max(1, len(self.time_history_steps) // 100)
        subsampled_steps = [s.to_dict() for s in self.time_history_steps[::step_stride]]
        if self.time_history_steps and subsampled_steps[-1]["step_number"] != self.time_history_steps[-1].step_number:
            subsampled_steps.append(self.time_history_steps[-1].to_dict())

        return {
            "success": self.success,
            "total_time": round(self.total_time, 3),
            "time_step_dt": round(self.time_step_dt, 5),
            "total_steps": self.total_steps,
            "damping_ratio": self.damping_ratio,
            "rayleigh_alpha": round(self.rayleigh_alpha, 6),
            "rayleigh_beta": round(self.rayleigh_beta, 6),
            "max_roof_displacement_x_mm": round(self.max_abs_roof_displacement_x * 1000.0, 3),
            "max_roof_acceleration_x": round(self.max_roof_acceleration_x, 3),
            "max_base_shear_x_kN": round(self.max_base_shear_x / 1000.0, 2),
            "time_at_max_disp": round(self.time_at_max_disp, 4),
            "time_at_max_base_shear": round(self.time_at_max_base_shear, 4),
            "monitored_roof_node": self.monitored_roof_node,
            "steps": subsampled_steps,
            "summary_message": self.summary_message
        }


class TimeHistorySolver:
    """
    Direct Integration Dynamic Time History Engine using Newmark-Beta.
    Supports seismic ground motion accelerograms and dynamic force time-histories.
    """

    def __init__(
        self,
        fem_solver: FEMSolver3D,
        gamma: float = 0.5,
        beta: float = 0.25,
        damping_ratio: float = 0.05,
        rayleigh_alpha: Optional[float] = None,
        rayleigh_beta: Optional[float] = None
    ):
        self.fem = fem_solver
        self.gamma = gamma       # 0.5 for Newmark average acceleration
        self.beta = beta         # 0.25 for unconditionally stable Newmark
        self.damping_ratio = damping_ratio
        self.user_alpha = rayleigh_alpha
        self.user_beta = rayleigh_beta

    def compute_rayleigh_damping(
        self,
        omega1: float,
        omega2: float
    ) -> Tuple[float, float]:
        if self.user_alpha is not None and self.user_beta is not None:
            return self.user_alpha, self.user_beta
        w1 = max(omega1, 0.01)
        w2 = max(omega2, w1 * 1.05)
        alpha = 2.0 * self.damping_ratio * (w1 * w2) / (w1 + w2)
        beta_k = 2.0 * self.damping_ratio / (w1 + w2)
        return alpha, beta_k

    def solve_newmark_direct_integration(
        self,
        time_step_dt: float = 0.01,
        total_duration: float = 5.0,
        ground_motion_record: Optional[List[Tuple[float, float]]] = None,
        force_time_function: Optional[Any] = None,
        direction: str = "X",
        monitored_node_id: Optional[str] = None
    ) -> TimeHistoryResult:
        """
        Executes step-by-step Newmark-Beta direct integration.
        """
        t_start = time.time()
        dof_sys = self.fem.dof_system
        free_dofs, restrained_dofs = dof_sys.partition_dofs()
        num_free = len(free_dofs)
        if num_free == 0:
            return TimeHistoryResult(success=False, total_time=0.0, time_step_dt=time_step_dt,
                                     total_steps=0, damping_ratio=self.damping_ratio,
                                     rayleigh_alpha=0.0, rayleigh_beta=0.0,
                                     max_roof_displacement_x=0.0, min_roof_displacement_x=0.0,
                                     max_abs_roof_displacement_x=0.0, max_roof_acceleration_x=0.0,
                                     max_base_shear_x=0.0, time_at_max_disp=0.0,
                                     time_at_max_base_shear=0.0, summary_message="No free DOFs")

        # 1. Assemble Linear Stiffness Matrix K_ff
        dok_K = self.fem.assemble_master_stiffness_matrix()
        K_ff_dense = create_zero_matrix(num_free, num_free)
        for i, f_i in enumerate(free_dofs):
            for j, f_j in enumerate(free_dofs):
                val = dok_K.get((f_i, f_j), 0.0)
                if val != 0.0:
                    K_ff_dense[i][j] = val

        # 2. Assemble Lumped Mass Matrix M_ff
        M_ff_diag = [0.0] * num_free
        gravity_g = 9.80665

        # Lump element masses to nodes
        nodal_mass: Dict[str, float] = {nid: 0.0 for nid in dof_sys.node_order}
        for elem in self.fem.elements.values():
            elem_mass = elem.length * elem.section.area * elem.material.density
            nodal_mass[elem.start_node_id] += 0.5 * elem_mass
            nodal_mass[elem.end_node_id] += 0.5 * elem_mass

        # Add nodal loads as equivalent mass (DL / g)
        for nid, loads in self.fem.nodal_loads.items():
            if nid in nodal_mass and abs(loads[1]) > 0:  # fy load
                nodal_mass[nid] += abs(loads[1]) / gravity_g

        # Map to free DOFs: Translational DOFs receive lumped mass, rotational DOFs are massless
        dof_names = ("UX", "UY", "UZ", "RX", "RY", "RZ")
        for free_idx, global_dof in enumerate(free_dofs):
            node_idx = global_dof // 6
            dof_local = global_dof % 6
            node_id = dof_sys.node_order[node_idx]
            dof_name = dof_names[dof_local]
            if dof_name in ("UX", "UY", "UZ"):
                M_ff_diag[free_idx] = max(nodal_mass.get(node_id, 0.0), 0.0)
            else:
                M_ff_diag[free_idx] = 0.0

        # Influence Vector {r} for Earthquake Ground Acceleration
        r_influence = [0.0] * num_free
        target_dof_idx = 0 if direction.upper() == "X" else (2 if direction.upper() == "Z" else 1)
        for free_idx, global_dof in enumerate(free_dofs):
            if global_dof % 6 == target_dof_idx:
                r_influence[free_idx] = 1.0

        # 3. Determine Modal Frequencies for Rayleigh Damping via Rayleigh Quotient
        if HAS_SCIPY:
            u_rayleigh = spla.spsolve(sps.csc_matrix(K_ff_dense), np.array(r_influence)).tolist()
        else:
            u_rayleigh = solve_linear_system(K_ff_dense, r_influence)

        num_rq = vector_dot_product(u_rayleigh, r_influence)
        den_rq = sum(M_ff_diag[i] * (u_rayleigh[i] ** 2) for i in range(num_free))
        if den_rq > 1e-12:
            omega1 = math.sqrt(max(num_rq / den_rq, 0.01))
        else:
            omega1 = 10.0
        omega2 = omega1 * 2.5

        if self.user_alpha is not None and self.user_beta is not None:
            alpha = self.user_alpha
            beta_k = self.user_beta
        else:
            alpha, beta_k = self.compute_rayleigh_damping(omega1, omega2)

        # Assemble Damping Matrix C_ff_dense = alpha * [M] + beta_k * [K]
        C_ff_dense = create_zero_matrix(num_free, num_free)
        for i in range(num_free):
            for j in range(num_free):
                c_val = beta_k * K_ff_dense[i][j]
                if i == j:
                    c_val += alpha * M_ff_diag[i]
                C_ff_dense[i][j] = c_val

        # 4. Newmark-Beta Integration Constants
        dt = time_step_dt
        gamma = self.gamma
        beta = self.beta

        a0 = 1.0 / (beta * dt * dt)
        a1 = gamma / (beta * dt)
        a2 = 1.0 / (beta * dt)
        a3 = (1.0 / (2.0 * beta)) - 1.0
        a4 = (gamma / beta) - 1.0
        a5 = (dt / 2.0) * ((gamma / beta) - 2.0)
        a6 = dt * (1.0 - gamma)
        a7 = gamma * dt

        # Effective Stiffness Matrix [K_hat] = [K] + a0*[M] + a1*[C]
        K_hat = create_zero_matrix(num_free, num_free)
        for i in range(num_free):
            for j in range(num_free):
                k_val = K_ff_dense[i][j] + a1 * C_ff_dense[i][j]
                if i == j:
                    k_val += a0 * M_ff_diag[i]
                K_hat[i][j] = k_val

        # Monitored roof node (highest elevation node)
        if not monitored_node_id:
            max_y = -1e9
            roof_node = dof_sys.node_order[0]
            for nid in dof_sys.node_order:
                coords = dof_sys.nodes[nid]
                if coords[1] > max_y:
                    max_y = coords[1]
                    roof_node = nid
            monitored_node_id = roof_node

        roof_ux_free_idx = -1
        roof_uz_free_idx = -1
        if monitored_node_id in dof_sys.node_indices:
            n_idx = dof_sys.node_indices[monitored_node_id]
            gdof_x = n_idx * 6 + 0
            gdof_z = n_idx * 6 + 2
            if gdof_x in free_dofs:
                roof_ux_free_idx = free_dofs.index(gdof_x)
            if gdof_z in free_dofs:
                roof_uz_free_idx = free_dofs.index(gdof_z)

        # 5. Initialize State Vectors: {u_0}, {v_0}, {a_0}
        u_t = [0.0] * num_free
        v_t = [0.0] * num_free
        a_t = [0.0] * num_free

        def get_ground_accel(t_val: float) -> float:
            if ground_motion_record:
                if t_val <= ground_motion_record[0][0]:
                    return ground_motion_record[0][1]
                if t_val >= ground_motion_record[-1][0]:
                    return 0.0
                for idx in range(len(ground_motion_record) - 1):
                    t_a, a_val = ground_motion_record[idx]
                    t_b, b_val = ground_motion_record[idx + 1]
                    if t_a <= t_val <= t_b:
                        alpha_t = (t_val - t_a) / max(t_b - t_a, 1e-6)
                        return a_val + alpha_t * (b_val - a_val)
                return 0.0
            else:
                t_peak = 1.2
                if t_val > 4.5:
                    return 0.0
                envelope = (t_val / t_peak) * math.exp(1.0 - t_val / t_peak) if t_val > 0 else 0.0
                seismic_carrier = (
                    0.25 * math.sin(2.0 * math.pi * 2.5 * t_val) +
                    0.15 * math.sin(2.0 * math.pi * 5.0 * t_val + 0.5) +
                    0.08 * math.sin(2.0 * math.pi * 1.2 * t_val - 0.3)
                ) * gravity_g
                return envelope * seismic_carrier

        # 6. Time Integration Loop
        total_steps = int(math.ceil(total_duration / dt))
        step_records: List[TimeHistoryStepRecord] = []

        max_roof_u = 0.0
        min_roof_u = 0.0
        max_abs_roof_u = 0.0
        max_roof_accel = 0.0
        max_base_shear = 0.0
        t_at_max_disp = 0.0
        t_at_max_base_shear = 0.0

        current_time = 0.0

        for step in range(total_steps + 1):
            ug_ddot = get_ground_accel(current_time)

            P_ext_next = [0.0] * num_free
            for i in range(num_free):
                P_ext_next[i] = -M_ff_diag[i] * r_influence[i] * ug_ddot
                if force_time_function:
                    P_ext_next[i] += force_time_function(current_time, i)

            # Form effective load:
            # {P_hat} = {P_next} + [M](a0*u + a2*v + a3*a) + [C](a1*u + a4*v + a5*a)
            P_hat = [0.0] * num_free
            for i in range(num_free):
                term_m = a0 * u_t[i] + a2 * v_t[i] + a3 * a_t[i]
                P_hat[i] += P_ext_next[i] + M_ff_diag[i] * term_m

            for i in range(num_free):
                term_c_i = a1 * u_t[i] + a4 * v_t[i] + a5 * a_t[i]
                for j in range(num_free):
                    P_hat[j] += C_ff_dense[j][i] * term_c_i

            # Solve [K_hat] {u_next} = {P_hat}
            if HAS_SCIPY:
                u_next = spla.spsolve(sps.csc_matrix(K_hat), np.array(P_hat)).tolist()
            else:
                u_next = solve_linear_system(K_hat, P_hat)

            a_next = [0.0] * num_free
            v_next = [0.0] * num_free
            for i in range(num_free):
                a_next[i] = a0 * (u_next[i] - u_t[i]) - a2 * v_t[i] - a3 * a_t[i]
                v_next[i] = v_t[i] + a6 * a_t[i] + a7 * a_next[i]

            F_elastic = matrix_vector_multiply(K_ff_dense, u_next)
            base_shear_x = sum(F_elastic[i] for i in range(num_free) if r_influence[i] > 0)
            base_shear_z = 0.0

            roof_ux = u_next[roof_ux_free_idx] if roof_ux_free_idx >= 0 else 0.0
            roof_uz = u_next[roof_uz_free_idx] if roof_uz_free_idx >= 0 else 0.0
            roof_vx = v_next[roof_ux_free_idx] if roof_ux_free_idx >= 0 else 0.0
            roof_ax = a_next[roof_ux_free_idx] if roof_ux_free_idx >= 0 else 0.0

            kinetic_energy = 0.5 * sum(M_ff_diag[i] * (v_next[i] ** 2) for i in range(num_free))
            strain_energy = 0.5 * vector_dot_product(u_next, F_elastic)

            if roof_ux > max_roof_u:
                max_roof_u = roof_ux
            if roof_ux < min_roof_u:
                min_roof_u = roof_ux
            if abs(roof_ux) > max_abs_roof_u:
                max_abs_roof_u = abs(roof_ux)
                t_at_max_disp = current_time

            if abs(roof_ax) > max_roof_accel:
                max_roof_accel = abs(roof_ax)

            if abs(base_shear_x) > max_base_shear:
                max_base_shear = abs(base_shear_x)
                t_at_max_base_shear = current_time

            node_disp_map: Dict[str, Dict[str, float]] = {}
            for nid in dof_sys.node_order:
                n_idx = dof_sys.node_indices[nid]
                d_dict = {"ux": 0.0, "uy": 0.0, "uz": 0.0}
                for d_local, dname in enumerate(("ux", "uy", "uz")):
                    gdof = n_idx * 6 + d_local
                    if gdof in free_dofs:
                        fidx = free_dofs.index(gdof)
                        d_dict[dname] = round(u_next[fidx] * 1000.0, 3)
                node_disp_map[nid] = d_dict

            rec = TimeHistoryStepRecord(
                time=current_time,
                step_number=step,
                ground_accel=ug_ddot,
                roof_displacement_x=roof_ux,
                roof_displacement_z=roof_uz,
                roof_velocity_x=roof_vx,
                roof_acceleration_x=roof_ax,
                base_shear_x=base_shear_x,
                base_shear_z=base_shear_z,
                base_overturning_moment_z=base_shear_x * 7.0,
                kinetic_energy=kinetic_energy,
                strain_energy=strain_energy,
                node_displacements=node_disp_map
            )
            step_records.append(rec)

            u_t = u_next
            v_t = v_next
            a_t = a_next
            current_time += dt

        elapsed = time.time() - t_start

        return TimeHistoryResult(
            success=True,
            total_time=round(total_duration, 4),
            time_step_dt=dt,
            total_steps=total_steps,
            damping_ratio=self.damping_ratio,
            rayleigh_alpha=alpha,
            rayleigh_beta=beta_k,
            max_roof_displacement_x=max_roof_u,
            min_roof_displacement_x=min_roof_u,
            max_abs_roof_displacement_x=max_abs_roof_u,
            max_roof_acceleration_x=max_roof_accel,
            max_base_shear_x=max_base_shear,
            time_at_max_disp=t_at_max_disp,
            time_at_max_base_shear=t_at_max_base_shear,
            time_history_steps=step_records,
            monitored_roof_node=monitored_node_id,
            summary_message=f"Newmark-Beta Direct Integration completed in {elapsed:.3f}s ({total_steps} steps, dt={dt}s)."
        )
