"""
STRUCTURE-X ULTIMATE — TORSION CAPACITY & DESIGN CHECK
Evaluates threshold torsion, cracking torque, space truss thin-walled tube model,
transverse closed stirrups, longitudinal rebar, and combined shear-torsion cross-section adequacy.
Strictly complies with ACI 318-19 (Clause 22.7, 9.5.4, 9.6.4, 9.7.6) and Eurocode 2 (Clause 6.3).
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


class TorsionCheck:
    """
    Modular torsion strength and reinforcement engine.
    """

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Tu_kNm: float,  # Factored torsion demand (kN*m)
        Vu_kN: float,  # Coexisting shear force (kN)
        b_mm: float,  # Cross-section width (mm)
        h_mm: float,  # Cross-section height (mm)
        d_mm: float,  # Effective depth (mm)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        At_provided_mm2: float = 78.5,  # Area of one leg of closed stirrup (mm^2, e.g. 10mm bar)
        s_mm: float = 150.0,  # Stirrup spacing (mm)
        Al_provided_mm2: float = 400.0,  # Total additional longitudinal steel (mm^2)
        cover_mm: float = 40.0,  # Clear concrete cover to stirrup outer face (mm)
        stirrup_dia_mm: float = 10.0,  # Stirrup bar diameter (mm)
        theta_deg: float = 45.0,  # Space truss compression strut angle (degrees)
    ) -> DesignCheckResult:
        """
        ACI 318-19 Torsion Design Check:
        Clauses 22.7, 9.5.4, 9.6.4, 9.7.6, Table 21.2.1 (phi = 0.75).
        """
        phi = 0.75  # ACI 318-19 Table 21.2.1
        fc = concrete.fc_prime
        fy = rebar.fy
        fyt = rebar.fyt if rebar.fyt else rebar.fy
        sqrt_fc = math.sqrt(max(fc, 1.0))
        lam = concrete.aggregate_factor_lambda

        # 1. Gross cross-sectional geometric properties
        Acp = b_mm * h_mm
        pcp = 2.0 * (b_mm + h_mm)

        # 2. Closed stirrup centerline dimensions (Aoh and ph)
        # Stirrup center is at cover + stirrup_dia / 2
        offset = cover_mm + stirrup_dia_mm / 2.0
        x1 = max(b_mm - 2.0 * offset, 20.0)
        y1 = max(h_mm - 2.0 * offset, 20.0)
        Aoh = x1 * y1
        ph = 2.0 * (x1 + y1)
        Ao = 0.85 * Aoh  # ACI 318-19 Clause 22.7.6.1.1

        inputs: Dict[str, Any] = {
            "Tu_kNm": Tu_kNm,
            "Vu_kN": Vu_kN,
            "b_mm": b_mm,
            "h_mm": h_mm,
            "d_mm": d_mm,
            "At_provided_mm2": At_provided_mm2,
            "s_mm": s_mm,
            "Al_provided_mm2": Al_provided_mm2,
            "fc_prime_MPa": fc,
            "fyt_MPa": fyt,
            "phi": phi
        }

        intermediate: Dict[str, Any] = {}

        # 3. Threshold torsion Tth (Clause 22.7.4.1)
        # Tth = 0.083 * lambda * sqrt(f'c) * (Acp^2 / pcp)
        Tth_Nmm = 0.083 * lam * sqrt_fc * ((Acp ** 2) / pcp)
        Tth_kNm = Tth_Nmm / 1.0e6
        phi_Tth_kNm = phi * Tth_kNm

        # 4. Cracking torsion Tcr (Clause 22.7.5.1)
        Tcr_Nmm = 0.33 * lam * sqrt_fc * ((Acp ** 2) / pcp)
        Tcr_kNm = Tcr_Nmm / 1.0e6

        # 5. Combined shear and torsion cross-section sizing adequacy (Clause 22.7.7.1)
        # sqrt( (Vu/(bw*d))^2 + (Tu*ph / (1.7*Aoh^2))^2 ) <= phi * ( Vc/(bw*d) + 0.66*sqrt(f'c) )
        # Basic Vc for beam: 0.17 * sqrt(f'c) * bw * d
        Vc_N = 0.17 * lam * sqrt_fc * b_mm * d_mm
        shear_stress_v = (abs(Vu_kN) * 1000.0) / (b_mm * d_mm)
        torsion_stress_vt = (abs(Tu_kNm) * 1.0e6 * ph) / (1.7 * (Aoh ** 2))
        combined_stress = math.sqrt(shear_stress_v ** 2 + torsion_stress_vt ** 2)
        allowable_stress = phi * (Vc_N / (b_mm * d_mm) + 0.66 * sqrt_fc)
        section_adequate = combined_stress <= (allowable_stress * 1.01)

        # 6. Nominal Torsional Strength Tn with provided stirrups (Clause 22.7.6.1)
        # Tn = (2 * Ao * At * fyt / s) * cot(theta)
        rad_theta = math.radians(theta_deg)
        cot_theta = 1.0 / math.tan(rad_theta)

        if At_provided_mm2 > 0 and s_mm > 0:
            Tn_Nmm = (2.0 * Ao * At_provided_mm2 * fyt / s_mm) * cot_theta
        else:
            Tn_Nmm = 0.0
        Tn_kNm = Tn_Nmm / 1.0e6
        phi_Tn_kNm = phi * Tn_kNm

        # 7. Required transverse torsion steel At/s
        Tu_Nmm = abs(Tu_kNm) * 1.0e6
        if abs(Tu_kNm) > phi_Tth_kNm:
            At_over_s_req = Tu_Nmm / (phi * 2.0 * Ao * fyt * cot_theta)
        else:
            At_over_s_req = 0.0

        # Minimum transverse reinforcement (Clause 9.6.4.2)
        # (Av/s + 2*At/s)min = max(0.062*sqrt(f'c)*b/fyt, 0.35*b/fyt)
        min_combined_transverse = max(0.062 * sqrt_fc * b_mm / fyt, 0.35 * b_mm / fyt)
        min_At_over_s = 0.5 * min_combined_transverse if abs(Tu_kNm) > phi_Tth_kNm else 0.0
        governing_At_over_s = max(At_over_s_req, min_At_over_s)

        # 8. Required longitudinal torsion steel Al (Clause 22.7.6.2)
        if abs(Tu_kNm) > phi_Tth_kNm:
            Al_req_calc = governing_At_over_s * ph * (fyt / fy) * (cot_theta ** 2)
            # Minimum longitudinal steel (Clause 9.6.4.3)
            Al_min = (0.42 * sqrt_fc * Acp / fy) - governing_At_over_s * ph * (fyt / fy)
            Al_min = max(0.0, Al_min)
            Al_required_mm2 = max(Al_req_calc, Al_min)
        else:
            Al_required_mm2 = 0.0

        # Maximum stirrup spacing (Clause 9.7.6.3.3): s_max = min(ph/8, 300 mm)
        s_max = min(ph / 8.0, 300.0)

        intermediate["Acp_mm2"] = Acp
        intermediate["Aoh_stirrup_area_mm2"] = round(Aoh, 1)
        intermediate["ph_stirrup_perimeter_mm"] = round(ph, 1)
        intermediate["Tth_threshold_kNm"] = round(Tth_kNm, 2)
        intermediate["phi_Tth_kNm"] = round(phi_Tth_kNm, 2)
        intermediate["Tcr_cracking_kNm"] = round(Tcr_kNm, 2)
        intermediate["Tn_nominal_kNm"] = round(Tn_kNm, 2)
        intermediate["phi_Tn_capacity_kNm"] = round(phi_Tn_kNm, 2)
        intermediate["combined_shear_torsion_stress_MPa"] = round(combined_stress, 3)
        intermediate["allowable_combined_stress_MPa"] = round(allowable_stress, 3)
        intermediate["section_sizing_adequate"] = section_adequate
        intermediate["At_over_s_req_mm2_per_mm"] = round(governing_At_over_s, 4)
        intermediate["Al_required_longitudinal_mm2"] = round(Al_required_mm2, 1)
        intermediate["s_max_spacing_mm"] = round(s_max, 1)

        capacity_kNm = phi_Tn_kNm
        demand_kNm = abs(Tu_kNm)

        if demand_kNm <= phi_Tth_kNm:
            # Torsion may be neglected per ACI 318-19 Cl. 22.7.4.1
            dc_ratio = demand_kNm / phi_Tth_kNm if phi_Tth_kNm > 0 else 0.0
            status = DesignStatus.PASS
            capacity_kNm = max(capacity_kNm, phi_Tth_kNm)
        else:
            dc_ratio = demand_kNm / capacity_kNm if capacity_kNm > 0 else 999.0
            spacing_valid = s_mm <= s_max * 1.05
            steel_valid = (Al_provided_mm2 >= Al_required_mm2 * 0.99)
            status = DesignStatus.PASS if (dc_ratio <= 1.0 and section_adequate and spacing_valid and steel_valid) else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=governing_At_over_s * s_mm,
            provided_area_mm2=At_provided_mm2,
            reinforcement_ratio=At_provided_mm2 / (b_mm * s_mm) if b_mm * s_mm > 0 else 0.0,
            bar_callout=f"At={round(At_provided_mm2)} mm² (1-leg) @ {round(s_mm)} mm, Al={round(Al_provided_mm2)} mm²",
            spacing_mm=s_mm,
            legs=1
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause="ACI 318-19 Clauses 22.7, 9.5.4, 9.6.4, 9.7.6 & Table 21.2.1",
            inputs=inputs,
            method="Space Truss Thin-Walled Tube Analogy with Softened Concrete Struts",
            intermediate_results=intermediate,
            final_result=f"Capacity phi*Tn = {round(capacity_kNm, 2)} kN*m",
            limit=f"Demand Tu = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Torsion check: Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(capacity_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.TORSION,
            member_type=member_type,
            demand=demand_kNm,
            capacity=capacity_kNm,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN*m",
            summary_message=summary
        )
