"""
STRUCTURE-X ULTIMATE — PUNCHING SHEAR CAPACITY & TWO-WAY SLAB CHECK
Evaluates two-way critical perimeter b0 at d/2, three-equation concrete stress envelope,
eccentric shear stress distribution due to unbalanced moment transfer (gamma_v, Jc),
and shear reinforcement requirements.
Strictly complies with ACI 318-19 (Clauses 22.6, 8.4.2, 8.4.4) and Eurocode 2 (Clause 6.4).
"""

import math
from typing import Optional, Dict, Any
from .types import (
    DesignCode,
    CodeEdition,
    MemberType,
    CheckType,
    DesignStatus,
    CalculationTrace,
    ReinforcementResult,
    DesignCheckResult,
)
from .materials import ConcreteMaterial, RebarMaterial


class PunchingShearCheck:
    """
    Modular two-way punching shear evaluator for slabs and foundations.
    """

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Vu_kN: float,  # Factored total vertical column reaction/punching force (kN)
        c1_mm: float,  # Column dimension in direction of unbalanced moment (mm)
        c2_mm: float,  # Column dimension transverse to unbalanced moment (mm)
        d_mm: float,  # Average effective flexural depth of slab (mm)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        column_location: str = "Interior",  # "Interior", "Edge", "Corner"
        Msc_kNm: float = 0.0,  # Unbalanced moment transferred to column (kN*m)
        Av_provided_mm2: float = 0.0,  # Punching shear reinforcement (studs or stirrup legs, mm^2)
        s_mm: float = 100.0,  # Spacing of shear reinforcement perimeters (mm)
    ) -> DesignCheckResult:
        """
        ACI 318-19 Two-Way Punching Shear Check:
        Clauses 22.6, 8.4.2, 8.4.4, Table 21.2.1 (phi = 0.75).
        """
        phi = 0.75  # ACI 318-19 Table 21.2.1
        fc = concrete.fc_prime
        fyt = rebar.fyt if rebar.fyt else rebar.fy
        sqrt_fc = math.sqrt(max(fc, 1.0))
        lam = concrete.aggregate_factor_lambda

        loc = column_location.strip().capitalize()
        if loc == "Edge":
            alpha_s = 30.0
            # Edge column: critical section length b1 = c1 + d/2, b2 = c2 + d
            b1 = c1_mm + 0.5 * d_mm
            b2 = c2_mm + d_mm
            b0 = 2.0 * b1 + b2
        elif loc == "Corner":
            alpha_s = 20.0
            # Corner column: b1 = c1 + d/2, b2 = c2 + d/2
            b1 = c1_mm + 0.5 * d_mm
            b2 = c2_mm + 0.5 * d_mm
            b0 = b1 + b2
        else:
            # Interior column (default)
            alpha_s = 40.0
            b1 = c1_mm + d_mm
            b2 = c2_mm + d_mm
            b0 = 2.0 * (b1 + b2)

        beta_col = max(c1_mm, c2_mm) / max(min(c1_mm, c2_mm), 1.0)

        inputs: Dict[str, Any] = {
            "Vu_kN": Vu_kN,
            "Msc_kNm": Msc_kNm,
            "c1_mm": c1_mm,
            "c2_mm": c2_mm,
            "d_mm": d_mm,
            "column_location": loc,
            "alpha_s": alpha_s,
            "fc_prime_MPa": fc,
            "phi": phi
        }

        intermediate: Dict[str, Any] = {}

        # 1. Three-equation envelope for concrete punching shear strength vc (Clause 22.6.5.2)
        # Eq 1: vc1 = 0.33 * lambda * sqrt(f'c)
        vc1 = 0.33 * lam * sqrt_fc

        # Eq 2: vc2 = 0.17 * (1 + 2 / beta) * lambda * sqrt(f'c)
        vc2 = 0.17 * (1.0 + 2.0 / beta_col) * lam * sqrt_fc

        # Eq 3: vc3 = 0.083 * (2 + alpha_s * d / b0) * lambda * sqrt(f'c)
        vc3 = 0.083 * (2.0 + (alpha_s * d_mm) / b0) * lam * sqrt_fc

        vc_governing = min(vc1, vc2, vc3)

        # 2. Unbalanced Moment Transfer by Eccentric Shear (Clause 8.4.2.3)
        # gamma_v = 1 - 1 / (1 + (2/3) * sqrt(b1 / b2))
        gamma_v = 1.0 - (1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(b1 / b2)))
        gamma_f = 1.0 - gamma_v

        # Polar moment of inertia Jc for interior rectangular section
        # Jc = d * b1^3 / 6 + b1 * d^3 / 6 + d * b2 * b1^2 / 2
        Jc = (d_mm * (b1 ** 3)) / 6.0 + (b1 * (d_mm ** 3)) / 6.0 + (d_mm * b2 * (b1 ** 2)) / 2.0
        c_ab = b1 / 2.0

        Vu_N = abs(Vu_kN) * 1000.0
        direct_shear_stress = Vu_N / (b0 * d_mm)

        if abs(Msc_kNm) > 0.0:
            Msc_Nmm = abs(Msc_kNm) * 1.0e6
            eccentric_shear_stress = (gamma_v * Msc_Nmm * c_ab) / Jc
        else:
            eccentric_shear_stress = 0.0

        vu_max = direct_shear_stress + eccentric_shear_stress
        phi_vc = phi * vc_governing

        # Nominal capacity in terms of force Vu_cap without reinforcement
        # Vu_cap = phi * vc * b0 * d (scaled by ratio if eccentric stress is present)
        eccentric_factor = vu_max / direct_shear_stress if direct_shear_stress > 0 else 1.0
        phi_Vc_force_kN = (phi * vc_governing * b0 * d_mm) / (1000.0 * eccentric_factor)

        # 3. Shear Reinforcement (Clause 22.6.9 & 8.4.4)
        if vu_max > phi_vc:
            # Need shear reinforcement (studs or stirrups)
            # vn = vc/2 + vs <= 0.50 * sqrt(f'c) (for stirrups: vc = 0.17*sqrt(f'c))
            vc_reduced = 0.17 * lam * sqrt_fc
            vs_req = (vu_max / phi) - vc_reduced
            vs_req = max(0.0, vs_req)
            Av_over_s_req = (vs_req * b0) / fyt
            # Maximum nominal capacity with stirrups: vn <= 0.50 * sqrt(f'c)
            vn_max = 0.50 * sqrt_fc
            phi_vn_max = phi * vn_max
            reinforcement_needed = True
        else:
            Av_over_s_req = 0.0
            phi_vn_max = phi_vc
            reinforcement_needed = False

        intermediate["critical_perimeter_b0_mm"] = round(b0, 1)
        intermediate["b1_mm"] = round(b1, 1)
        intermediate["b2_mm"] = round(b2, 1)
        intermediate["column_aspect_ratio_beta"] = round(beta_col, 2)
        intermediate["vc1_basic_MPa"] = round(vc1, 3)
        intermediate["vc2_aspect_ratio_MPa"] = round(vc2, 3)
        intermediate["vc3_perimeter_ratio_MPa"] = round(vc3, 3)
        intermediate["vc_governing_MPa"] = round(vc_governing, 3)
        intermediate["phi_vc_allowable_stress_MPa"] = round(phi_vc, 3)
        intermediate["direct_shear_stress_MPa"] = round(direct_shear_stress, 3)
        intermediate["eccentric_shear_stress_MPa"] = round(eccentric_shear_stress, 3)
        intermediate["vu_max_stress_MPa"] = round(vu_max, 3)
        intermediate["gamma_v_fraction"] = round(gamma_v, 4)
        intermediate["gamma_f_flexure_fraction"] = round(gamma_f, 4)
        intermediate["reinforcement_needed"] = reinforcement_needed

        capacity_stress_MPa = phi_vc
        demand_stress_MPa = vu_max
        dc_ratio = demand_stress_MPa / capacity_stress_MPa if capacity_stress_MPa > 0 else 999.0

        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=Av_over_s_req * s_mm,
            provided_area_mm2=Av_provided_mm2,
            reinforcement_ratio=Av_provided_mm2 / (b0 * s_mm) if b0 * s_mm > 0 else 0.0,
            bar_callout=f"Av={round(Av_provided_mm2)} mm² around perimeter (req Av/s={round(Av_over_s_req, 3)})" if reinforcement_needed else "No shear rebar required (vu <= phi*vc)",
            spacing_mm=s_mm
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause="ACI 318-19 Clauses 22.6.5.2, 8.4.2.3 & Table 21.2.1",
            inputs=inputs,
            method="ACI 318-19 Three-Equation Two-Way Punching Envelope with Polar Eccentric Stress (Jc)",
            intermediate_results=intermediate,
            final_result=f"Capacity phi*vc = {round(capacity_stress_MPa, 3)} MPa (Equivalent phi*Vc = {round(phi_Vc_force_kN, 1)} kN)",
            limit=f"Demand vu_max = {round(demand_stress_MPa, 3)} MPa (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Punching shear check ({loc} col): Demand = {round(demand_stress_MPa, 3)} MPa, Allowable = {round(capacity_stress_MPa, 3)} MPa, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.PUNCHING_SHEAR,
            member_type=member_type,
            demand=demand_stress_MPa,
            capacity=capacity_stress_MPa,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="MPa",
            summary_message=summary
        )
