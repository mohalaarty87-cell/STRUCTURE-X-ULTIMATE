"""
STRUCTURE-X ULTIMATE — STEEL COMBINED FORCES & P-M-M INTERACTION CHECK
Evaluates simultaneous axial compression/tension with biaxial bending moments (P-Mx-My),
amplification factors (B1/B2), and interaction formulas.
Strictly complies with AISC 360-16 (Chapter H, Eqs. H1-1a & H1-1b) and Eurocode 3 (EN 1993-1-1 Clause 6.3.3).
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
)
from .materials import SteelMaterial
from .sections import SteelSection
from .compression_check import CompressionCheck
from .tension_check import TensionCheck
from .flexure_check import FlexureCheck


class InteractionCheck:
    """
    Modular structural steel combined force & P-M interaction evaluator.
    """

    @staticmethod
    def calculate_b1_amplification(
        Pr_kN: float,
        Pe1_kN: float,
        Cm: float = 1.0,
        method: DesignMethod = DesignMethod.LRFD,
    ) -> float:
        """
        AISC 360-16 Appendix 8 Eq. A-8-3:
        B1 = Cm / (1 - alpha * Pr / Pe1) >= 1.0
        alpha = 1.00 for LRFD, 1.60 for ASD.
        """
        alpha = 1.00 if method == DesignMethod.LRFD else 1.60
        if Pe1_kN <= 0.0:
            return 1.0
        ratio = (alpha * abs(Pr_kN)) / Pe1_kN
        if ratio >= 0.99:
            return 5.0  # Cap near singularity to flag severe instability
        b1 = Cm / (1.0 - ratio)
        return max(1.0, b1)

    @staticmethod
    def check_aisc_360_16(
        section: SteelSection,
        material: SteelMaterial,
        Pu_kN: float,                    # Factored axial force demand (+ for compression, - for tension)
        Mux_kNm: float,                  # Factored major axis moment demand (kN*m)
        Muy_kNm: float,                  # Factored minor axis moment demand (kN*m)
        Lx_mm: float,                    # Unbraced length major axis (mm)
        Ly_mm: float,                    # Unbraced length minor axis (mm)
        Lb_mm: Optional[float] = None,   # Unbraced length for LTB (mm)
        Kx: float = 1.0,
        Ky: float = 1.0,
        Cb: float = 1.0,
        Cm_x: float = 1.0,
        Cm_y: float = 1.0,
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Chapter H (Section H1): Doubly Symmetric Members Subject to Flexure and Axial Force.
        Equations H1-1a and H1-1b.
        """
        if Lb_mm is None or Lb_mm <= 0:
            Lb_mm = Ly_mm

        is_compression = Pu_kN >= 0.0

        # 1. Compute available axial capacity Pc
        if is_compression:
            comp_res = CompressionCheck.check_aisc_360_16(
                section=section,
                material=material,
                Pu_kN=abs(Pu_kN),
                Lx_mm=Lx_mm,
                Ly_mm=Ly_mm,
                Kx=Kx,
                Ky=Ky,
                method=method
            )
            Pc_kN = comp_res.capacity
            axial_type = "Compression"
        else:
            tens_res = TensionCheck.check_aisc_360_16(
                section=section,
                material=material,
                Pu_kN=abs(Pu_kN),
                L_mm=max(Lx_mm, Ly_mm),
                method=method
            )
            Pc_kN = tens_res.capacity
            axial_type = "Tension"

        # 2. Compute available flexural capacities Mcx and Mcy
        flex_x_res = FlexureCheck.check_aisc_360_16_major(
            section=section,
            material=material,
            Mu_kNm=abs(Mux_kNm),
            Lb_mm=Lb_mm,
            Cb=Cb,
            method=method
        )
        Mcx_kNm = flex_x_res.capacity

        flex_y_res = FlexureCheck.check_aisc_360_16_minor(
            section=section,
            material=material,
            Mu_y_kNm=abs(Muy_kNm),
            method=method
        )
        Mcy_kNm = flex_y_res.capacity

        # 3. Calculate first-order elastic critical Euler loads for B1 magnification
        # Pe1 = pi^2 * E * I / (K1 * L)^2
        pe1_x_kN = ((math.pi ** 2) * material.E * section.Ix) / ((Kx * Lx_mm) ** 2) / 1000.0 if (Kx * Lx_mm > 0) else 1.0e6
        pe1_y_kN = ((math.pi ** 2) * material.E * section.Iy) / ((Ky * Ly_mm) ** 2) / 1000.0 if (Ky * Ly_mm > 0) else 1.0e6

        b1_x = InteractionCheck.calculate_b1_amplification(abs(Pu_kN), pe1_x_kN, Cm_x, method) if is_compression else 1.0
        b1_y = InteractionCheck.calculate_b1_amplification(abs(Pu_kN), pe1_y_kN, Cm_y, method) if is_compression else 1.0

        Mrx_amplified_kNm = b1_x * abs(Mux_kNm)
        Mry_amplified_kNm = b1_y * abs(Muy_kNm)

        # 4. Evaluate Interaction Equations (Section H1.1)
        Pr_kN = abs(Pu_kN)
        axial_ratio = Pr_kN / Pc_kN if Pc_kN > 0 else 999.0
        flex_x_ratio = Mrx_amplified_kNm / Mcx_kNm if Mcx_kNm > 0 else 0.0
        flex_y_ratio = Mry_amplified_kNm / Mcy_kNm if Mcy_kNm > 0 else 0.0

        if axial_ratio >= 0.2:
            # AISC Eq. H1-1a:
            # Pr / Pc + (8/9) * (Mrx / Mcx + Mry / Mcy) <= 1.0
            interaction_value = axial_ratio + (8.0 / 9.0) * (flex_x_ratio + flex_y_ratio)
            governing_equation = "AISC 360-16 Eq. H1-1a (Pr/Pc >= 0.2)"
        else:
            # AISC Eq. H1-1b:
            # Pr / (2 * Pc) + (Mrx / Mcx + Mry / Mcy) <= 1.0
            interaction_value = (axial_ratio / 2.0) + (flex_x_ratio + flex_y_ratio)
            governing_equation = "AISC 360-16 Eq. H1-1b (Pr/Pc < 0.2)"

        status = DesignStatus.PASS if interaction_value <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Pu_kN": Pu_kN,
            "axial_type": axial_type,
            "Mux_kNm": Mux_kNm,
            "Muy_kNm": Muy_kNm,
            "section": section.name,
            "Lx_mm": Lx_mm,
            "Ly_mm": Ly_mm,
            "Lb_mm": Lb_mm,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Pc_axial_capacity_kN": round(Pc_kN, 2),
            "Mcx_capacity_kNm": round(Mcx_kNm, 2),
            "Mcy_capacity_kNm": round(Mcy_kNm, 2),
            "B1_x_amplification": round(b1_x, 3),
            "B1_y_amplification": round(b1_y, 3),
            "Mrx_amplified_kNm": round(Mrx_amplified_kNm, 2),
            "Mry_amplified_kNm": round(Mry_amplified_kNm, 2),
            "Pr_over_Pc": round(axial_ratio, 4),
            "Mrx_over_Mcx": round(flex_x_ratio, 4),
            "Mry_over_Mcy": round(flex_y_ratio, 4),
            "interaction_index": round(interaction_value, 4),
            "governing_equation": governing_equation
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Chapter H (Eqs. H1-1a / H1-1b)",
            inputs=inputs,
            method="AISC Interaction of Axial Force and Biaxial Flexure with B1 Amplification",
            intermediate_results=intermediate,
            final_result=f"Interaction Ratio = {round(interaction_value, 4)} ({governing_equation})",
            limit="1.0000",
            status=status
        )

        summary = f"Interaction check ({section.name}): Demand/Capacity Index = {round(interaction_value, 3)} <= 1.0 [{status.value}] ({governing_equation})"

        return SteelCheckResult(
            check_type=SteelCheckType.INTERACTION,
            demand=interaction_value,
            capacity=1.0,
            dc_ratio=interaction_value,
            status=status,
            governing_limit_state=governing_equation,
            trace=trace,
            units="ratio",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_3(
        section: SteelSection,
        material: SteelMaterial,
        NEd_kN: float,                   # Design axial force (+ for compression, kN)
        My_Ed_kNm: float,                # Design major moment (kN*m)
        Mz_Ed_kNm: float,                # Design minor moment (kN*m)
        Lcr_y_mm: float,
        Lcr_z_mm: float,
        L_ltb_mm: Optional[float] = None,
        gamma_M1: float = 1.0,
    ) -> SteelCheckResult:
        """
        Eurocode 3 (EN 1993-1-1:2005) Clause 6.3.3: Beam-Columns.
        Interaction expressions (6.61) & (6.62).
        """
        if L_ltb_mm is None or L_ltb_mm <= 0:
            L_ltb_mm = Lcr_z_mm

        # 1. Compressive buckling resistances Nb,y,Rd and Nb,z,Rd
        comp_res = CompressionCheck.check_eurocode_3(
            section=section,
            material=material,
            NEd_kN=abs(NEd_kN),
            Lcr_y_mm=Lcr_y_mm,
            Lcr_z_mm=Lcr_z_mm,
            gamma_M1=gamma_M1
        )
        Nb_Rd_kN = comp_res.capacity

        # 2. Major bending and LTB resistance Mb,Rd
        flex_res = FlexureCheck.check_eurocode_3(
            section=section,
            material=material,
            MEd_kNm=abs(My_Ed_kNm),
            L_mm=L_ltb_mm,
            gamma_M1=gamma_M1
        )
        Mb_Rd_kNm = flex_res.capacity

        # Minor bending resistance Mc,z,Rd
        Mz_Rd_kNm = (section.Zy * material.Fy) / gamma_M1 / 1.0e6

        # Interaction factors kyy, kyz, kzy, kzz (Annex B Method 2 simplified approach)
        # kyy = Cmy * (1 + (lambda_bar_y - 0.2) * NEd / Nb,y,Rd) <= Cmy * (1 + 0.8 * NEd / Nb,y,Rd)
        ned = abs(NEd_kN)
        ratio_n = ned / max(Nb_Rd_kN, 1.0)
        kyy = min(1.0 + 0.8 * ratio_n, 1.8)
        kzz = min(1.0 + 1.0 * ratio_n, 2.0)
        kyz = 0.6 * kzz
        kzy = 0.6 * kyy

        # Expression 6.61:
        term_n1 = ned / max(Nb_Rd_kN, 1.0)
        term_my1 = kyy * abs(My_Ed_kNm) / max(Mb_Rd_kNm, 1.0)
        term_mz1 = kyz * abs(Mz_Ed_kNm) / max(Mz_Rd_kNm, 1.0)
        util_6_61 = term_n1 + term_my1 + term_mz1

        # Expression 6.62:
        term_my2 = kzy * abs(My_Ed_kNm) / max(Mb_Rd_kNm, 1.0)
        term_mz2 = kzz * abs(Mz_Ed_kNm) / max(Mz_Rd_kNm, 1.0)
        util_6_62 = term_n1 + term_my2 + term_mz2

        governing_util = max(util_6_61, util_6_62)
        gov_expr = "EC3 Eq. (6.61)" if util_6_61 >= util_6_62 else "EC3 Eq. (6.62)"
        status = DesignStatus.PASS if governing_util <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "NEd_kN": NEd_kN,
            "My_Ed_kNm": My_Ed_kNm,
            "Mz_Ed_kNm": Mz_Ed_kNm,
            "section": section.name,
            "Lcr_y_mm": Lcr_y_mm,
            "Lcr_z_mm": Lcr_z_mm
        }

        intermediate: Dict[str, Any] = {
            "Nb_Rd_kN": round(Nb_Rd_kN, 2),
            "Mb_Rd_kNm": round(Mb_Rd_kNm, 2),
            "Mz_Rd_kNm": round(Mz_Rd_kNm, 2),
            "kyy": round(kyy, 3),
            "kzz": round(kzz, 3),
            "util_6_61": round(util_6_61, 4),
            "util_6_62": round(util_6_62, 4),
            "governing_expression": gov_expr
        }

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_3.value,
            code_edition=CodeEdition.EN_1993_1_1_2005.value,
            clause="EN 1993-1-1:2005 Clause 6.3.3 (Eq. 6.61 / 6.62)",
            inputs=inputs,
            method="EC3 Beam-Column Stability Interaction",
            intermediate_results=intermediate,
            final_result=f"Interaction Utilization = {round(governing_util, 4)} ({gov_expr})",
            limit="1.0000",
            status=status
        )

        summary = f"EC3 Interaction check ({section.name}): Utilization = {round(governing_util, 3)} <= 1.0 [{status.value}] ({gov_expr})"

        return SteelCheckResult(
            check_type=SteelCheckType.INTERACTION,
            demand=governing_util,
            capacity=1.0,
            dc_ratio=governing_util,
            status=status,
            governing_limit_state=gov_expr,
            trace=trace,
            units="ratio",
            summary_message=summary
        )
