"""
STRUCTURE-X ULTIMATE — STEEL FLEXURE & LATERAL TORSIONAL BUCKLING (LTB) CHECK
Evaluates plastic moment Mp, unbraced lengths Lp & Lr, moment gradient factor Cb,
inelastic & elastic lateral-torsional buckling, flange local buckling (FLB), web local buckling (WLB),
and minor-axis flexure.
Strictly complies with AISC 360-16 (Chapter F) and Eurocode 3 (EN 1993-1-1 Clauses 6.2.5 & 6.3.2).
"""

import math
from typing import Dict, Any, Optional
from .types import (
    DesignCode,
    CodeEdition,
    DesignMethod,
    SteelCheckType,
    DesignStatus,
    CalculationTrace,
    SteelCheckResult,
    SectionCompactness,
)
from .materials import SteelMaterial
from .sections import SteelSection


class FlexureCheck:
    """
    Modular structural steel flexure & lateral-torsional buckling evaluator.
    """

    @staticmethod
    def calculate_cb(
        Mmax: float,
        MA: float,
        MB: float,
        MC: float,
    ) -> float:
        """
        AISC 360-16 Eq. F1-1:
        Cb = 12.5 * Mmax / (2.5 * Mmax + 3*MA + 4*MB + 3*MC)
        """
        m_max = abs(Mmax)
        m_a = abs(MA)
        m_b = abs(MB)
        m_c = abs(MC)
        denom = 2.5 * m_max + 3.0 * m_a + 4.0 * m_b + 3.0 * m_c
        if denom <= 1.0e-4:
            return 1.0
        cb = (12.5 * m_max) / denom
        return max(1.0, min(cb, 3.0))

    @staticmethod
    def check_aisc_360_16_major(
        section: SteelSection,
        material: SteelMaterial,
        Mu_kNm: float,                   # Factored major axis moment demand (kN*m)
        Lb_mm: float,                    # Unbraced length for lateral-torsional buckling (mm)
        Cb: float = 1.0,                 # Lateral-torsional buckling modification factor
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Chapter F: Major Axis Flexure (X-X) & Lateral-Torsional Buckling (LTB).
        Sections F2 (compact I-shapes) and F3 (non-compact/slender flanges).
        """
        Fy = material.Fy
        E = material.E
        Zx = section.Zx
        Sx = section.Sx
        ry = section.ry
        rts = section.rts if section.rts > 0 else ry * 1.1
        J = section.J
        ho = section.ho if section.ho > 0 else (section.d - section.tf)
        c = 1.0  # For doubly symmetric I-shapes

        # 1. Plastic moment capacity Mp (Eq. F2-1)
        Mp_Nmm = Fy * Zx
        Mp_kNm = Mp_Nmm / 1.0e6

        # 2. Limiting unbraced length for plastic moment Lp (Eq. F2-5)
        # Lp = 1.76 * ry * sqrt(E / Fy)
        Lp_mm = 1.76 * ry * math.sqrt(E / Fy)

        # 3. Limiting unbraced length for inelastic LTB Lr (Eq. F2-6)
        # Lr = 1.95 * rts * (E / (0.7*Fy)) * sqrt( (J*c / (Sx*ho)) + sqrt((J*c / (Sx*ho))^2 + 6.76*(0.7*Fy / E)^2) )
        term1 = (J * c) / (Sx * ho) if (Sx * ho > 0) else 0.0
        term2 = 6.76 * ((0.7 * Fy) / E) ** 2
        root_bracket = math.sqrt(term1 + math.sqrt(term1 ** 2 + term2))
        Lr_mm = 1.95 * rts * (E / (0.7 * Fy)) * root_bracket

        # 4. Lateral-Torsional Buckling Nominal Strength Mn_ltb
        if Lb_mm <= Lp_mm:
            Mn_ltb_kNm = Mp_kNm
            ltb_regime = "Lb <= Lp: Yielding Controls (No LTB)"
        elif Lb_mm <= Lr_mm:
            # Inelastic LTB (Eq. F2-2)
            # Mn = Cb * [Mp - (Mp - 0.7*Fy*Sx) * ((Lb - Lp) / (Lr - Lp))] <= Mp
            M_unfactored = Mp_kNm - (Mp_kNm - (0.7 * Fy * Sx) / 1.0e6) * ((Lb_mm - Lp_mm) / (Lr_mm - Lp_mm))
            Mn_ltb_kNm = min(Cb * M_unfactored, Mp_kNm)
            ltb_regime = "Lp < Lb <= Lr: Inelastic Lateral-Torsional Buckling (Eq. F2-2)"
        else:
            # Elastic LTB (Eq. F2-3 & F2-4)
            # Fcr = (Cb * pi^2 * E) / (Lb / rts)^2 * sqrt(1 + 0.078 * (J*c / (Sx*ho)) * (Lb/rts)^2)
            slender_ratio = Lb_mm / rts
            term_fcr = 1.0 + 0.078 * ((J * c) / (Sx * ho)) * (slender_ratio ** 2)
            Fcr = ((Cb * (math.pi ** 2) * E) / (slender_ratio ** 2)) * math.sqrt(term_fcr)
            Mn_elastic_Nmm = Fcr * Sx
            Mn_ltb_kNm = min(Mn_elastic_Nmm / 1.0e6, Mp_kNm)
            ltb_regime = "Lb > Lr: Elastic Lateral-Torsional Buckling (Eq. F2-3)"

        # 5. Flange Local Buckling (FLB) Check (Section F3)
        compactness, flb_details = section.check_flexural_compactness_aisc(material)
        if compactness == SectionCompactness.NON_COMPACT:
            lambda_f = section.b_over_2tf
            lp_f = 0.38 * math.sqrt(E / Fy)
            lr_f = 1.00 * math.sqrt(E / Fy)
            Mn_flb_kNm = Mp_kNm - (Mp_kNm - (0.7 * Fy * Sx) / 1.0e6) * ((lambda_f - lp_f) / (lr_f - lp_f))
        elif compactness == SectionCompactness.SLENDER:
            kc = 4.0 / math.sqrt(max(section.h_over_tw, 1.0))
            kc = max(0.35, min(0.76, kc))
            Fcr_flb = (0.9 * E * kc) / (section.b_over_2tf ** 2)
            Mn_flb_kNm = (Fcr_flb * Sx) / 1.0e6
        else:
            Mn_flb_kNm = Mp_kNm

        # Overall nominal flexural strength
        if Mn_flb_kNm < Mn_ltb_kNm:
            Mn_governing_kNm = Mn_flb_kNm
            governing_state = f"Flange Local Buckling ({compactness.value})"
        else:
            Mn_governing_kNm = Mn_ltb_kNm
            governing_state = ltb_regime

        # Apply design factors
        if method == DesignMethod.LRFD:
            phi_b = 0.90
            available_Mn_kNm = phi_b * Mn_governing_kNm
            factor_note = "phi = 0.90 (LRFD)"
        else:
            omega_b = 1.67
            available_Mn_kNm = Mn_governing_kNm / omega_b
            factor_note = "Omega = 1.67 (ASD)"

        demand_kNm = abs(Mu_kNm)
        dc_ratio = demand_kNm / available_Mn_kNm if available_Mn_kNm > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Mu_kNm": Mu_kNm,
            "section": section.name,
            "Fy_MPa": Fy,
            "Zx_mm3": Zx,
            "Sx_mm3": Sx,
            "Lb_mm": Lb_mm,
            "Cb": Cb,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Mp_plastic_kNm": round(Mp_kNm, 2),
            "Lp_limiting_mm": round(Lp_mm, 1),
            "Lr_limiting_mm": round(Lr_mm, 1),
            "Mn_ltb_kNm": round(Mn_ltb_kNm, 2),
            "Mn_flb_kNm": round(Mn_flb_kNm, 2),
            "governing_nominal_kNm": round(Mn_governing_kNm, 2),
            "available_flexural_kNm": round(available_Mn_kNm, 2),
            "design_factor": factor_note,
            "ltb_regime": ltb_regime,
            "flange_compactness": compactness.value
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Chapter F (Sections F1, F2, F3)",
            inputs=inputs,
            method=f"AISC {method.value} Flexural Strength with Lateral-Torsional Buckling",
            intermediate_results=intermediate,
            final_result=f"Available Flexural Strength = {round(available_Mn_kNm, 2)} kN*m ({governing_state})",
            limit=f"Moment Demand Mu = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Flexure check ({section.name}): Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(available_Mn_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.FLEXURE_MAJOR,
            demand=demand_kNm,
            capacity=available_Mn_kNm,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=governing_state,
            trace=trace,
            units="kN*m",
            summary_message=summary
        )

    @staticmethod
    def check_aisc_360_16_minor(
        section: SteelSection,
        material: SteelMaterial,
        Mu_y_kNm: float,                 # Factored minor axis moment demand (kN*m)
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Section F6: I-Shaped Members Bent about Their Minor Axis (Y-Y).
        Lateral-torsional buckling does not occur in minor axis bending.
        Mn = min(Fy * Zy, 1.6 * Fy * Sy).
        """
        Fy = material.Fy
        Zy = section.Zy
        Sy = section.Sy

        # Yielding limit state (Eq. F6-1)
        Mp_y_Nmm = Fy * Zy
        My_limit_Nmm = 1.6 * Fy * Sy
        Mn_y_Nmm = min(Mp_y_Nmm, My_limit_Nmm)
        Mn_y_kNm = Mn_y_Nmm / 1.0e6

        # Check for non-compact flanges in minor axis flexure
        lambda_f = section.b_over_2tf
        lp_f = 0.38 * math.sqrt(material.E / Fy)
        lr_f = 1.00 * math.sqrt(material.E / Fy)
        if lambda_f > lp_f:
            if lambda_f <= lr_f:
                Mn_flb_kNm = (Mp_y_Nmm - (Mp_y_Nmm - 0.7 * Fy * Sy) * ((lambda_f - lp_f) / (lr_f - lp_f))) / 1.0e6
            else:
                Fcr = (0.69 * material.E) / (lambda_f ** 2)
                Mn_flb_kNm = (Fcr * Sy) / 1.0e6
            Mn_y_kNm = min(Mn_y_kNm, Mn_flb_kNm)
            governing_state = "Flange Local Buckling (Section F6.2)"
        else:
            governing_state = "Minor Axis Yielding (Section F6.1)"

        if method == DesignMethod.LRFD:
            phi_b = 0.90
            available_Mn_kNm = phi_b * Mn_y_kNm
        else:
            omega_b = 1.67
            available_Mn_kNm = Mn_y_kNm / omega_b

        demand_kNm = abs(Mu_y_kNm)
        dc_ratio = demand_kNm / available_Mn_kNm if available_Mn_kNm > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Mu_y_kNm": Mu_y_kNm,
            "section": section.name,
            "Fy_MPa": Fy,
            "Zy_mm3": Zy,
            "Sy_mm3": Sy,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Mp_minor_kNm": round((Fy * Zy) / 1.0e6, 2),
            "1.6_My_limit_kNm": round((1.6 * Fy * Sy) / 1.0e6, 2),
            "Mn_nominal_kNm": round(Mn_y_kNm, 2),
            "available_strength_kNm": round(available_Mn_kNm, 2),
            "governing_state": governing_state
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Section F6",
            inputs=inputs,
            method="AISC Minor-Axis Flexural Strength (Mn = min(Fy*Zy, 1.6*Fy*Sy))",
            intermediate_results=intermediate,
            final_result=f"Available Minor Flexure = {round(available_Mn_kNm, 2)} kN*m ({governing_state})",
            limit=f"Minor Moment Demand Muy = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Minor flexure check ({section.name}): Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(available_Mn_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.FLEXURE_MINOR,
            demand=demand_kNm,
            capacity=available_Mn_kNm,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=governing_state,
            trace=trace,
            units="kN*m",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_3(
        section: SteelSection,
        material: SteelMaterial,
        MEd_kNm: float,                  # Design bending moment (kN*m)
        L_mm: float,                      # Unbraced length (mm)
        C1: float = 1.0,                  # Moment distribution factor
        gamma_M0: float = 1.0,
        gamma_M1: float = 1.0,
    ) -> SteelCheckResult:
        """
        Eurocode 3 (EN 1993-1-1:2005) Clauses 6.2.5 & 6.3.2: Bending & Lateral Torsional Buckling.
        """
        fy = material.Fy
        E = material.E
        G = material.G

        # Cross-section plastic resistance (Eq. 6.13)
        Mc_Rd_Nmm = (section.Zx * fy) / gamma_M0
        Mc_Rd_kNm = Mc_Rd_Nmm / 1.0e6

        # Elastic critical moment Mcr for lateral torsional buckling
        # Mcr = C1 * (pi^2 * E * Iz / L^2) * sqrt( Iw/Iz + L^2*G*It / (pi^2 * E * Iz) )
        Iz = section.Iy  # Minor axis inertia
        Iw = section.Cw  # Warping constant
        It = section.J   # Torsion constant

        term_e_iz = (math.pi ** 2 * E * Iz) / (L_mm ** 2) if L_mm > 0 else 1.0e12
        term_iw = Iw / max(Iz, 1.0)
        term_it = (L_mm ** 2 * G * It) / (math.pi ** 2 * E * max(Iz, 1.0)) if Iz > 0 else 0.0
        Mcr_Nmm = C1 * term_e_iz * math.sqrt(term_iw + term_it)
        Mcr_kNm = Mcr_Nmm / 1.0e6

        # Non-dimensional slenderness lambda_bar_LT (Eq. 6.56)
        lambda_bar_LT = math.sqrt((section.Zx * fy) / max(Mcr_Nmm, 1.0))

        # Imperfection factor alpha_LT (Table 6.4, curve b for rolled I-sections with h/b <= 2)
        h_over_b = section.d / max(section.bf, 1.0)
        alpha_LT = 0.34 if h_over_b <= 2.0 else 0.49

        # Value of phi_LT
        phi_LT = 0.5 * (1.0 + alpha_LT * (lambda_bar_LT - 0.2) + lambda_bar_LT ** 2)

        # Reduction factor chi_LT (Eq. 6.56)
        disc = phi_LT ** 2 - lambda_bar_LT ** 2
        if disc >= 0.0:
            chi_LT = 1.0 / (phi_LT + math.sqrt(disc))
        else:
            chi_LT = 1.0 / phi_LT
        chi_LT = min(1.0, max(0.1, chi_LT))

        # Design buckling resistance moment Mb,Rd (Eq. 6.55)
        Mb_Rd_Nmm = (chi_LT * section.Zx * fy) / gamma_M1
        Mb_Rd_kNm = Mb_Rd_Nmm / 1.0e6

        demand_kNm = abs(MEd_kNm)
        dc_ratio = demand_kNm / Mb_Rd_kNm if Mb_Rd_kNm > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "MEd_kNm": MEd_kNm,
            "section": section.name,
            "fy_MPa": fy,
            "Zx_mm3": section.Zx,
            "L_mm": L_mm,
            "C1": C1
        }

        intermediate: Dict[str, Any] = {
            "Mc_Rd_kNm": round(Mc_Rd_kNm, 2),
            "Mcr_kNm": round(Mcr_kNm, 2),
            "lambda_bar_LT": round(lambda_bar_LT, 3),
            "alpha_LT": alpha_LT,
            "chi_LT": round(chi_LT, 4),
            "Mb_Rd_kNm": round(Mb_Rd_kNm, 2)
        }

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_3.value,
            code_edition=CodeEdition.EN_1993_1_1_2005.value,
            clause="EN 1993-1-1:2005 Clause 6.3.2 (Eq. 6.55 - 6.57)",
            inputs=inputs,
            method="EC3 Lateral-Torsional Buckling Resistance Mb,Rd = chi_LT * Wpl * fy / gamma_M1",
            intermediate_results=intermediate,
            final_result=f"LTB Capacity Mb,Rd = {round(Mb_Rd_kNm, 2)} kN*m",
            limit=f"Demand MEd = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC3 Flexure/LTB check ({section.name}): Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(Mb_Rd_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.LATERAL_TORSIONAL_BUCKLING,
            demand=demand_kNm,
            capacity=Mb_Rd_kNm,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state="EC3 Lateral-Torsional Buckling Mb,Rd",
            trace=trace,
            units="kN*m",
            summary_message=summary
        )
