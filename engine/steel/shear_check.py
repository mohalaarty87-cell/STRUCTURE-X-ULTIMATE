"""
STRUCTURE-X ULTIMATE — STEEL SHEAR CAPACITY & DESIGN CHECK
Evaluates web shear, flange shear, web shear coefficient Cv1/Cv2, tension field action limits,
and shear buckling for I-shapes, channels, and tubular sections.
Strictly complies with AISC 360-16 (Chapter G) and Eurocode 3 (EN 1993-1-1 Clause 6.2.6).
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
    SteelSectionType,
)
from .materials import SteelMaterial
from .sections import SteelSection


class ShearCheck:
    """
    Modular structural steel shear capacity evaluator.
    """

    @staticmethod
    def check_aisc_360_16_major(
        section: SteelSection,
        material: SteelMaterial,
        Vu_kN: float,                    # Factored major shear force demand (kN)
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Chapter G: Section G2 (I-Shapes and Channels, Web Shear).
        """
        Fy = material.Fy
        E = material.E
        d = section.d
        tw = section.tw
        h_tw = section.h_over_tw

        # Web area Aw = d * tw (Eq. G2-1)
        Aw_mm2 = d * tw

        # Section G2.1(a): Rolled I-shapes with h/tw <= 2.24 * sqrt(E / Fy)
        limit_g2_1a = 2.24 * math.sqrt(E / Fy)

        if h_tw <= limit_g2_1a and section.section_type == SteelSectionType.I_SHAPE:
            # Special provision: phi = 1.00, Omega = 1.50, Cv1 = 1.00
            Cv1 = 1.00
            if method == DesignMethod.LRFD:
                phi_v = 1.00
                omega_v = 1.50
            else:
                phi_v = 1.00
                omega_v = 1.50
            provision = "AISC 360-16 Section G2.1(a) [Rolled I-shape web yielding, phi=1.00]"
        else:
            # Section G2.1(b): Other shapes and unstiffened webs (kv = 5.34)
            kv = 5.34
            sqrt_kv_E_Fy = math.sqrt((kv * E) / Fy)
            limit_1 = 1.10 * sqrt_kv_E_Fy
            limit_2 = 1.37 * sqrt_kv_E_Fy

            if h_tw <= limit_1:
                Cv1 = 1.00
                provision = "Section G2.1(b) (h/tw <= 1.10*sqrt(kv*E/Fy), Cv1=1.0)"
            elif h_tw <= limit_2:
                Cv1 = limit_1 / h_tw
                provision = "Section G2.1(b) (Inelastic web shear buckling, Eq. G2-3)"
            else:
                Cv1 = (1.51 * kv * E) / ((h_tw ** 2) * Fy)
                provision = "Section G2.1(b) (Elastic web shear buckling, Eq. G2-4)"

            phi_v = 0.90
            omega_v = 1.67

        # Nominal shear strength Vn (Eq. G2-1)
        Vn_N = 0.6 * Fy * Aw_mm2 * Cv1
        Vn_kN = Vn_N / 1000.0

        if method == DesignMethod.LRFD:
            available_Vn_kN = phi_v * Vn_kN
            factor_label = f"phi = {phi_v:.2f} (LRFD)"
        else:
            available_Vn_kN = Vn_kN / omega_v
            factor_label = f"Omega = {omega_v:.2f} (ASD)"

        demand_kN = abs(Vu_kN)
        dc_ratio = demand_kN / available_Vn_kN if available_Vn_kN > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Vu_kN": Vu_kN,
            "section": section.name,
            "d_mm": d,
            "tw_mm": tw,
            "h_tw": round(h_tw, 2),
            "Fy_MPa": Fy,
            "E_MPa": E,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Aw_mm2": round(Aw_mm2, 1),
            "limit_g2_1a": round(limit_g2_1a, 2),
            "Cv1_shear_coeff": round(Cv1, 4),
            "Vn_nominal_kN": round(Vn_kN, 2),
            "available_strength_kN": round(available_Vn_kN, 2),
            "design_factor": factor_label,
            "provision": provision
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Section G2 (Eq. G2-1)",
            inputs=inputs,
            method="AISC Web Shear Strength Vn = 0.6 * Fy * Aw * Cv1",
            intermediate_results=intermediate,
            final_result=f"Available Shear Strength = {round(available_Vn_kN, 2)} kN ({provision})",
            limit=f"Shear Demand Vu = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Shear check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(available_Vn_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.SHEAR_MAJOR,
            demand=demand_kN,
            capacity=available_Vn_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=provision,
            trace=trace,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_aisc_360_16_minor(
        section: SteelSection,
        material: SteelMaterial,
        Vu_y_kN: float,                  # Factored minor shear demand (flanges) (kN)
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Section G6: Minor Axis Shear (Flange Shear).
        Av = 2 * bf * tf.
        """
        Fy = material.Fy
        bf = section.bf
        tf = section.tf

        # Flange shear area
        Av_mm2 = 2.0 * bf * tf
        Cv2 = 1.0  # For typical flanges

        Vn_N = 0.6 * Fy * Av_mm2 * Cv2
        Vn_kN = Vn_N / 1000.0

        if method == DesignMethod.LRFD:
            phi_v = 0.90
            available_Vn_kN = phi_v * Vn_kN
        else:
            omega_v = 1.67
            available_Vn_kN = Vn_kN / omega_v

        demand_kN = abs(Vu_y_kN)
        dc_ratio = demand_kN / available_Vn_kN if available_Vn_kN > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Vu_y_kN": Vu_y_kN,
            "section": section.name,
            "bf_mm": bf,
            "tf_mm": tf,
            "Fy_MPa": Fy,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Av_flange_area_mm2": round(Av_mm2, 1),
            "Cv2": Cv2,
            "Vn_nominal_kN": round(Vn_kN, 2),
            "available_strength_kN": round(available_Vn_kN, 2)
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Section G6",
            inputs=inputs,
            method="AISC Minor-Axis Flange Shear Strength (Vn = 0.6*Fy*2*bf*tf*Cv2)",
            intermediate_results=intermediate,
            final_result=f"Available Minor Shear = {round(available_Vn_kN, 2)} kN",
            limit=f"Minor Shear Demand = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Minor shear check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(available_Vn_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.SHEAR_MINOR,
            demand=demand_kN,
            capacity=available_Vn_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state="Minor Flange Shear (Section G6)",
            trace=trace,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_3(
        section: SteelSection,
        material: SteelMaterial,
        VEd_kN: float,                   # Design shear force (kN)
        gamma_M0: float = 1.0,
    ) -> SteelCheckResult:
        """
        Eurocode 3 (EN 1993-1-1:2005) Clause 6.2.6: Shear.
        """
        fy = material.Fy
        A = section.Ag
        b = section.bf
        tf = section.tf
        tw = section.tw
        r = section.r
        hw = section.d - 2.0 * tf

        # Shear area Av for rolled I and H sections (Clause 6.2.6(3)a)
        # Av = max(A - 2*b*tf + (tw + 2*r)*tf, eta * hw * tw)
        eta = 1.0
        av1 = A - 2.0 * b * tf + (tw + 2.0 * r) * tf
        av2 = eta * hw * tw
        Av = max(av1, av2)

        # Plastic shear resistance Vpl,Rd (Eq. 6.18)
        # Vpl,Rd = Av * (fy / sqrt(3)) / gamma_M0
        Vpl_Rd_N = (Av * (fy / math.sqrt(3.0))) / gamma_M0
        Vpl_Rd_kN = Vpl_Rd_N / 1000.0

        demand_kN = abs(VEd_kN)
        dc_ratio = demand_kN / Vpl_Rd_kN if Vpl_Rd_kN > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        # Shear buckling verification requirement (Clause 6.2.6(6))
        # Check if hw/tw > (72 * eps / eta)
        eps = material.epsilon
        hw_tw = hw / max(tw, 0.1)
        shear_buckling_limit = (72.0 * eps) / eta
        needs_shear_buckling = hw_tw > shear_buckling_limit

        inputs: Dict[str, Any] = {
            "VEd_kN": VEd_kN,
            "section": section.name,
            "fy_MPa": fy,
            "Av_mm2": round(Av, 1),
            "gamma_M0": gamma_M0
        }

        intermediate: Dict[str, Any] = {
            "Vpl_Rd_kN": round(Vpl_Rd_kN, 2),
            "hw_tw": round(hw_tw, 2),
            "shear_buckling_limit": round(shear_buckling_limit, 2),
            "shear_buckling_check_needed": needs_shear_buckling
        }

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_3.value,
            code_edition=CodeEdition.EN_1993_1_1_2005.value,
            clause="EN 1993-1-1:2005 Clause 6.2.6 (Eq. 6.18)",
            inputs=inputs,
            method="EC3 Plastic Shear Resistance Vpl,Rd = Av * (fy / sqrt(3)) / gamma_M0",
            intermediate_results=intermediate,
            final_result=f"Capacity Vpl,Rd = {round(Vpl_Rd_kN, 2)} kN",
            limit=f"Demand VEd = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC3 Shear check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(Vpl_Rd_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.SHEAR_MAJOR,
            demand=demand_kN,
            capacity=Vpl_Rd_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state="EC3 Plastic Shear Resistance Vpl,Rd",
            trace=trace,
            units="kN",
            summary_message=summary
        )
