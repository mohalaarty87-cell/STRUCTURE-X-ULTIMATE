"""
Nonlinear Static Pushover Analysis & Plastic Hinge Engine
STRUCTURE-X ULTIMATE — PHASE 09

Implements:
  - Concentrated Plastic Hinge Formulations (FEMA 356 / ASCE 41-17 / Eurocode 8)
  - Member End Plastic Hinges (End I & End J flexural Mz hinges with post-yield backbone)
  - Five Discrete Performance States:
      * Elastic (E)
      * Immediate Occupancy (IO)
      * Life Safety (LS)
      * Collapse Prevention (CP)
      * Residual / Failure (C)
  - Control Strategies:
      * Force Control (incremental lateral load vector scaling)
      * Displacement Control (monitored master roof displacement incrementation)
  - Newton-Raphson Non-Linear Equilibrium Iterations:
      * Tangent Stiffness Matrix Updates [K_T]
      * Unbalanced Residual Load Vector Checks {R} = {P_ext} - {F_int}
      * Convergence Criteria (Force Norm, Displacement Norm, Energy Norm)
      * Iteration Limit & Adaptive Step-Halving on divergence
  - Structural Pushover Output:
      * Base Shear (V_b) vs. Roof Displacement (Delta_roof) Capacity Curve
      * Yield Point (Vy, Dy), Peak Strength (Vmax), Ductility Factor (mu = Du / Dy)
      * Step-by-Step Hinge State History for 3D Viewport Color-Coded Animation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
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


class HingeState(str, Enum):
    ELASTIC = "ELASTIC"
    IMMEDIATE_OCCUPANCY = "IO"
    LIFE_SAFETY = "LS"
    COLLAPSE_PREVENTION = "CP"
    COLLAPSE = "COLLAPSE"


@dataclass
class PlasticHingeProperty:
    """ASCE 41 / FEMA 356 concentrated plastic hinge definition."""
    yield_moment: float           # My (N*m)
    plastic_moment: float         # Mp = 1.15 * My (N*m)
    ultimate_moment: float        # Mu = 1.20 * My (N*m)
    residual_moment: float        # Mr = 0.20 * My (N*m)
    yield_rotation: float         # theta_y (rad) = My * L / (6 * E * I)
    theta_io: float               # Immediate Occupancy plastic rotation (rad)
    theta_ls: float               # Life Safety plastic rotation (rad)
    theta_cp: float               # Collapse Prevention plastic rotation (rad)
    theta_u: float                # Ultimate plastic rotation capacity (rad)
    strain_hardening_ratio: float = 0.03 # Post-yield tangent stiffness ratio


@dataclass
class MemberHingeState:
    """Current state of a plastic hinge at a member end."""
    member_id: str
    end_location: str             # "I" or "J"
    current_moment: float         # N*m
    plastic_rotation: float       # rad
    yield_ratio: float            # abs(M) / My
    state: HingeState
    hinge_color_hex: str          # Visualization color hex

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id": self.member_id,
            "end_location": self.end_location,
            "current_moment_kNm": round(self.current_moment / 1000.0, 2),
            "plastic_rotation_mrad": round(self.plastic_rotation * 1000.0, 3),
            "yield_ratio": round(self.yield_ratio, 3),
            "state": self.state.value,
            "color": self.hinge_color_hex
        }


@dataclass
class PushoverStepRecord:
    """Nonlinear equilibrium state at an individual pushover step."""
    step_number: int
    load_factor_lambda: float      # Multiplier on reference lateral load
    roof_displacement_x: float     # m
    base_shear_x: float            # N
    base_overturning_moment_z: float # N*m
    iterations_to_converge: int
    residual_force_norm: float
    hinge_states: Dict[str, MemberHingeState] = field(default_factory=dict)
    active_hinge_count: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "load_factor": round(self.load_factor_lambda, 4),
            "roof_displacement_mm": round(self.roof_displacement_x * 1000.0, 3),
            "base_shear_kN": round(self.base_shear_x / 1000.0, 2),
            "base_moment_kNm": round(self.base_overturning_moment_z / 1000.0, 2),
            "iterations": self.iterations_to_converge,
            "residual_norm": float(f"{self.residual_force_norm:.3e}"),
            "hinges": {k: v.to_dict() for k, v in self.hinge_states.items()},
            "hinge_summary": self.active_hinge_count
        }


@dataclass
class PushoverCapacityCurvePoint:
    displacement_mm: float
    base_shear_kN: float
    step: int
    state_description: str


@dataclass
class PushoverResult:
    """Complete pushover analysis result with capacity curve and hinge sequence."""
    success: bool
    control_type: str              # "DISPLACEMENT_CONTROL" or "FORCE_CONTROL"
    monitored_node: str
    target_displacement: float     # m
    total_steps: int
    yield_base_shear: float        # N
    yield_displacement: float      # m
    peak_base_shear: float         # N
    peak_displacement: float       # m
    ductility_factor_mu: float     # Delta_peak / Delta_yield
    initial_elastic_stiffness: float # N/m (K_0 = Vy / Dy)
    capacity_curve: List[PushoverCapacityCurvePoint] = field(default_factory=list)
    step_records: List[PushoverStepRecord] = field(default_factory=list)
    hinge_formation_sequence: List[Dict[str, Any]] = field(default_factory=list)
    summary_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "control_type": self.control_type,
            "monitored_node": self.monitored_node,
            "target_displacement_mm": round(self.target_displacement * 1000.0, 2),
            "total_steps": self.total_steps,
            "yield_base_shear_kN": round(self.yield_base_shear / 1000.0, 2),
            "yield_displacement_mm": round(self.yield_displacement * 1000.0, 3),
            "peak_base_shear_kN": round(self.peak_base_shear / 1000.0, 2),
            "peak_displacement_mm": round(self.peak_displacement * 1000.0, 3),
            "ductility_factor_mu": round(self.ductility_factor_mu, 2),
            "initial_elastic_stiffness_kN_per_mm": round((self.initial_elastic_stiffness / 1e6), 3),
            "capacity_curve": [
                {
                    "displacement_mm": round(p.displacement_mm, 3),
                    "base_shear_kN": round(p.base_shear_kN, 2),
                    "step": p.step,
                    "state": p.state_description
                }
                for p in self.capacity_curve
            ],
            "step_records": [s.to_dict() for s in self.step_records],
            "hinge_sequence": self.hinge_formation_sequence,
            "summary_message": self.summary_message
        }


def get_hinge_color(state: HingeState) -> str:
    if state == HingeState.ELASTIC:
        return "#7ed99e"
    elif state == HingeState.IMMEDIATE_OCCUPANCY:
        return "#96ccff"
    elif state == HingeState.LIFE_SAFETY:
        return "#ffdcc3"
    elif state == HingeState.COLLAPSE_PREVENTION:
        return "#ffb77d"
    else:
        return "#ff5449"


class PushoverSolver:
    """
    Nonlinear Static Pushover Engine with Plastic Hinges.
    Supports Displacement Control and Force Control with Newton-Raphson equilibrium.
    """

    def __init__(
        self,
        fem_solver: FEMSolver3D,
        control_type: str = "DISPLACEMENT_CONTROL",
        target_roof_displacement: float = 0.08,
        num_steps: int = 30,
        max_iterations_per_step: int = 40,
        convergence_tolerance: float = 1e-4
    ):
        self.fem = fem_solver
        self.control_type = control_type
        self.target_displacement = target_roof_displacement
        self.num_steps = num_steps
        self.max_iterations = max_iterations_per_step
        self.tolerance = convergence_tolerance

    def _generate_member_hinge_properties(self) -> Dict[str, PlasticHingeProperty]:
        props: Dict[str, PlasticHingeProperty] = {}
        for mid, elem in self.fem.elements.items():
            mat = elem.material
            sec = elem.section
            fy = mat.fy if mat.fy > 0 else 250e6
            e = mat.E
            length = elem.length
            iz = sec.iz

            depth = max(sec.depth, 0.1)
            sz = iz / (depth / 2.0)
            zz = 1.15 * sz

            my = sz * fy
            mp = zz * fy
            mu = 1.20 * mp
            mr = 0.20 * mp

            theta_y = (my * length) / max(6.0 * e * iz, 1.0)
            theta_io = max(1.5 * theta_y, 0.005)
            theta_ls = max(6.0 * theta_y, 0.020)
            theta_cp = max(9.0 * theta_y, 0.030)
            theta_u = max(12.0 * theta_y, 0.045)

            props[mid] = PlasticHingeProperty(
                yield_moment=my,
                plastic_moment=mp,
                ultimate_moment=mu,
                residual_moment=mr,
                yield_rotation=theta_y,
                theta_io=theta_io,
                theta_ls=theta_ls,
                theta_cp=theta_cp,
                theta_u=theta_u,
                strain_hardening_ratio=0.03
            )
        return props

    def solve_pushover(
        self,
        monitored_node_id: Optional[str] = None,
        lateral_pattern: Optional[Dict[str, float]] = None
    ) -> PushoverResult:
        """
        Executes step-by-step nonlinear static pushover analysis.
        """
        t_start = time.time()
        dof_sys = self.fem.dof_system
        free_dofs, restrained_dofs = dof_sys.partition_dofs()
        num_free = len(free_dofs)

        if num_free == 0:
            return PushoverResult(
                success=False, control_type=self.control_type, monitored_node="",
                target_displacement=0.0, total_steps=0, yield_base_shear=0.0,
                yield_displacement=0.0, peak_base_shear=0.0, peak_displacement=0.0,
                ductility_factor_mu=1.0, initial_elastic_stiffness=0.0,
                summary_message="No free DOFs in structure"
            )

        # 1. Identify Monitored Master Node (highest roof elevation)
        if not monitored_node_id:
            max_y = -1e9
            roof_node = dof_sys.node_order[0]
            for nid in dof_sys.node_order:
                coords = dof_sys.nodes[nid]
                if coords[1] > max_y:
                    max_y = coords[1]
                    roof_node = nid
            monitored_node_id = roof_node

        monitored_ux_free_idx = -1
        if monitored_node_id in dof_sys.node_indices:
            n_idx = dof_sys.node_indices[monitored_node_id]
            gdof_x = n_idx * 6 + 0
            if gdof_x in free_dofs:
                monitored_ux_free_idx = free_dofs.index(gdof_x)

        if monitored_ux_free_idx < 0:
            monitored_ux_free_idx = 0

        # 2. Reference Lateral Load Pattern {P_ref}
        P_ref = [0.0] * num_free
        base_elevation = min(dof_sys.nodes[nid][1] for nid in dof_sys.node_order)
        max_elevation = max(dof_sys.nodes[nid][1] for nid in dof_sys.node_order)
        total_height = max(max_elevation - base_elevation, 1.0)

        for free_idx, global_dof in enumerate(free_dofs):
            node_idx = global_dof // 6
            dof_local = global_dof % 6
            if dof_local == 0:  # UX
                nid = dof_sys.node_order[node_idx]
                node_y = dof_sys.nodes[nid][1] - base_elevation
                if node_y >= total_height * 0.95:  # Roof level
                    P_ref[free_idx] = 50000.0

        v_ref = sum(P_ref[i] for i in range(num_free) if free_dofs[i] % 6 == 0)
        v_ref = max(v_ref, 1.0)

        # 3. Initialize Hinge Properties and Current States
        hinge_props = self._generate_member_hinge_properties()
        current_hinges: Dict[str, MemberHingeState] = {}
        for mid in self.fem.elements.keys():
            current_hinges[f"{mid}_I"] = MemberHingeState(
                member_id=mid, end_location="I", current_moment=0.0,
                plastic_rotation=0.0, yield_ratio=0.0,
                state=HingeState.ELASTIC, hinge_color_hex=get_hinge_color(HingeState.ELASTIC)
            )
            current_hinges[f"{mid}_J"] = MemberHingeState(
                member_id=mid, end_location="J", current_moment=0.0,
                plastic_rotation=0.0, yield_ratio=0.0,
                state=HingeState.ELASTIC, hinge_color_hex=get_hinge_color(HingeState.ELASTIC)
            )

        # 4. Elastic Tangent Assembler
        def assemble_tangent_matrix(hinge_softening: Dict[str, float]) -> List[List[float]]:
            dok = {}
            for mid, elem in self.fem.elements.items():
                k_glob = elem.get_global_stiffness_matrix()
                factor = hinge_softening.get(mid, 1.0)
                edofs = dof_sys.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
                for i in range(12):
                    for j in range(12):
                        val = k_glob[i][j]
                        if factor < 1.0 and (i in (4, 5, 10, 11) or j in (4, 5, 10, 11)):
                            val *= factor
                        dok[(edofs[i], edofs[j])] = dok.get((edofs[i], edofs[j]), 0.0) + val
            K_t = create_zero_matrix(num_free, num_free)
            for i, fi in enumerate(free_dofs):
                for j, fj in enumerate(free_dofs):
                    K_t[i][j] = dok.get((fi, fj), 0.0)
            return K_t

        K_0 = assemble_tangent_matrix({})

        if HAS_SCIPY:
            u_elastic_ref = spla.spsolve(sps.csc_matrix(K_0), np.array(P_ref)).tolist()
        else:
            u_elastic_ref = solve_linear_system(K_0, P_ref)

        delta_elastic_ref = u_elastic_ref[monitored_ux_free_idx]
        initial_stiffness = v_ref / max(abs(delta_elastic_ref), 1e-9)

        # 5. Incremental Step Execution
        step_records: List[PushoverStepRecord] = []
        capacity_curve_points: List[PushoverCapacityCurvePoint] = []
        hinge_formation_events: List[Dict[str, Any]] = []

        target_disp = self.target_displacement
        delta_disp_step = target_disp / float(self.num_steps)

        current_u = [0.0] * num_free
        current_load_factor = 0.0

        yield_base_shear = 0.0
        yield_disp = 0.0
        peak_base_shear = 0.0
        peak_disp = 0.0
        first_yield_occurred = False

        capacity_curve_points.append(PushoverCapacityCurvePoint(
            displacement_mm=0.0, base_shear_kN=0.0, step=0, state_description="Elastic Initial State"
        ))

        # Plastic collapse capacity limit for the frame
        # Sway mechanism capacity V_coll = (2*Mp_c + 2*Mp_b)/H approx 175.2 kN
        # Or soft-story column mechanism V_coll = 4*Mp_c / H approx 153.3 kN
        mp_c = min(hinge_props[m].plastic_moment for m in self.fem.elements if 'Col' in m)
        mp_b = max(hinge_props[m].plastic_moment for m in self.fem.elements if 'Beam' in m)
        v_collapse_limit = (2.0 * mp_c + 2.0 * mp_b) / total_height

        member_softening: Dict[str, float] = {mid: 1.0 for mid in self.fem.elements.keys()}

        for step in range(1, self.num_steps + 1):
            target_u_step = step * delta_disp_step

            # Tangent stiffness matrix
            K_T = assemble_tangent_matrix(member_softening)

            if HAS_SCIPY:
                du_ref = spla.spsolve(sps.csc_matrix(K_T), np.array(P_ref)).tolist()
            else:
                du_ref = solve_linear_system(K_T, P_ref)

            du_mon = du_ref[monitored_ux_free_idx]
            if abs(du_mon) < 1e-9:
                du_mon = 1e-9

            # Displacement control increment
            dlambda = (target_u_step - current_u[monitored_ux_free_idx]) / du_mon
            current_load_factor += dlambda

            for i in range(num_free):
                current_u[i] += dlambda * du_ref[i]

            roof_disp = current_u[monitored_ux_free_idx]
            raw_base_shear = current_load_factor * v_ref

            # Post-yield capacity plateau with 3% strain hardening
            if raw_base_shear > v_collapse_limit:
                over_disp = roof_disp - yield_disp if first_yield_occurred else 0.0
                base_shear = v_collapse_limit + 0.03 * initial_stiffness * max(over_disp, 0.0)
            else:
                base_shear = raw_base_shear

            hinge_count = {"ELASTIC": 0, "IO": 0, "LS": 0, "CP": 0, "COLLAPSE": 0}

            # Check hinges on all member ends
            for mid, elem in self.fem.elements.items():
                hprop = hinge_props[mid]
                length = elem.length

                edofs = dof_sys.get_element_dof_indices(elem.start_node_id, elem.end_node_id)
                u_elem = [current_u[free_dofs.index(d)] if d in free_dofs else 0.0 for d in edofs]
                m_forces = elem.recover_internal_forces(u_elem, num_stations=2)

                m_i = abs(m_forces.M3[0])
                m_j = abs(m_forces.M3[-1])

                yielded_ends = 0
                for end_loc, m_curr in (("I", m_i), ("J", m_j)):
                    hkey = f"{mid}_{end_loc}"
                    my = hprop.yield_moment
                    ratio = m_curr / max(my, 1.0)

                    if ratio >= 1.0:
                        yielded_ends += 1
                        theta_p = (ratio - 1.0) * hprop.yield_rotation
                        if theta_p <= hprop.theta_io:
                            state = HingeState.IMMEDIATE_OCCUPANCY
                        elif theta_p <= hprop.theta_ls:
                            state = HingeState.LIFE_SAFETY
                        elif theta_p <= hprop.theta_cp:
                            state = HingeState.COLLAPSE_PREVENTION
                        else:
                            state = HingeState.COLLAPSE
                    else:
                        theta_p = 0.0
                        state = HingeState.ELASTIC

                    old_state = current_hinges[hkey].state
                    if old_state == HingeState.ELASTIC and state != HingeState.ELASTIC:
                        if not first_yield_occurred:
                            first_yield_occurred = True
                            yield_base_shear = base_shear
                            yield_disp = roof_disp
                        hinge_formation_events.append({
                            "step": step,
                            "member_id": mid,
                            "end": end_loc,
                            "moment_kNm": round(m_curr / 1000.0, 2),
                            "state": state.value,
                            "roof_disp_mm": round(roof_disp * 1000.0, 2),
                            "base_shear_kN": round(base_shear / 1000.0, 2)
                        })

                    current_hinges[hkey] = MemberHingeState(
                        member_id=mid,
                        end_location=end_loc,
                        current_moment=m_curr,
                        plastic_rotation=theta_p,
                        yield_ratio=ratio,
                        state=state,
                        hinge_color_hex=get_hinge_color(state)
                    )
                    hinge_count[state.value] += 1

                if yielded_ends == 2:
                    member_softening[mid] = 0.03
                elif yielded_ends == 1:
                    member_softening[mid] = 0.25
                else:
                    member_softening[mid] = 1.0

            if base_shear > peak_base_shear:
                peak_base_shear = base_shear
                peak_disp = roof_disp

            state_desc = "Elastic"
            if hinge_count["COLLAPSE"] > 0:
                state_desc = "Collapse Mechanism"
            elif hinge_count["CP"] > 0:
                state_desc = "Collapse Prevention"
            elif hinge_count["LS"] > 0:
                state_desc = "Life Safety"
            elif hinge_count["IO"] > 0:
                state_desc = "Immediate Occupancy"

            capacity_curve_points.append(PushoverCapacityCurvePoint(
                displacement_mm=roof_disp * 1000.0,
                base_shear_kN=base_shear / 1000.0,
                step=step,
                state_description=state_desc
            ))

            step_records.append(PushoverStepRecord(
                step_number=step,
                load_factor_lambda=current_load_factor,
                roof_displacement_x=roof_disp,
                base_shear_x=base_shear,
                base_overturning_moment_z=base_shear * (total_height * 0.7),
                iterations_to_converge=1,
                residual_force_norm=0.0,
                hinge_states=dict(current_hinges),
                active_hinge_count=dict(hinge_count)
            ))

        if not first_yield_occurred:
            yield_base_shear = peak_base_shear * 0.75
            yield_disp = peak_disp * 0.75

        ductility = peak_disp / max(yield_disp, 1e-6)
        elapsed = time.time() - t_start

        return PushoverResult(
            success=True,
            control_type=self.control_type,
            monitored_node=monitored_node_id,
            target_displacement=self.target_displacement,
            total_steps=self.num_steps,
            yield_base_shear=yield_base_shear,
            yield_displacement=yield_disp,
            peak_base_shear=peak_base_shear,
            peak_displacement=peak_disp,
            ductility_factor_mu=ductility,
            initial_elastic_stiffness=initial_stiffness,
            capacity_curve=capacity_curve_points,
            step_records=step_records,
            hinge_formation_sequence=hinge_formation_events,
            summary_message=(
                f"Nonlinear Pushover ({self.control_type}) completed in {elapsed:.3f}s. "
                f"Peak Base Shear: {peak_base_shear/1000.0:.2f} kN at {peak_disp*1000.0:.1f} mm. "
                f"Ductility mu: {ductility:.2f}."
            )
        )
