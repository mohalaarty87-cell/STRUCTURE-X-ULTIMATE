"""
Response Spectrum Analysis (RSA) Engine
STRUCTURE-X ULTIMATE — PHASE 08

Implements:
  - Design Response Spectrum Definition (ASCE 7-16/22, Eurocode 8, Custom)
  - Modal Response: Spectral Acceleration Sa(Tn), Modal Displacements, Modal Forces
  - Modal Combination Rules:
      * SRSS (Square Root of the Sum of Squares)
      * CQC (Complete Quadratic Combination with Der Kiureghian Correlation Coefficient)
  - Spatial Directional Combinations (100%-30% Rule, SRSS Directional)
  - Structural Response Quantities:
      * Base Shear (total dynamic base shears, modal contributions, code minimums)
      * Story Shear (floor-by-floor cumulative lateral forces)
      * Story Drift (story drift delta and drift ratios vs code limits)
      * Story Displacements (lateral floor displacements)
      * Modal Mass Participation (effective masses, ratios, cumulative sums)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import math
import time

from .modal_analysis import ModalSolver, ModalAnalysisResult, ModalParticipationResult
from .solver_core import FEMSolver3D, NodalDisplacement


@dataclass
class SpectrumPoint:
    period: float      # seconds
    sa: float          # Spectral acceleration (g)


@dataclass
class ResponseSpectrumDefinition:
    """
    Standard Design Response Spectrum.
    Supports ASCE 7-16/22, Eurocode 8, or user-defined custom spectrum.
    """
    spectrum_type: str = "ASCE7"   # 'ASCE7', 'EUROCODE8', 'CUSTOM'
    damping_ratio: float = 0.05    # 5% critical damping (xi)
    importance_factor_Ie: float = 1.0
    response_modification_R: float = 8.0 # R factor for ductile detailing
    
    # ASCE 7 Parameters
    Ss: float = 1.50   # Mapped short-period acceleration (g)
    S1: float = 0.60   # Mapped 1-second period acceleration (g)
    Fa: float = 1.20   # Site coefficient
    Fv: float = 1.50   # Site coefficient
    TL: float = 8.0    # Long-period transition period (s)
    
    # Eurocode 8 Parameters
    ag: float = 0.30   # Design ground acceleration (g)
    ground_type: str = "C" # A, B, C, D, E
    behavior_factor_q: float = 3.9
    
    # Custom curve points: list of (T, Sa)
    custom_points: List[SpectrumPoint] = field(default_factory=list)

    @classmethod
    def asce_7_design_spectrum(
        cls,
        ss: float = 1.5,
        s1: float = 0.6,
        fa: float = 1.2,
        fv: float = 1.5,
        tl: float = 8.0,
        r_factor: float = 8.0,
        importance_factor: float = 1.0,
        damping_ratio: float = 0.05
    ) -> "ResponseSpectrumDefinition":
        return cls(
            spectrum_type="ASCE7",
            Ss=ss,
            S1=s1,
            Fa=fa,
            Fv=fv,
            TL=tl,
            response_modification_R=r_factor,
            importance_factor_Ie=importance_factor,
            damping_ratio=damping_ratio
        )

    @classmethod
    def eurocode8_design_spectrum(
        cls,
        ag: float = 0.30,
        ground_type: str = "C",
        behavior_factor_q: float = 3.9,
        damping_ratio: float = 0.05
    ) -> "ResponseSpectrumDefinition":
        return cls(
            spectrum_type="EUROCODE8",
            ag=ag,
            ground_type=ground_type,
            behavior_factor_q=behavior_factor_q,
            damping_ratio=damping_ratio
        )

    def get_asce7_derived_parameters(self) -> Dict[str, float]:
        """Calculates SMS, SM1, SDS, SD1, T0, Ts according to ASCE 7."""
        S_MS = self.Fa * self.Ss
        S_M1 = self.Fv * self.S1
        S_DS = (2.0 / 3.0) * S_MS
        S_D1 = (2.0 / 3.0) * S_M1
        T_s = S_D1 / max(S_DS, 1e-6)
        T_0 = 0.2 * T_s
        return {
            "S_MS": S_MS, "S_M1": S_M1,
            "S_DS": S_DS, "S_D1": S_D1,
            "T_0": T_0, "T_s": T_s,
            "T_L": self.TL
        }

    def get_spectral_acceleration(self, T: float, use_design_R: bool = True) -> float:
        """
        Returns spectral acceleration Sa (in units of g) for period T (seconds).
        """
        T = max(0.001, float(T))
        scale = (self.importance_factor_Ie / self.response_modification_R) if use_design_R else 1.0

        if self.spectrum_type == "CUSTOM" and self.custom_points:
            # Linear interpolation in log or linear space
            pts = sorted(self.custom_points, key=lambda p: p.period)
            if T <= pts[0].period:
                return pts[0].sa * scale
            if T >= pts[-1].period:
                return pts[-1].sa * scale
            for i in range(len(pts) - 1):
                if pts[i].period <= T <= pts[i+1].period:
                    t0, t1 = pts[i].period, pts[i+1].period
                    s0, s1 = pts[i].sa, pts[i+1].sa
                    interp_sa = s0 + (s1 - s0) * (T - t0) / (t1 - t0)
                    return interp_sa * scale

        elif self.spectrum_type == "EUROCODE8":
            # EC8 Type 1 elastic spectrum parameters for Ground Type C (default)
            S_param = 1.15
            TB = 0.20
            TC = 0.60
            TD = 2.00
            q = self.behavior_factor_q if use_design_R else 1.0

            ag_s = self.ag * S_param
            if T < TB:
                sa = self.ag * (2.0/3.0 + (T/TB) * (2.5/q - 2.0/3.0))
            elif T <= TC:
                sa = (ag_s * 2.5) / q
            elif T <= TD:
                sa = (ag_s * 2.5 * (TC / T)) / q
            else:
                sa = (ag_s * 2.5 * (TC * TD / (T**2))) / q
            return max(sa, 0.2 * self.ag)

        # Default: ASCE 7-16 / IBC Design Response Spectrum
        params = self.get_asce7_derived_parameters()
        S_DS = params["S_DS"]
        S_D1 = params["S_D1"]
        T_0 = params["T_0"]
        T_s = params["T_s"]
        T_L = params["T_L"]

        if T < T_0:
            sa_elastic = S_DS * (0.4 + 0.6 * (T / T_0))
        elif T <= T_s:
            sa_elastic = S_DS
        elif T <= T_L:
            sa_elastic = S_D1 / T
        else:
            sa_elastic = (S_D1 * T_L) / (T ** 2)

        # Minimum base design acceleration check per ASCE 7 (0.044 * S_DS * Ie >= 0.01)
        sa_min = max(0.044 * S_DS * self.importance_factor_Ie, 0.01)
        sa_design = max(sa_elastic * scale, sa_min)
        return sa_design

    def generate_spectrum_curve(self, max_period: float = 4.0, num_points: int = 100) -> List[Dict[str, float]]:
        """Generates (T, Sa) points for plotting the spectrum curve."""
        curve = []
        for i in range(num_points):
            T = 0.02 + i * (max_period - 0.02) / (num_points - 1)
            sa = self.get_spectral_acceleration(T)
            curve.append({"period": round(T, 4), "sa": round(sa, 4)})
        return curve


@dataclass
class StoryResponseResult:
    """Calculated dynamic story response quantities along building height."""
    story_index: int
    elevation: float            # m
    story_height: float         # m
    story_shear_X: float        # N (CQC/SRSS combined story shear along X)
    story_shear_Z: float        # N (CQC/SRSS combined story shear along Z)
    story_drift_X: float        # m
    story_drift_Z: float        # m
    drift_ratio_X: float        # delta_X / h (percentage e.g. 0.35%)
    drift_ratio_Z: float        # delta_Z / h
    displacement_X: float       # m
    displacement_Z: float       # m
    allowable_drift_ratio: float = 0.02 # 2.0% per ASCE 7
    drift_acceptable_X: bool = True
    drift_acceptable_Z: bool = True


@dataclass
class ModalResponseData:
    """Response of a single vibration mode under the spectrum."""
    mode_number: int
    period: float               # s
    frequency: float            # Hz
    sa_g: float                 # Spectral acceleration in g
    sa_mps2: float              # Spectral acceleration in m/s^2 (sa_g * 9.80665)
    modal_base_shear_X: float   # N
    modal_base_shear_Z: float   # N
    mass_participation_X: float # %
    mass_participation_Z: float # %
    modal_roof_disp_X: float    # m
    modal_roof_disp_Z: float    # m


@dataclass
class ResponseSpectrumAnalysisResult:
    """Complete package of Response Spectrum Analysis outputs."""
    spectrum_definition: Dict[str, Any]
    spectrum_curve: List[Dict[str, float]]
    damping_ratio: float
    combination_method: str     # 'CQC' or 'SRSS'
    
    # Base Shears
    base_shear_X: float         # N (Combined base shear along X)
    base_shear_Z: float         # N (Combined base shear along Z)
    total_structural_weight: float # N (W = M_tot * g)
    base_shear_ratio_X: float   # V_b_X / W
    base_shear_ratio_Z: float   # V_b_Z / W
    
    # Directional Combinations (100%-30% Rule)
    directional_base_shear_X30Z: float # 1.0*Vx + 0.3*Vz
    directional_base_shear_Z30X: float # 1.0*Vz + 0.3*Vx
    directional_base_shear_SRSS: float # sqrt(Vx^2 + Vz^2)
    
    # Modal Responses
    modal_responses: List[ModalResponseData]
    cqc_correlation_matrix: List[List[float]]
    
    # Story-Level Responses
    story_responses: List[StoryResponseResult]
    max_drift_ratio_X: float
    max_drift_ratio_Z: float
    governing_story_X: int
    governing_story_Z: int
    all_drifts_pass: bool
    
    # Displacements
    nodal_displacements: Dict[str, NodalDisplacement]
    execution_time_ms: float = 0.0


class ResponseSpectrumSolver:
    """
    Performs Response Spectrum Analysis on a 3D structural model.
    Integrates Eigenvalue modal results with dynamic spectrum inputs.
    """

    def __init__(
        self,
        solver: FEMSolver3D,
        spectrum: Optional[ResponseSpectrumDefinition] = None,
        spectrum_def: Optional[ResponseSpectrumDefinition] = None,
        combination_method: str = "CQC",
        modal_combination: Optional[str] = None,
        directional_combination: str = "SRSS",
        modal_result: Optional[ModalAnalysisResult] = None
    ):
        self.solver = solver
        self.spectrum = spectrum or spectrum_def or ResponseSpectrumDefinition()
        comb = modal_combination or combination_method
        self.combination_method = comb.upper()
        self.directional_combination = directional_combination.upper()
        self.initial_modal_result = modal_result

    def solve(
        self,
        num_modes: int = 12,
        modal_result: Optional[ModalAnalysisResult] = None
    ) -> ResponseSpectrumAnalysisResult:
        """
        Executes complete modal response spectrum procedure:
          1. Runs modal analysis to extract eigenmodes, frequencies, and mass participation.
          2. Evaluates spectral acceleration Sa(T_n) for each mode.
          3. Computes modal response vectors (displacements, base shears, story forces).
          4. Combines modal responses via CQC (Complete Quadratic Combination) or SRSS.
          5. Computes multi-directional spatial combinations (100%-30% and SRSS).
          6. Evaluates floor shears, story drifts, and displacement profiles.
        """
        t_start = time.time()
        g = 9.80665

        # 1. Obtain modal analysis result
        if modal_result is None:
            modal_result = self.initial_modal_result
        if modal_result is None:
            modal_result = self.solver.solve_modal(num_modes=num_modes)

        modes = modal_result.modes
        num_computed_modes = len(modes)
        if num_computed_modes == 0:
            raise RuntimeError("Response Spectrum Analysis: No vibration modes were computed.")

        # 2. Compute CQC Correlation Matrix (Der Kiureghian formula)
        xi = self.spectrum.damping_ratio
        rho = [[0.0 for _ in range(num_computed_modes)] for _ in range(num_computed_modes)]
        for i in range(num_computed_modes):
            wi = modes[i].angular_frequency
            for j in range(num_computed_modes):
                if i == j:
                    rho[i][j] = 1.0
                else:
                    wj = modes[j].angular_frequency
                    if wi > 1e-6 and wj > 1e-6:
                        beta = wj / wi
                        num = 8.0 * (xi ** 2) * (1.0 + beta) * (beta ** 1.5)
                        den = ((1.0 - beta ** 2) ** 2) + 4.0 * (xi ** 2) * beta * ((1.0 + beta) ** 2)
                        rho[i][j] = num / max(den, 1e-12)
                    else:
                        rho[i][j] = 0.0

        # Total Structural Weight
        total_mass = modal_result.total_structural_mass.get('X', modal_result.total_structural_mass.get('Y', 1.0))
        total_weight = modal_result.total_weight_kn * 1000.0 if modal_result.total_weight_kn > 0 else (total_mass * g)

        # 3. Modal Responses
        modal_data_list: List[ModalResponseData] = []
        modal_vb_X: List[float] = []
        modal_vb_Z: List[float] = []
        modal_disp_node_X: List[Dict[str, float]] = [] # For each mode: {nid: ux}
        modal_disp_node_Z: List[Dict[str, float]] = [] # For each mode: {nid: uz}

        # Identify top node for roof displacement monitoring
        top_node = max(self.solver.dof_system.nodes.items(), key=lambda item: item[1][1])[0]

        for m in modes:
            Tn = m.period
            wn = m.angular_frequency
            sa_g = self.spectrum.get_spectral_acceleration(Tn)
            sa_mps2 = sa_g * g

            # Directional participation factors and effective modal mass
            eff_mass_X = m.effective_modal_mass.get('X', 0.0)
            eff_mass_Z = m.effective_modal_mass.get('Z', 0.0)
            gamma_X = m.participation_factors.get('X', 0.0)
            gamma_Z = m.participation_factors.get('Z', 0.0)

            # Modal Base Shear: V_bn = M_eff,n * Sa
            vb_x = eff_mass_X * sa_mps2
            vb_z = eff_mass_Z * sa_mps2

            modal_vb_X.append(vb_x)
            modal_vb_Z.append(vb_z)

            # Modal Nodal Displacements: {u_n} = Gamma_n * (Sa / omega_n^2) * {phi_n}
            # Since mode shapes are mass-normalized (phi^T * M * phi = 1),
            # displacement scale factor is Gamma * Sa / omega^2
            scale_disp_X = (gamma_X * sa_mps2) / max(wn ** 2, 1e-6)
            scale_disp_Z = (gamma_Z * sa_mps2) / max(wn ** 2, 1e-6)

            m_disp_x: Dict[str, float] = {}
            m_disp_z: Dict[str, float] = {}
            for nid, shape in m.mode_shapes.items():
                m_disp_x[nid] = abs(scale_disp_X * shape.ux)
                m_disp_z[nid] = abs(scale_disp_Z * shape.uz)

            modal_disp_node_X.append(m_disp_x)
            modal_disp_node_Z.append(m_disp_z)

            modal_data_list.append(ModalResponseData(
                mode_number=m.mode_number,
                period=round(Tn, 4),
                frequency=round(m.frequency, 3),
                sa_g=round(sa_g, 4),
                sa_mps2=round(sa_mps2, 3),
                modal_base_shear_X=vb_x,
                modal_base_shear_Z=vb_z,
                mass_participation_X=round(m.participation_ratio.get('X', 0.0) * 100.0, 2),
                mass_participation_Z=round(m.participation_ratio.get('Z', 0.0) * 100.0, 2),
                modal_roof_disp_X=m_disp_x.get(top_node, 0.0),
                modal_roof_disp_Z=m_disp_z.get(top_node, 0.0)
            ))

        # 4. Combine Modal Base Shears
        def combine_responses(values: List[float]) -> float:
            if self.combination_method == "SRSS":
                return math.sqrt(sum(v ** 2 for v in values))
            # CQC combination
            sum_val = 0.0
            for i in range(len(values)):
                for j in range(len(values)):
                    sum_val += values[i] * rho[i][j] * values[j]
            return math.sqrt(max(sum_val, 0.0))

        base_shear_X = combine_responses(modal_vb_X)
        base_shear_Z = combine_responses(modal_vb_Z)

        # 5. Combined Nodal Displacements
        combined_displacements: Dict[str, NodalDisplacement] = {}
        for nid in self.solver.dof_system.node_order:
            ux_modes = [modal_disp_node_X[m_idx].get(nid, 0.0) for m_idx in range(num_computed_modes)]
            uz_modes = [modal_disp_node_Z[m_idx].get(nid, 0.0) for m_idx in range(num_computed_modes)]
            comb_ux = combine_responses(ux_modes)
            comb_uz = combine_responses(uz_modes)
            combined_displacements[nid] = NodalDisplacement(
                ux=comb_ux,
                uy=0.0,
                uz=comb_uz,
                rx=0.0,
                ry=0.0,
                rz=0.0
            )

        # 6. Group by Stories & Calculate Story Shears and Drifts
        # Story elevations sorted along Y
        y_coords = sorted(list(set(round(coord[1], 3) for coord in self.solver.dof_system.nodes.values())))
        story_responses: List[StoryResponseResult] = []
        max_drift_X, max_drift_Z = 0.0, 0.0
        gov_story_X, gov_story_Z = 1, 1

        if len(y_coords) > 1:
            for s_idx in range(len(y_coords) - 1):
                y_bot = y_coords[s_idx]
                y_top = y_coords[s_idx + 1]
                h_i = max(y_top - y_bot, 0.1)

                top_nodes = [nid for nid, c in self.solver.dof_system.nodes.items() if abs(c[1] - y_top) < 0.01]
                bot_nodes = [nid for nid, c in self.solver.dof_system.nodes.items() if abs(c[1] - y_bot) < 0.01]

                # Average displacement at top and bottom
                top_ux = sum(combined_displacements[n].ux for n in top_nodes) / max(len(top_nodes), 1)
                bot_ux = sum(combined_displacements[n].ux for n in bot_nodes) / max(len(bot_nodes), 1)
                drift_X = abs(top_ux - bot_ux)
                drift_ratio_X = drift_X / h_i

                top_uz = sum(combined_displacements[n].uz for n in top_nodes) / max(len(top_nodes), 1)
                bot_uz = sum(combined_displacements[n].uz for n in bot_nodes) / max(len(bot_nodes), 1)
                drift_Z = abs(top_uz - bot_uz)
                drift_ratio_Z = drift_Z / h_i

                # Story shear calculation:
                # In each mode n: story shear V_{story,n} = sum of lateral inertial forces at levels >= y_top
                story_v_modes_X: List[float] = []
                story_v_modes_Z: List[float] = []
                for m_idx, m in enumerate(modes):
                    # Fractional base shear at this story based on height and mass distribution
                    # Or modal inertial force sum: sum_{nodes above} m_node * phi * Gamma * Sa
                    nodes_above = [nid for nid, c in self.solver.dof_system.nodes.items() if c[1] >= y_top - 0.01]
                    ratio_nodes = len(nodes_above) / max(len(self.solver.dof_system.nodes), 1)
                    story_v_modes_X.append(modal_vb_X[m_idx] * ratio_nodes)
                    story_v_modes_Z.append(modal_vb_Z[m_idx] * ratio_nodes)

                combined_story_vx = combine_responses(story_v_modes_X)
                combined_story_vz = combine_responses(story_v_modes_Z)

                if drift_ratio_X > max_drift_X:
                    max_drift_X = drift_ratio_X
                    gov_story_X = s_idx + 1

                if drift_ratio_Z > max_drift_Z:
                    max_drift_Z = drift_ratio_Z
                    gov_story_Z = s_idx + 1

                story_responses.append(StoryResponseResult(
                    story_index=s_idx + 1,
                    elevation=y_top,
                    story_height=h_i,
                    story_shear_X=combined_story_vx,
                    story_shear_Z=combined_story_vz,
                    story_drift_X=drift_X,
                    story_drift_Z=drift_Z,
                    drift_ratio_X=drift_ratio_X,
                    drift_ratio_Z=drift_ratio_Z,
                    displacement_X=top_ux,
                    displacement_Z=top_uz,
                    allowable_drift_ratio=0.02, # 2% per ASCE 7
                    drift_acceptable_X=drift_ratio_X <= 0.02,
                    drift_acceptable_Z=drift_ratio_Z <= 0.02
                ))

        # 7. Directional Spatial Combinations (100%-30% Rule & SRSS)
        dir_X30Z = base_shear_X + 0.3 * base_shear_Z
        dir_Z30X = base_shear_Z + 0.3 * base_shear_X
        dir_SRSS = math.sqrt(base_shear_X ** 2 + base_shear_Z ** 2)

        # Spectrum Curve for visualization
        spectrum_curve = self.spectrum.generate_spectrum_curve(max_period=4.0, num_points=80)

        all_drifts_pass = (max_drift_X <= 0.02) and (max_drift_Z <= 0.02)
        execution_time_ms = (time.time() - t_start) * 1000.0

        return ResponseSpectrumAnalysisResult(
            spectrum_definition={
                "type": self.spectrum.spectrum_type,
                "damping": self.spectrum.damping_ratio,
                "R": self.spectrum.response_modification_R,
                "Ie": self.spectrum.importance_factor_Ie,
                "Ss": self.spectrum.Ss,
                "S1": self.spectrum.S1,
                "Fa": self.spectrum.Fa,
                "Fv": self.spectrum.Fv,
                "derived": self.spectrum.get_asce7_derived_parameters()
            },
            spectrum_curve=spectrum_curve,
            damping_ratio=self.spectrum.damping_ratio,
            combination_method=self.combination_method,
            base_shear_X=base_shear_X,
            base_shear_Z=base_shear_Z,
            total_structural_weight=total_weight,
            base_shear_ratio_X=base_shear_X / max(total_weight, 1e-6),
            base_shear_ratio_Z=base_shear_Z / max(total_weight, 1e-6),
            directional_base_shear_X30Z=dir_X30Z,
            directional_base_shear_Z30X=dir_Z30X,
            directional_base_shear_SRSS=dir_SRSS,
            modal_responses=modal_data_list,
            cqc_correlation_matrix=rho,
            story_responses=story_responses,
            max_drift_ratio_X=max_drift_X,
            max_drift_ratio_Z=max_drift_Z,
            governing_story_X=gov_story_X,
            governing_story_Z=gov_story_Z,
            all_drifts_pass=all_drifts_pass,
            nodal_displacements=combined_displacements,
            execution_time_ms=execution_time_ms
        )
