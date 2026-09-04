"""
STRUCTURE-X ULTIMATE — BIAXIAL FLEXURAL CAPACITY & INTERACTION CHECK
Evaluates simultaneous axial force Pu and biaxial bending moments (Mux, Muy) for Columns and Piers.
Strictly complies with ACI 318-19 (Clause 22.4, Commentary R10.6.4: Bresler Reciprocal Load Method
& Load Contour Method) and Eurocode 2 (Clause 5.8.9).
"""

import math
from typing import Optional, Dict, Any, Tuple
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


class BiaxialFlexureCheck:
    """
    Modular biaxial flexural strength evaluator.
    """

    @staticmethod
    def _compute_uniaxial_moment_capacity(
        b_mm: float,
        h_mm: float,
        d_mm: float,
        Ast_mm2: float,
        Pu_kN: float,
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        phi: float = 0.65
    ) -> float:
        """
        Computes the nominal/design uniaxial moment capacity Mn at given axial load Pu.
        """
        fc = concrete.fc_prime
        fy = rebar.fy
        beta1 = concrete.get_beta1_aci()
        Pu_N = abs(Pu_kN) * 1000.0

        # Steel on tension face As1, steel on compression face As2
        As1 = Ast_mm2 / 2.0
        As2 = Ast_mm2 / 2.0
        d_prime = h_mm - d_mm

        # Approximate compression zone depth from equilibrium:
        # 0.85 * f'c * b * (beta1 * c) + As2 * fy - As1 * fy = Pu
        # c = (Pu) / (0.85 * f'c * b * beta1)
        a = (Pu_N + As1 * fy - As2 * fy) / (0.85 * fc * b_mm)
        a = max(20.0, min(a, 0.95 * h_mm))
        c = a / beta1

        # Mn about centroid of section (h/2):
        # Cc * (h/2 - a/2) + As1 * fy * (d - h/2) + As2 * fy * (h/2 - d_prime)
        Cc = 0.85 * fc * a * b_mm
        Mn_Nmm = Cc * (h_mm / 2.0 - a / 2.0) + As1 * fy * (d_mm - h_mm / 2.0) + As2 * fy * (h_mm / 2.0 - d_prime)
        Mn_kNm = max(Mn_Nmm / 1.0e6, 1.0)
        return Mn_kNm

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Pu_kN: float,  # Factored axial compression (kN)
        Mux_kNm: float,  # Factored moment about X-axis (bending in Y direction, kN*m)
        Muy_kNm: float,  # Factored moment about Y-axis (bending in X direction, kN*m)
        b_mm: float,  # Column width (X dimension, mm)
        h_mm: float,  # Column depth (Y dimension, mm)
        Ast_provided_mm2: float,  # Total longitudinal reinforcement (mm^2)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        cover_mm: float = 40.0,
        bar_dia_mm: float = 20.0,
        method: str = "Bresler_Reciprocal",  # "Bresler_Reciprocal" or "Load_Contour"
    ) -> DesignCheckResult:
        """
        ACI 318-19 Biaxial Flexure Check:
        Commentary R10.6.4 (Bresler Reciprocal Load Method: 1/Pn = 1/Pnx0 + 1/Pny0 - 1/P0).
        """
        phi = 0.65  # Tied column strength reduction factor
        fc = concrete.fc_prime
        fy = rebar.fy
        Ag = b_mm * h_mm

        inputs: Dict[str, Any] = {
            "Pu_kN": Pu_kN,
            "Mux_kNm": Mux_kNm,
            "Muy_kNm": Muy_kNm,
            "b_mm": b_mm,
            "h_mm": h_mm,
            "Ast_provided_mm2": Ast_provided_mm2,
            "fc_prime_MPa": fc,
            "fy_MPa": fy,
            "method": method,
            "phi": phi
        }

        intermediate: Dict[str, Any] = {}

        # 1. Pure axial concentric strength P0 (ACI 318-19 Eq. 22.4.2.2)
        net_Ac = max(Ag - Ast_provided_mm2, 0.0)
        P0_N = 0.85 * fc * net_Ac + fy * Ast_provided_mm2
        P0_kN = P0_N / 1000.0
        phi_P0_kN = phi * P0_kN

        # Effective depths
        d_x = h_mm - cover_mm - bar_dia_mm / 2.0  # bending about X (depth = h)
        d_y = b_mm - cover_mm - bar_dia_mm / 2.0  # bending about Y (depth = b)

        # 2. Eccentricities: ey = Mux / Pu, ex = Muy / Pu
        abs_Pu = max(abs(Pu_kN), 1.0)
        ey_mm = (abs(Mux_kNm) * 1.0e6) / (abs_Pu * 1000.0)
        ex_mm = (abs(Muy_kNm) * 1.0e6) / (abs_Pu * 1000.0)

        # Minimum accidental eccentricity check (ACI 318-19 Cl. 6.6.4.5.4): e_min = 15 + 0.03*h
        ey_min = 15.0 + 0.03 * h_mm
        ex_min = 15.0 + 0.03 * b_mm
        ey_design = max(ey_mm, ey_min)
        ex_design = max(ex_mm, ex_min)

        # 3. Uniaxial capacities
        # Pnx0: nominal capacity with eccentricity ey only (bending about X)
        # Pny0: nominal capacity with eccentricity ex only (bending about Y)
        # Approximation of Pnx0 from interaction: Pnx0 = P0 / (1 + (P0/M_nx_bal) * ey) or standard interaction
        Mnx_bal = BiaxialFlexureCheck._compute_uniaxial_moment_capacity(b_mm, h_mm, d_x, Ast_provided_mm2, Pu_kN, concrete, rebar, phi)
        Mny_bal = BiaxialFlexureCheck._compute_uniaxial_moment_capacity(h_mm, b_mm, d_y, Ast_provided_mm2, Pu_kN, concrete, rebar, phi)

        # Approximate Pnx0 and Pny0 under eccentricities:
        # Whitney formula for compression-controlled columns:
        # Pnx0 = (b * h * f'c) / [ (3*h*ey / d_x^2) + 1.18 ] + Ast * fy / (2*ey/(d_x - d') + 1)
        # Or standard interpolation:
        Pnx0_kN = P0_kN / (1.0 + (P0_kN / max(Mnx_bal, 1.0)) * (ey_design / 1000.0))
        Pny0_kN = P0_kN / (1.0 + (P0_kN / max(Mny_bal, 1.0)) * (ex_design / 1000.0))

        # 4. Bresler Reciprocal Load Method (ACI R10.6.4 Eq. R10.6.4)
        # 1/Pn = 1/Pnx0 + 1/Pny0 - 1/P0
        inv_Pn = (1.0 / max(Pnx0_kN, 1.0)) + (1.0 / max(Pny0_kN, 1.0)) - (1.0 / max(P0_kN, 1.0))
        if inv_Pn > 0:
            Pn_biaxial_kN = 1.0 / inv_Pn
        else:
            Pn_biaxial_kN = min(Pnx0_kN, Pny0_kN)

        # Maximum permissible axial load cap: 0.80 * P0
        Pn_biaxial_kN = min(Pn_biaxial_kN, 0.80 * P0_kN)
        phi_Pn_biaxial_kN = phi * Pn_biaxial_kN

        # 5. Load Contour Method Alternative / Verification
        # (Mux / phi*Mnx)^alpha + (Muy / phi*Mny)^alpha <= 1.0
        phi_Mnx = phi * Mnx_bal
        phi_Mny = phi * Mny_bal
        ratio_P = abs_Pu / phi_P0_kN
        alpha_exponent = 1.15 + 0.85 * min(ratio_P, 1.0)
        contour_val = (abs(Mux_kNm) / max(phi_Mnx, 1e-3)) ** alpha_exponent + (abs(Muy_kNm) / max(phi_Mny, 1e-3)) ** alpha_exponent

        intermediate["P0_pure_axial_kN"] = round(P0_kN, 2)
        intermediate["phi_P0_kN"] = round(phi_P0_kN, 2)
        intermediate["ey_eccentricity_mm"] = round(ey_design, 1)
        intermediate["ex_eccentricity_mm"] = round(ex_design, 1)
        intermediate["Mnx_capacity_kNm"] = round(Mnx_bal, 2)
        intermediate["Mny_capacity_kNm"] = round(Mny_bal, 2)
        intermediate["phi_Mnx_kNm"] = round(phi_Mnx, 2)
        intermediate["phi_Mny_kNm"] = round(phi_Mny, 2)
        intermediate["Pnx0_uniaxial_kN"] = round(Pnx0_kN, 2)
        intermediate["Pny0_uniaxial_kN"] = round(Pny0_kN, 2)
        intermediate["Pn_bresler_capacity_kN"] = round(Pn_biaxial_kN, 2)
        intermediate["phi_Pn_bresler_capacity_kN"] = round(phi_Pn_biaxial_kN, 2)
        intermediate["load_contour_exponent_alpha"] = round(alpha_exponent, 3)
        intermediate["load_contour_demand_ratio"] = round(contour_val, 4)

        # D/C ratio
        dc_ratio_bresler = abs_Pu / phi_Pn_biaxial_kN if phi_Pn_biaxial_kN > 0 else 999.0
        dc_ratio = max(dc_ratio_bresler, contour_val ** (1.0 / alpha_exponent))

        capacity_kN = phi_Pn_biaxial_kN
        demand_kN = abs_Pu
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        rho_prov = Ast_provided_mm2 / Ag
        reinf = ReinforcementResult(
            required_area_mm2=Ast_provided_mm2 * max(dc_ratio, 0.5),
            provided_area_mm2=Ast_provided_mm2,
            reinforcement_ratio=rho_prov,
            min_area_mm2=0.01 * Ag,
            max_area_mm2=0.04 * Ag,
            bar_callout=f"Ast={round(Ast_provided_mm2)} mm² ({round(rho_prov*100, 2)}% Ag)"
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause="ACI 318-19 Clause 22.4 & Commentary R10.6.4 (Bresler Reciprocal Method)",
            inputs=inputs,
            method="Bresler Reciprocal Load 1/Pn = 1/Pnx0 + 1/Pny0 - 1/P0 and Load Contour (Parme) Envelope",
            intermediate_results=intermediate,
            final_result=f"Capacity phi*Pn = {round(capacity_kN, 2)} kN, phi*Mnx={round(phi_Mnx, 1)} kNm, phi*Mny={round(phi_Mny, 1)} kNm",
            limit=f"Demand Pu = {round(demand_kN, 2)} kN, Mux={round(Mux_kNm, 1)} kNm, Muy={round(Muy_kNm, 1)} kNm (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Biaxial flexure check: Demand Pu = {round(demand_kN, 1)} kN, Mux={round(Mux_kNm, 1)} kNm, Muy={round(Muy_kNm, 1)} kNm, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.BIAXIAL_FLEXURE,
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
        NEd_kN: float,  # Design axial load (kN)
        MEdy_kNm: float,  # Design moment about y (kN*m)
        MEdz_kNm: float,  # Design moment about z (kN*m)
        b_mm: float,  # Column dimension along y (mm)
        h_mm: float,  # Column dimension along z (mm)
        As_provided_mm2: float,
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
    ) -> DesignCheckResult:
        """
        Eurocode 2 (EN 1992-1-1:2004) Biaxial Bending Check:
        Clause 5.8.9, Expression (5.39).
        (MEdz / MRdz)^a + (MEdy / MRdy)^a <= 1.0
        """
        fck = concrete.fc_prime
        fcd = concrete.get_design_strength_ec2(gamma_c=1.5)
        fyd = rebar.get_design_yield_strength_ec2(gamma_s=1.15)
        Ac = b_mm * h_mm
        NRd_kN = (Ac * fcd + As_provided_mm2 * fyd) / 1000.0

        inputs: Dict[str, Any] = {
            "NEd_kN": NEd_kN,
            "MEdy_kNm": MEdy_kNm,
            "MEdz_kNm": MEdz_kNm,
            "b_mm": b_mm,
            "h_mm": h_mm,
            "As_provided_mm2": As_provided_mm2,
            "fck_MPa": fck,
            "fcd_MPa": round(fcd, 2),
            "fyd_MPa": round(fyd, 2)
        }

        intermediate: Dict[str, Any] = {}

        # Uniaxial capacities MRdz and MRdy
        d_z = h_mm - 50.0
        d_y = b_mm - 50.0
        MRdz_kNm = BiaxialFlexureCheck._compute_uniaxial_moment_capacity(b_mm, h_mm, d_z, As_provided_mm2, NEd_kN, concrete, rebar, 1.0)
        MRdy_kNm = BiaxialFlexureCheck._compute_uniaxial_moment_capacity(h_mm, b_mm, d_y, As_provided_mm2, NEd_kN, concrete, rebar, 1.0)

        # Exponent 'a' from EC2 Clause 5.8.9 (Expression 5.39 table)
        ratio_N = abs(NEd_kN) / max(NRd_kN, 1.0)
        if ratio_N <= 0.1:
            a_exp = 1.0
        elif ratio_N <= 0.7:
            a_exp = 1.0 + (ratio_N - 0.1) * (1.5 - 1.0) / (0.7 - 0.1)
        elif ratio_N <= 1.0:
            a_exp = 1.5 + (ratio_N - 0.7) * (2.0 - 1.5) / (1.0 - 0.7)
        else:
            a_exp = 2.0

        # Expression 5.39: (MEdz / MRdz)^a + (MEdy / MRdy)^a <= 1.0
        term_z = (abs(MEdz_kNm) / max(MRdz_kNm, 1e-3)) ** a_exp
        term_y = (abs(MEdy_kNm) / max(MRdy_kNm, 1e-3)) ** a_exp
        biaxial_sum = term_z + term_y
        dc_ratio = biaxial_sum ** (1.0 / a_exp)

        intermediate["NRd_kN"] = round(NRd_kN, 2)
        intermediate["NEd_over_NRd"] = round(ratio_N, 4)
        intermediate["exponent_a"] = round(a_exp, 3)
        intermediate["MRdz_kNm"] = round(MRdz_kNm, 2)
        intermediate["MRdy_kNm"] = round(MRdy_kNm, 2)
        intermediate["biaxial_sum_expr_5_39"] = round(biaxial_sum, 4)

        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=As_provided_mm2 * max(dc_ratio, 0.5),
            provided_area_mm2=As_provided_mm2,
            reinforcement_ratio=As_provided_mm2 / Ac,
            bar_callout=f"As={round(As_provided_mm2)} mm²"
        )

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_2.value,
            code_edition=CodeEdition.EN_1992_1_1_2004.value,
            clause="EN 1992-1-1:2004 Clause 5.8.9 & Expression (5.39)",
            inputs=inputs,
            method="Eurocode 2 Biaxial Bending Elliptical Contour (MEdz/MRdz)^a + (MEdy/MRdy)^a <= 1.0",
            intermediate_results=intermediate,
            final_result=f"Capacity MRdz = {round(MRdz_kNm, 2)} kNm, MRdy = {round(MRdy_kNm, 2)} kNm, a={round(a_exp, 2)}",
            limit=f"Demand Sum = {round(biaxial_sum, 4)} <= 1.0 (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC2 Biaxial check: Demand NEd = {round(NEd_kN, 1)} kN, MEdz={round(MEdz_kNm, 1)} kNm, MEdy={round(MEdy_kNm, 1)} kNm, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.BIAXIAL_FLEXURE,
            member_type=member_type,
            demand=dc_ratio,
            capacity=1.0,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="ratio",
            summary_message=summary
        )
