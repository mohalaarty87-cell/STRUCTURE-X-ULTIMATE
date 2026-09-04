"""
STRUCTURE-X ULTIMATE — ONE-WAY SHEAR CAPACITY & DESIGN CHECK
Evaluates concrete shear contribution Vc, transverse stirrup steel Vs, size effect factor lambda_s,
axial load enhancement, minimum shear reinforcement, and maximum spacing limits.
Strictly complies with ACI 318-19 (Clause 22.5, 9.6.3, 9.7.6) and Eurocode 2 (Clause 6.2).
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


class ShearCheck:
    """
    Modular one-way shear strength evaluator.
    """

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Vu_kN: float,  # Factored design shear demand (kN)
        bw_mm: float,  # Web width (mm)
        d_mm: float,  # Effective depth (mm)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        Av_provided_mm2: float = 0.0,  # Area of shear reinforcement within spacing s (mm^2)
        s_mm: float = 200.0,  # Stirrup spacing (mm)
        Nu_kN: float = 0.0,  # Factored axial force (kN, positive = compression, negative = tension)
        Ag_mm2: Optional[float] = None,  # Gross area for axial stress (mm^2)
    ) -> DesignCheckResult:
        """
        ACI 318-19 One-Way Shear Design Check:
        Clauses 22.5, 9.6.3, 9.7.6, Table 21.2.1 (phi = 0.75).
        """
        phi = 0.75  # ACI 318-19 Table 21.2.1
        fc = concrete.fc_prime
        fyt = rebar.fyt if rebar.fyt else rebar.fy
        sqrt_fc = math.sqrt(max(fc, 1.0))
        lam = concrete.aggregate_factor_lambda

        if Ag_mm2 is None or Ag_mm2 <= 0.0:
            Ag_mm2 = bw_mm * (d_mm / 0.9)  # Approximate gross area if not passed

        inputs: Dict[str, Any] = {
            "Vu_kN": Vu_kN,
            "bw_mm": bw_mm,
            "d_mm": d_mm,
            "Av_provided_mm2": Av_provided_mm2,
            "s_mm": s_mm,
            "Nu_kN": Nu_kN,
            "fc_prime_MPa": fc,
            "fyt_MPa": fyt,
            "phi": phi
        }

        intermediate: Dict[str, Any] = {}

        # 1. Minimum Shear Reinforcement (Clause 9.6.3.3)
        # Av/s,min = max(0.062*sqrt(f'c)*bw/fyt, 0.35*bw/fyt)
        Av_s_min1 = 0.062 * sqrt_fc * bw_mm / fyt
        Av_s_min2 = 0.35 * bw_mm / fyt
        Av_s_min = max(Av_s_min1, Av_s_min2)

        # 2. Size effect factor lambda_s (Clause 22.5.5.1.3)
        # If Av >= Av_min: lambda_s = 1.0
        Av_s_provided = Av_provided_mm2 / max(s_mm, 1.0)
        has_min_shear_rebar = Av_s_provided >= (Av_s_min * 0.99)
        if has_min_shear_rebar or member_type == MemberType.COLUMN:
            lambda_s = 1.0
        else:
            lambda_s = math.sqrt(2.0 / (1.0 + d_mm / 250.0))
            lambda_s = min(1.0, lambda_s)

        # 3. Concrete Shear Contribution Vc (Table 22.5.5.1)
        # With axial force Nu (compression positive)
        if Nu_kN > 0.0:
            # Compression: Vc = [0.17*lambda*sqrt(f'c) + Nu/(6*Ag)] * bw * d or Eq 22.5.5.1
            axial_factor = 1.0 + (Nu_kN * 1000.0) / (14.0 * Ag_mm2)
            Vc_N = 0.17 * axial_factor * lam * sqrt_fc * bw_mm * d_mm
            axial_effect = f"Compression enhanced (+{round((axial_factor - 1.0)*100, 1)}%)"
        elif Nu_kN < 0.0:
            # Tension: Vc = 0.17 * [1 + 0.29*Nu/Ag] * lambda * sqrt(f'c) * bw * d >= 0
            axial_factor = max(0.0, 1.0 + (0.29 * Nu_kN * 1000.0) / Ag_mm2)
            Vc_N = 0.17 * axial_factor * lam * sqrt_fc * bw_mm * d_mm
            axial_effect = f"Tension reduced ({round(axial_factor, 3)})"
        else:
            Vc_N = 0.17 * lambda_s * lam * sqrt_fc * bw_mm * d_mm
            axial_effect = "None (Nu = 0)"

        Vc_kN = Vc_N / 1000.0

        # 4. Transverse Steel Shear Contribution Vs (Clause 22.5.10.5.3)
        # Vs = (Av * fyt * d) / s
        if Av_provided_mm2 > 0 and s_mm > 0:
            Vs_N = (Av_provided_mm2 * fyt * d_mm) / s_mm
        else:
            Vs_N = 0.0
        Vs_kN = Vs_N / 1000.0

        # Upper limit on Vs: Vs,max = 0.66 * sqrt(f'c) * bw * d (Clause 22.5.1.2)
        Vs_max_N = 0.66 * sqrt_fc * bw_mm * d_mm
        Vs_max_kN = Vs_max_N / 1000.0
        Vs_governed_N = min(Vs_N, Vs_max_N)
        Vs_governed_kN = Vs_governed_N / 1000.0

        # 5. Total Shear Capacity phi*Vn
        Vn_kN = Vc_kN + Vs_governed_kN
        phi_Vn_kN = phi * Vn_kN

        # 6. Required Shear Reinforcement for demand Vu
        Vu_N = abs(Vu_kN) * 1000.0
        phi_Vc_kN = phi * Vc_kN
        if abs(Vu_kN) > phi_Vc_kN:
            Vs_req_N = (Vu_N / phi) - Vc_N
            Av_s_req = Vs_req_N / (fyt * d_mm)
            Av_s_required = max(Av_s_req, Av_s_min)
        elif abs(Vu_kN) > 0.5 * phi_Vc_kN and member_type != MemberType.SLAB:
            Av_s_required = Av_s_min
        else:
            Av_s_required = 0.0

        # 7. Maximum Spacing Limits (Clause 9.7.6.2.2)
        if Vs_governed_N <= (0.33 * sqrt_fc * bw_mm * d_mm):
            s_max_code = min(0.5 * d_mm, 600.0)
        else:
            s_max_code = min(0.25 * d_mm, 300.0)

        intermediate["Vc_concrete_kN"] = round(Vc_kN, 2)
        intermediate["Vs_steel_provided_kN"] = round(Vs_kN, 2)
        intermediate["Vs_max_permitted_kN"] = round(Vs_max_kN, 2)
        intermediate["phi_Vc_kN"] = round(phi_Vc_kN, 2)
        intermediate["phi_Vn_capacity_kN"] = round(phi_Vn_kN, 2)
        intermediate["lambda_s_size_effect"] = round(lambda_s, 3)
        intermediate["axial_load_effect"] = axial_effect
        intermediate["Av_over_s_req_mm2_per_mm"] = round(Av_s_required, 4)
        intermediate["Av_over_s_prov_mm2_per_mm"] = round(Av_s_provided, 4)
        intermediate["s_max_permitted_mm"] = round(s_max_code, 1)

        capacity_kN = phi_Vn_kN
        demand_kN = abs(Vu_kN)
        dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0

        spacing_valid = (s_mm <= s_max_code * 1.05) if Av_provided_mm2 > 0 else True
        web_crush_valid = Vs_N <= Vs_max_N * 1.01
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and spacing_valid and web_crush_valid) else DesignStatus.FAIL

        # Reinforcement info
        Av_req_for_s = Av_s_required * s_mm
        reinf = ReinforcementResult(
            required_area_mm2=Av_req_for_s,
            provided_area_mm2=Av_provided_mm2,
            reinforcement_ratio=Av_s_provided / bw_mm if bw_mm > 0 else 0.0,
            min_area_mm2=Av_s_min * s_mm,
            max_area_mm2=9999.0,
            bar_callout=f"Av={round(Av_provided_mm2)} mm² @ {round(s_mm)} mm (Av/s = {round(Av_s_provided, 3)} mm²/mm)",
            spacing_mm=s_mm,
            legs=2
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause="ACI 318-19 Clauses 22.5, 9.6.3, 9.7.6 & Table 21.2.1",
            inputs=inputs,
            method="ACI 318-19 Modified Truss Model with Concrete Shear Mechanism & Size Effect",
            intermediate_results=intermediate,
            final_result=f"Capacity phi*Vn = {round(capacity_kN, 2)} kN",
            limit=f"Demand Vu = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Shear check: Demand = {round(demand_kN, 1)} kN, Capacity = {round(capacity_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.SHEAR,
            member_type=member_type,
            demand=demand_kN,
            capacity=capacity_kN,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_2(
        member_type: MemberType,
        VEd_kN: float,  # Design shear demand (kN)
        bw_mm: float,  # Web width (mm)
        d_mm: float,  # Effective depth (mm)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        Asw_provided_mm2: float = 0.0,  # Shear reinforcement (mm^2)
        s_mm: float = 200.0,  # Stirrup spacing (mm)
        Asl_mm2: float = 500.0,  # Longitudinal tension steel (mm^2)
        NEd_kN: float = 0.0,  # Design axial load (kN, compression positive)
        Ac_mm2: Optional[float] = None,
        cot_theta: float = 2.5,  # Variable strut angle (1.0 <= cot(theta) <= 2.5)
    ) -> DesignCheckResult:
        """
        Eurocode 2 (EN 1992-1-1:2004) One-Way Shear Design Check:
        Clause 6.2 (Variable Strut Inclination Method).
        """
        fck = concrete.fc_prime
        fcd = concrete.get_design_strength_ec2(gamma_c=1.5)
        fywd = rebar.get_design_yield_strength_ec2(gamma_s=1.15)
        gamma_c = 1.5

        if Ac_mm2 is None or Ac_mm2 <= 0:
            Ac_mm2 = bw_mm * (d_mm / 0.9)

        inputs: Dict[str, Any] = {
            "VEd_kN": VEd_kN,
            "bw_mm": bw_mm,
            "d_mm": d_mm,
            "Asw_provided_mm2": Asw_provided_mm2,
            "s_mm": s_mm,
            "Asl_mm2": Asl_mm2,
            "NEd_kN": NEd_kN,
            "fck_MPa": fck,
            "fcd_MPa": round(fcd, 2),
            "fywd_MPa": round(fywd, 2),
            "cot_theta": cot_theta
        }

        intermediate: Dict[str, Any] = {}

        # 1. Concrete resistance without shear reinforcement VRd,c (EC2 Eq 6.2.a)
        CRd_c = 0.18 / gamma_c
        k = min(2.0, 1.0 + math.sqrt(200.0 / max(d_mm, 1.0)))
        rho_l = min(0.02, Asl_mm2 / (bw_mm * d_mm))
        sigma_cp = max(0.0, min(0.2 * fcd, (NEd_kN * 1000.0) / Ac_mm2)) if NEd_kN > 0 else 0.0
        k1 = 0.15

        vmin = 0.035 * (k ** 1.5) * math.sqrt(fck)
        v_calc = CRd_c * k * math.pow(100.0 * rho_l * fck, 1.0 / 3.0) + k1 * sigma_cp
        v_rdc = max(vmin + k1 * sigma_cp, v_calc)
        VRd_c_N = v_rdc * bw_mm * d_mm
        VRd_c_kN = VRd_c_N / 1000.0

        # 2. Shear resistance with shear reinforcement VRd,s (EC2 Eq 6.8)
        # Lever arm z approx 0.9 * d
        z = 0.9 * d_mm
        cot_theta = max(1.0, min(2.5, cot_theta))
        tan_theta = 1.0 / cot_theta

        if Asw_provided_mm2 > 0 and s_mm > 0:
            VRd_s_N = (Asw_provided_mm2 / s_mm) * z * fywd * cot_theta
        else:
            VRd_s_N = 0.0
        VRd_s_kN = VRd_s_N / 1000.0

        # 3. Maximum shear resistance limited by crushing of concrete struts VRd,max (EC2 Eq 6.9)
        nu1 = 0.6 * (1.0 - fck / 250.0)
        alpha_cw = 1.0  # non-prestressed
        VRd_max_N = alpha_cw * bw_mm * z * nu1 * fcd / (cot_theta + tan_theta)
        VRd_max_kN = VRd_max_N / 1000.0

        # Total capacity
        if Asw_provided_mm2 > 0:
            capacity_kN = min(VRd_s_kN, VRd_max_kN)
        else:
            capacity_kN = VRd_c_kN

        intermediate["VRd_c_concrete_kN"] = round(VRd_c_kN, 2)
        intermediate["VRd_s_steel_kN"] = round(VRd_s_kN, 2)
        intermediate["VRd_max_strut_crush_kN"] = round(VRd_max_kN, 2)
        intermediate["k_size_factor"] = round(k, 3)
        intermediate["rho_l_longitudinal"] = round(rho_l, 4)
        intermediate["strut_angle_cot"] = cot_theta

        demand_kN = abs(VEd_kN)
        dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and demand_kN <= VRd_max_kN * 1.01) else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=(demand_kN * 1000.0) / (z * fywd * cot_theta) * s_mm if demand_kN > VRd_c_kN else 0.0,
            provided_area_mm2=Asw_provided_mm2,
            reinforcement_ratio=Asw_provided_mm2 / (bw_mm * s_mm) if bw_mm * s_mm > 0 else 0.0,
            bar_callout=f"Asw={round(Asw_provided_mm2)} mm² @ {round(s_mm)} mm",
            spacing_mm=s_mm,
            legs=2
        )

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_2.value,
            code_edition=CodeEdition.EN_1992_1_1_2004.value,
            clause="EN 1992-1-1:2004 Clause 6.2 (Variable Strut Method)",
            inputs=inputs,
            method="Eurocode 2 Truss Model with Variable Inclination Concrete Struts",
            intermediate_results=intermediate,
            final_result=f"Capacity VRd = {round(capacity_kN, 2)} kN",
            limit=f"Demand VEd = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC2 Shear check: Demand = {round(demand_kN, 1)} kN, Capacity = {round(capacity_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.SHEAR,
            member_type=member_type,
            demand=demand_kN,
            capacity=capacity_kN,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN",
            summary_message=summary
        )
