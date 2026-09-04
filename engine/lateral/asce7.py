"""
STRUCTURE-X ULTIMATE — ASCE 7 SEISMIC & WIND ENGINE
Modular implementation of Equivalent Lateral Force (ELF) Seismic Procedure and
Directional MWFRS Wind Procedure strictly complying with ASCE 7-16 and ASCE 7-22.
"""

import math
from typing import Dict, Any, List, Optional, Tuple

from .types import (
    LateralCode,
    CodeEdition,
    SiteClass,
    RiskCategory,
    SeismicDesignCategory,
    ExposureCategory,
    DesignStatus,
    CalculationTrace,
    StoryLevel,
    SeismicParameters,
    WindParameters,
    StorySeismicResult,
    StoryWindResult,
    SeismicAnalysisResult,
    WindAnalysisResult,
)


class ASCE7Engine:
    """
    ASCE 7-16 and ASCE 7-22 Seismic & Wind calculation engine.
    """

    # -------------------------------------------------------------------------
    # SEISMIC PROVISIONS (Chapters 11 & 12)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_site_coefficients(
        site_class: SiteClass,
        Ss: float,
        S1: float,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[float, float, CalculationTrace]:
        """
        Determines short-period site coefficient Fa and 1-second site coefficient Fv
        per ASCE 7-16 Tables 11.4-1 and 11.4-2.
        """
        # --- Fa Calculation (Table 11.4-1) ---
        if site_class == SiteClass.A:
            Fa = 0.8
        elif site_class == SiteClass.B:
            Fa = 1.0 if edition == CodeEdition.ASCE_7_16 else 0.9
        elif site_class == SiteClass.C:
            if Ss <= 0.50:
                Fa = 1.30
            elif Ss <= 1.00:
                Fa = 1.30 - (Ss - 0.50) * 0.20  # 1.30 to 1.20
            else:
                Fa = 1.20
        elif site_class == SiteClass.D:
            if Ss <= 0.25:
                Fa = 1.60
            elif Ss <= 0.50:
                Fa = 1.60 - (Ss - 0.25) * (0.20 / 0.25)  # 1.60 to 1.40
            elif Ss <= 0.75:
                Fa = 1.40 - (Ss - 0.50) * (0.20 / 0.25)  # 1.40 to 1.20
            elif Ss <= 1.00:
                Fa = 1.20 - (Ss - 0.75) * (0.10 / 0.25)  # 1.20 to 1.10
            elif Ss <= 1.25:
                Fa = 1.10 - (Ss - 1.00) * (0.10 / 0.25)  # 1.10 to 1.00
            else:
                Fa = 1.00
        elif site_class == SiteClass.E:
            if Ss <= 0.25:
                Fa = 2.40
            elif Ss <= 0.50:
                Fa = 2.40 - (Ss - 0.25) * (0.70 / 0.25)  # 2.40 to 1.70
            elif Ss <= 0.75:
                Fa = 1.70 - (Ss - 0.50) * (0.40 / 0.25)  # 1.70 to 1.30
            elif Ss <= 1.00:
                Fa = 1.30 - (Ss - 0.75) * (0.40 / 0.25)  # 1.30 to 0.90
            else:
                Fa = 0.90
        else:  # Site Class F
            Fa = 1.00

        # --- Fv Calculation (Table 11.4-2) ---
        if site_class == SiteClass.A:
            Fv = 0.8
        elif site_class == SiteClass.B:
            Fv = 0.8 if edition == CodeEdition.ASCE_7_16 else 1.0
        elif site_class == SiteClass.C:
            if S1 <= 0.10:
                Fv = 1.50
            elif S1 <= 0.40:
                Fv = 1.50
            elif S1 <= 0.50:
                Fv = 1.50 - (S1 - 0.40) * (0.10 / 0.10)  # 1.50 to 1.40
            else:
                Fv = 1.40
        elif site_class == SiteClass.D:
            if S1 <= 0.10:
                Fv = 2.40
            elif S1 <= 0.20:
                Fv = 2.40 - (S1 - 0.10) * (0.20 / 0.10)  # 2.40 to 2.20
            elif S1 <= 0.30:
                Fv = 2.20 - (S1 - 0.20) * (0.20 / 0.10)  # 2.20 to 2.00
            elif S1 <= 0.40:
                Fv = 2.00 - (S1 - 0.30) * (0.10 / 0.10)  # 2.00 to 1.90
            elif S1 <= 0.50:
                Fv = 1.90 - (S1 - 0.40) * (0.10 / 0.10)  # 1.90 to 1.80
            else:
                Fv = 1.80
        elif site_class == SiteClass.E:
            if S1 <= 0.10:
                Fv = 4.20
            elif S1 <= 0.20:
                Fv = 4.20 - (S1 - 0.10) * (0.90 / 0.10)  # 4.20 to 3.30
            elif S1 <= 0.30:
                Fv = 3.30 - (S1 - 0.20) * (0.50 / 0.10)  # 3.30 to 2.80
            elif S1 <= 0.40:
                Fv = 2.80 - (S1 - 0.30) * (0.40 / 0.10)  # 2.80 to 2.40
            else:
                Fv = 2.40
        else:  # Site Class F
            Fv = 1.00

        inputs = {
            "site_class": site_class.value,
            "Ss": Ss,
            "S1": S1,
            "edition": edition.value
        }
        intermediate = {
            "Fa_interpolated": round(Fa, 3),
            "Fv_interpolated": round(Fv, 3)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Tables 11.4-1 and 11.4-2",
            inputs=inputs,
            method="Site Coefficient Interpolation based on Site Class, Ss, and S1",
            intermediate_results=intermediate,
            final_result=f"Fa = {round(Fa, 3)}, Fv = {round(Fv, 3)}",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return Fa, Fv, trace

    @staticmethod
    def calculate_design_spectral_parameters(
        Ss: float,
        S1: float,
        Fa: float,
        Fv: float,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[float, float, float, float, float, float, CalculationTrace]:
        """
        Computes SMS, SM1, SDS, SD1, Ts, and T0 per ASCE 7-16 Section 11.4.
        """
        # Eq. 11.4-1: SMS = Fa * Ss
        SMS = Fa * Ss
        # Eq. 11.4-2: SM1 = Fv * S1
        SM1 = Fv * S1
        # Eq. 11.4-3: SDS = (2/3) * SMS
        SDS = (2.0 / 3.0) * SMS
        # Eq. 11.4-4: SD1 = (2/3) * SM1
        SD1 = (2.0 / 3.0) * SM1

        Ts = SD1 / max(SDS, 0.001)
        T0 = 0.2 * Ts

        inputs = {
            "Ss": Ss,
            "S1": S1,
            "Fa": Fa,
            "Fv": Fv
        }
        intermediate = {
            "SMS_Eq_11_4_1": round(SMS, 4),
            "SM1_Eq_11_4_2": round(SM1, 4),
            "SDS_Eq_11_4_3": round(SDS, 4),
            "SD1_Eq_11_4_4": round(SD1, 4),
            "Ts_seconds": round(Ts, 4),
            "T0_seconds": round(T0, 4)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 11.4.4 & 11.4.5",
            inputs=inputs,
            method="Design Spectral Accelerations (SMS, SM1, SDS, SD1, Ts, T0)",
            intermediate_results=intermediate,
            final_result=f"SDS = {round(SDS, 4)}g, SD1 = {round(SD1, 4)}g, Ts = {round(Ts, 3)}s",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return SMS, SM1, SDS, SD1, Ts, T0, trace

    @staticmethod
    def determine_seismic_design_category(
        SDS: float,
        SD1: float,
        S1: float,
        risk_category: RiskCategory = RiskCategory.II,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[SeismicDesignCategory, CalculationTrace]:
        """
        Determines Seismic Design Category (SDC A through F) per ASCE 7-16 Section 11.6
        (Tables 11.6-1 and 11.6-2).
        """
        is_risk_iv = (risk_category == RiskCategory.IV)

        # Table 11.6-1 based on SDS
        if SDS < 0.167:
            sdc_sds = SeismicDesignCategory.A
        elif SDS < 0.33:
            sdc_sds = SeismicDesignCategory.C if is_risk_iv else SeismicDesignCategory.B
        elif SDS < 0.50:
            sdc_sds = SeismicDesignCategory.D if is_risk_iv else SeismicDesignCategory.C
        else:
            sdc_sds = SeismicDesignCategory.D

        # Table 11.6-2 based on SD1
        if SD1 < 0.067:
            sdc_sd1 = SeismicDesignCategory.A
        elif SD1 < 0.133:
            sdc_sd1 = SeismicDesignCategory.C if is_risk_iv else SeismicDesignCategory.B
        elif SD1 < 0.20:
            sdc_sd1 = SeismicDesignCategory.D if is_risk_iv else SeismicDesignCategory.C
        else:
            sdc_sd1 = SeismicDesignCategory.D

        # Special provision for high seismicity (Section 11.6)
        if S1 >= 0.75:
            sdc_governing = SeismicDesignCategory.F if is_risk_iv else SeismicDesignCategory.E
        else:
            # SDC is the more severe of SDC(SDS) and SDC(SD1)
            rank = {
                SeismicDesignCategory.A: 1,
                SeismicDesignCategory.B: 2,
                SeismicDesignCategory.C: 3,
                SeismicDesignCategory.D: 4,
                SeismicDesignCategory.E: 5,
                SeismicDesignCategory.F: 6,
            }
            sdc_governing = sdc_sds if rank[sdc_sds] >= rank[sdc_sd1] else sdc_sd1

        inputs = {
            "SDS": SDS,
            "SD1": SD1,
            "S1": S1,
            "risk_category": risk_category.value
        }
        intermediate = {
            "SDC_from_SDS_Table_11_6_1": sdc_sds.value,
            "SDC_from_SD1_Table_11_6_2": sdc_sd1.value,
            "S1_ge_0_75_check": S1 >= 0.75
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 11.6 (Tables 11.6-1 & 11.6-2)",
            inputs=inputs,
            method="Seismic Design Category Classification (A through F)",
            intermediate_results=intermediate,
            final_result=f"SDC = {sdc_governing.value}",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return sdc_governing, trace

    @staticmethod
    def calculate_approximate_period(
        total_height_m: float,
        system_type: str = "STEEL_MOMENT_FRAME",
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[float, CalculationTrace]:
        """
        Calculates approximate fundamental period Ta per ASCE 7-16 Section 12.8.2.1:
        Ta = Ct * hn^x (hn in meters).
        """
        sys_upper = system_type.upper()
        if "STEEL_MOMENT" in sys_upper or "SMF" in sys_upper:
            Ct = 0.0724
            x = 0.80
            desc = "Steel Moment-Resisting Frames"
        elif "CONCRETE_MOMENT" in sys_upper or "RC_MOMENT" in sys_upper:
            Ct = 0.0466
            x = 0.90
            desc = "Concrete Moment-Resisting Frames"
        elif "EBF" in sys_upper or "ECCENTRIC" in sys_upper or "BRBF" in sys_upper:
            Ct = 0.0731
            x = 0.75
            desc = "Steel Eccentrically / Buckling-Restrained Braced Frames"
        else:
            Ct = 0.0488
            x = 0.75
            desc = "All Other Structural Systems"

        Ta = Ct * (total_height_m ** x)

        inputs = {
            "total_height_hn_m": total_height_m,
            "structural_system": desc,
            "Ct": Ct,
            "x": x
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 12.8.2.1 (Eq. 12.8-7)",
            inputs=inputs,
            method=f"Approximate Fundamental Period Ta = Ct * hn^x ({desc})",
            intermediate_results={"Ct": Ct, "x": x, "hn_m": total_height_m},
            final_result=f"Ta = {round(Ta, 4)} s",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return Ta, trace

    @staticmethod
    def calculate_period_upper_limit(
        Ta: float,
        SD1: float,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[float, float, CalculationTrace]:
        """
        Calculates upper limit coefficient Cu and maximum period T_max = Cu * Ta
        per ASCE 7-16 Table 12.8-1.
        """
        if SD1 >= 0.40:
            Cu = 1.40
        elif SD1 >= 0.30:
            Cu = 1.40 + (0.40 - SD1) * (0.00 / 0.10)  # 1.40
        elif SD1 >= 0.20:
            Cu = 1.40 + (0.30 - SD1) * (0.10 / 0.10)  # 1.40 to 1.50
        elif SD1 >= 0.15:
            Cu = 1.50 + (0.20 - SD1) * (0.10 / 0.05)  # 1.50 to 1.60
        elif SD1 >= 0.10:
            Cu = 1.60 + (0.15 - SD1) * (0.10 / 0.05)  # 1.60 to 1.70
        else:
            Cu = 1.70

        T_max = Cu * Ta

        inputs = {"Ta_seconds": Ta, "SD1": SD1}
        intermediate = {"Cu_coefficient": round(Cu, 3), "T_max_seconds": round(T_max, 4)}

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Table 12.8-1 (Section 12.8.2)",
            inputs=inputs,
            method="Upper Limit on Calculated Period T <= Cu * Ta",
            intermediate_results=intermediate,
            final_result=f"Cu = {round(Cu, 3)}, T_max = {round(T_max, 4)} s",
            limit=f"{round(T_max, 4)} s",
            status=DesignStatus.PASS
        )

        return Cu, T_max, trace

    @staticmethod
    def calculate_seismic_response_coefficient_cs(
        SDS: float,
        SD1: float,
        S1: float,
        T_s: float,
        R: float,
        Ie: float = 1.00,
        TL_s: float = 8.0,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[float, str, CalculationTrace]:
        """
        Calculates the seismic response coefficient Cs per ASCE 7-16 Section 12.8.1.1.
        Eq 12.8-2: Cs = SDS / (R / Ie)
        Eq 12.8-3: Cs <= SD1 / (T * (R / Ie)) for T <= TL
        Eq 12.8-4: Cs <= (SD1 * TL) / (T^2 * (R / Ie)) for T > TL
        Eq 12.8-5: Cs >= max(0.044 * SDS * Ie, 0.01)
        Eq 12.8-6: If S1 >= 0.6: Cs >= 0.5 * S1 / (R / Ie)
        """
        R_over_Ie = R / max(Ie, 0.1)

        # 1. Base Cs formula (Eq. 12.8-2)
        cs_base = SDS / R_over_Ie

        # 2. Maximum Cs upper bound (Eq. 12.8-3 or 12.8-4)
        if T_s <= TL_s:
            cs_max = SD1 / (max(T_s, 0.01) * R_over_Ie)
            max_eq = "Eq. 12.8-3 (T <= TL)"
        else:
            cs_max = (SD1 * TL_s) / ((max(T_s, 0.01) ** 2) * R_over_Ie)
            max_eq = "Eq. 12.8-4 (T > TL)"

        # 3. Minimum Cs lower bound (Eq. 12.8-5 and 12.8-6)
        cs_min1 = max(0.044 * SDS * Ie, 0.01)
        min1_eq = "Eq. 12.8-5"

        cs_min2 = 0.0
        min2_eq = ""
        if S1 >= 0.60:
            cs_min2 = (0.50 * S1) / R_over_Ie
            min2_eq = "Eq. 12.8-6 (S1 >= 0.6g)"

        cs_min = max(cs_min1, cs_min2)

        # Determine governing value
        governing_formula = "Eq. 12.8-2 (Base Cs)"
        cs_governing = cs_base

        if cs_governing > cs_max:
            cs_governing = cs_max
            governing_formula = f"Governed by Upper Bound {max_eq}"

        if cs_governing < cs_min:
            cs_governing = cs_min
            active_min = min2_eq if (cs_min2 > cs_min1) else min1_eq
            governing_formula = f"Governed by Lower Bound {active_min}"

        inputs = {
            "SDS": SDS,
            "SD1": SD1,
            "S1": S1,
            "T_s": T_s,
            "R": R,
            "Ie": Ie,
            "TL_s": TL_s
        }

        intermediate = {
            "R_over_Ie": round(R_over_Ie, 3),
            "Cs_base_Eq_12_8_2": round(cs_base, 5),
            "Cs_max": round(cs_max, 5),
            "max_clause": max_eq,
            "Cs_min1_Eq_12_8_5": round(cs_min1, 5),
            "Cs_min2_Eq_12_8_6": round(cs_min2, 5),
            "Cs_min_governing": round(cs_min, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 12.8.1.1 (Eqs. 12.8-2 through 12.8-6)",
            inputs=inputs,
            method="Seismic Response Coefficient Cs with Upper & Lower Limits",
            intermediate_results=intermediate,
            final_result=f"Cs = {round(cs_governing, 5)} ({governing_formula})",
            limit=f"[{round(cs_min, 5)} <= Cs <= {round(cs_max, 5)}]",
            status=DesignStatus.PASS
        )

        return cs_governing, governing_formula, trace

    @staticmethod
    def calculate_seismic_vertical_distribution(
        base_shear_V_kN: float,
        stories: List[StoryLevel],
        T_s: float,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[List[float], List[float], List[float], float, CalculationTrace]:
        """
        Calculates vertical distribution factor Cvx, lateral story seismic forces Fx,
        story shears Vx, and overturning moments Mx per ASCE 7-16 Section 12.8.3.
        """
        # Distribution exponent k (Section 12.8.3)
        if T_s <= 0.50:
            k = 1.00
        elif T_s >= 2.50:
            k = 2.00
        else:
            k = 1.00 + (T_s - 0.50) / (2.50 - 0.50) * (2.00 - 1.00)

        # Denominator: sum(wi * hi^k)
        w_h_k = [story.weight_kN * (story.height_from_base_m ** k) for story in stories]
        denom = sum(w_h_k)
        if denom <= 0:
            denom = 1.0

        Cvx = [val / denom for val in w_h_k]
        Fx_kN = [c * base_shear_V_kN for c in Cvx]

        # Story shear Vx = sum of forces at and above level x
        n = len(stories)
        Vx_kN = [0.0] * n
        for i in range(n):
            Vx_kN[i] = sum(Fx_kN[j] for j in range(i, n))

        # Overturning moment at level x = sum(Fj * (hj - hx)) for j >= x
        Mx_kNm = [0.0] * n
        for i in range(n):
            hx = stories[i].height_from_base_m
            Mx_kNm[i] = sum(Fx_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))

        # Base overturning moment M0 = sum(Fi * hi)
        M0_kNm = sum(Fx_kN[i] * stories[i].height_from_base_m for i in range(n))

        inputs = {
            "base_shear_V_kN": base_shear_V_kN,
            "period_T_s": T_s,
            "num_stories": n
        }
        intermediate = {
            "distribution_exponent_k": round(k, 3),
            "sum_w_h_k": round(denom, 2),
            "base_overturning_M0_kNm": round(M0_kNm, 2)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 12.8.3 (Eqs. 12.8-11 & 12.8-12)",
            inputs=inputs,
            method="Vertical Distribution of Seismic Forces Fx = Cvx * V",
            intermediate_results=intermediate,
            final_result=f"Base Shear V = {round(base_shear_V_kN, 2)} kN, Base Overturning M0 = {round(M0_kNm, 2)} kN*m",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return Cvx, Fx_kN, Vx_kN, M0_kNm, trace

    @staticmethod
    def calculate_seismic_drifts_and_stability(
        stories: List[StoryLevel],
        Fx_kN: List[float],
        Vx_kN: List[float],
        Cd: float,
        Ie: float,
        risk_category: RiskCategory = RiskCategory.II,
        beta: float = 1.0,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> Tuple[List[StorySeismicResult], float, str, float, DesignStatus, CalculationTrace]:
        """
        Calculates elastic deflections dxe, amplified design displacements dx,
        interstory drifts delta, allowable drifts delta_a, and P-Delta stability coefficients theta
        per ASCE 7-16 Section 12.8.6 and Section 12.8.7.
        """
        # Allowable drift limit ratio (Table 12.12-1)
        if risk_category in (RiskCategory.I, RiskCategory.II):
            allowable_ratio = 0.020
        elif risk_category == RiskCategory.III:
            allowable_ratio = 0.015
        else:  # Risk Category IV
            allowable_ratio = 0.010

        # Maximum stability coefficient theta_max (Eq. 12.8-17): theta_max = 0.5 / (beta * Cd) <= 0.25
        theta_max = min(0.50 / max(beta * Cd, 0.1), 0.25)

        n = len(stories)
        dxe_mm = [0.0] * n  # Elastic displacements
        dx_mm = [0.0] * n   # Inelastic design displacements
        story_results: List[StorySeismicResult] = []

        overall_status = DesignStatus.PASS
        max_drift_ratio = 0.0
        max_drift_story = ""
        max_theta = 0.0

        cum_dxe = 0.0
        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0

            # First-order interstory elastic shear deflection: delta_e = Vx / K_story
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)
            inter_dxe = Vx_kN[i] / k_story
            cum_dxe += inter_dxe
            dxe_mm[i] = cum_dxe

            # Amplified total displacement dx = Cd * dxe / Ie (Eq. 12.8-15)
            dx_mm[i] = (Cd * dxe_mm[i]) / max(Ie, 0.1)

            # Design story drift delta = dx[i] - dx[i-1] (Eq. 12.8-16)
            prev_dx = dx_mm[i - 1] if i > 0 else 0.0
            delta_mm = dx_mm[i] - prev_dx
            delta_a_mm = allowable_ratio * hsx_mm

            drift_ratio = delta_mm / hsx_mm if hsx_mm > 0 else 0.0
            drift_pass = delta_mm <= delta_a_mm
            drift_status = DesignStatus.PASS if drift_pass else DesignStatus.FAIL

            if not drift_pass:
                overall_status = DesignStatus.FAIL

            if drift_ratio > max_drift_ratio:
                max_drift_ratio = drift_ratio
                max_drift_story = story.name

            # Cumulative vertical gravity load at and above level x: Px
            # Px = sum(Wj for j >= i)
            Px_kN = sum(stories[j].weight_kN for j in range(i, n))

            # P-Delta stability coefficient theta = (Px * delta * Ie) / (Vx * hsx * Cd) (Eq. 12.8-16)
            denom = Vx_kN[i] * hsx_mm * Cd
            if denom > 0:
                theta = (Px_kN * delta_mm * Ie) / denom
            else:
                theta = 0.0

            if theta > max_theta:
                max_theta = theta

            if theta > theta_max:
                overall_status = DesignStatus.FAIL
                drift_status = DesignStatus.FAIL

            story_res = StorySeismicResult(
                level_index=story.level_index,
                name=story.name,
                height_from_base_m=story.height_from_base_m,
                story_height_m=story.story_height_m,
                weight_kN=story.weight_kN,
                Cvx_distribution_factor=0.0,  # updated by caller
                story_force_Fx_kN=Fx_kN[i],
                story_shear_Vx_kN=Vx_kN[i],
                story_overturning_Mx_kNm=0.0, # updated by caller
                elastic_displacement_dxe_mm=dxe_mm[i],
                design_displacement_dx_mm=dx_mm[i],
                story_drift_delta_mm=delta_mm,
                allowable_drift_delta_a_mm=delta_a_mm,
                drift_ratio=drift_ratio,
                allowable_drift_ratio=allowable_ratio,
                stability_coefficient_theta=theta,
                drift_status=drift_status
            )
            story_results.append(story_res)

        inputs = {
            "Cd": Cd,
            "Ie": Ie,
            "risk_category": risk_category.value,
            "allowable_drift_ratio": allowable_ratio,
            "theta_max": round(theta_max, 4)
        }
        intermediate = {
            "max_drift_ratio": round(max_drift_ratio, 5),
            "max_drift_story": max_drift_story,
            "max_stability_theta": round(max_theta, 4)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Section 12.8.6 & 12.8.7 (Eqs. 12.8-15, 12.8-16, 12.8-17)",
            inputs=inputs,
            method="Story Drift Amplification dx = Cd*dxe/Ie & P-Delta Stability Coefficient theta",
            intermediate_results=intermediate,
            final_result=f"Max Drift Ratio = {round(max_drift_ratio, 5)} (Limit: {allowable_ratio}), Max theta = {round(max_theta, 4)} (Limit: {round(theta_max, 3)})",
            limit=f"Delta <= {allowable_ratio}*hsx, theta <= {round(theta_max, 3)}",
            status=overall_status
        )

        return story_results, max_drift_ratio, max_drift_story, max_theta, overall_status, trace

    # -------------------------------------------------------------------------
    # WIND PROVISIONS (Chapters 26 & 27 — MWFRS Directional Procedure)
    # -------------------------------------------------------------------------

    @staticmethod
    def calculate_velocity_pressure_exposure_coeff_kz(
        z_m: float,
        exposure: ExposureCategory = ExposureCategory.C,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> float:
        """
        Velocity pressure exposure coefficient Kz per ASCE 7-16 Table 26.10-1 (Eq. 26.10-1):
        Kz = 2.01 * (z / zg)^(2 / alpha) for 4.6 m <= z <= zg.
        """
        if exposure == ExposureCategory.B:
            alpha = 7.0
            zg_m = 365.76  # 1200 ft
            z_min_m = 9.14 # 30 ft
        elif exposure == ExposureCategory.D:
            alpha = 11.5
            zg_m = 213.36  # 700 ft
            z_min_m = 2.13 # 7 ft
        else:  # Exposure C
            alpha = 9.5
            zg_m = 274.32  # 900 ft
            z_min_m = 4.57 # 15 ft

        eff_z = min(max(z_m, z_min_m), zg_m)
        kz = 2.01 * ((eff_z / zg_m) ** (2.0 / alpha))
        return max(kz, 0.70)

    @staticmethod
    def calculate_velocity_pressure_qz(
        V_mps: float,
        Kz: float,
        Kzt: float = 1.0,
        Kd: float = 0.85,
        Ke: float = 1.0,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> float:
        """
        Calculates velocity pressure qz (N/m^2) per ASCE 7-16 Eq. 26.10-1:
        qz = 0.613 * Kz * Kzt * Kd * Ke * V^2 (SI metric units, V in m/s).
        """
        # qz in N/m2
        return 0.613 * Kz * Kzt * Kd * Ke * (V_mps ** 2)

    @staticmethod
    def calculate_wind_forces_and_drift(
        stories: List[StoryLevel],
        params: WindParameters,
        edition: CodeEdition = CodeEdition.ASCE_7_16,
    ) -> WindAnalysisResult:
        """
        Executes ASCE 7-16 / 7-22 MWFRS Directional Wind Procedure:
        Generates:
        - Story Wind Forces (Fw)
        - Story Shear (Vw)
        - Base Shear
        - Overturning Moment (Mw)
        - Drift and drift ratios checked against serviceability limit.
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m

        # Top level mean roof height velocity pressure qh
        Kz_roof = ASCE7Engine.calculate_velocity_pressure_exposure_coeff_kz(total_height_m, params.exposure_category, edition)
        qh_N_m2 = ASCE7Engine.calculate_velocity_pressure_qz(
            params.basic_wind_speed_mps, Kz_roof, params.Kzt_topographic, params.Kd_directionality, params.Ke_elevation, edition
        )

        G = params.G_gust_factor
        Cp_w = params.Cp_windward
        Cp_l = params.Cp_leeward

        story_results: List[StoryWindResult] = []
        Fw_kN = [0.0] * n
        Vw_kN = [0.0] * n
        Mw_kNm = [0.0] * n

        # 1. Calculate pressure and forces at each level
        for i in range(n):
            story = stories[i]
            z = story.height_from_base_m

            # Tributary height
            h_below = story.story_height_m
            h_above = (stories[i + 1].height_from_base_m - z) if i < n - 1 else (story.story_height_m * 0.5)
            h_trib = (h_below * 0.5) + (h_above * 0.5) if i < n - 1 else (h_below * 0.5)
            if i == 0:
                h_trib = story.story_height_m * 0.5 + (stories[1].height_from_base_m - z) * 0.5 if n > 1 else story.story_height_m

            trib_area_m2 = story.width_m * h_trib

            # Velocity pressure at this elevation
            kz = ASCE7Engine.calculate_velocity_pressure_exposure_coeff_kz(z, params.exposure_category, edition)
            qz = ASCE7Engine.calculate_velocity_pressure_qz(
                params.basic_wind_speed_mps, kz, params.Kzt_topographic, params.Kd_directionality, params.Ke_elevation, edition
            )

            # Design pressures:
            # Windward pressure p_w(z) = qz * G * Cp_w
            # Leeward suction p_l = qh * G * Cp_l (evaluated at roof height qh)
            p_windward = qz * G * Cp_w
            p_leeward = qh_N_m2 * G * Cp_l
            net_pressure = p_windward - p_leeward  # subtracting negative suction gives sum

            # Story horizontal wind force Fw = net_pressure * trib_area / 1000 (kN)
            force_kN = (net_pressure * trib_area_m2) / 1000.0
            Fw_kN[i] = force_kN

            story_results.append(
                StoryWindResult(
                    level_index=story.level_index,
                    name=story.name,
                    height_from_base_m=story.height_from_base_m,
                    story_height_m=story.story_height_m,
                    tributary_height_m=h_trib,
                    width_m=story.width_m,
                    tributary_area_m2=trib_area_m2,
                    Kz_exposure_coeff=kz,
                    velocity_pressure_qz_N_m2=qz,
                    windward_pressure_p_N_m2=p_windward,
                    leeward_pressure_p_N_m2=p_leeward,
                    net_design_pressure_N_m2=net_pressure,
                    story_wind_force_Fw_kN=force_kN,
                    story_wind_shear_Vw_kN=0.0,
                    story_overturning_Mw_kNm=0.0,
                    lateral_displacement_mm=0.0,
                    story_drift_mm=0.0,
                    drift_ratio=0.0,
                    allowable_drift_ratio=0.0025,  # H/400 serviceability limit
                    drift_status=DesignStatus.PASS
                )
            )

        # 2. Cumulative Story Shear and Overturning Moments
        for i in range(n):
            Vw_kN[i] = sum(Fw_kN[j] for j in range(i, n))
            hx = stories[i].height_from_base_m
            Mw_kNm[i] = sum(Fw_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))
            story_results[i].story_wind_shear_Vw_kN = Vw_kN[i]
            story_results[i].story_overturning_Mw_kNm = Mw_kNm[i]

        base_shear_Vw_kN = sum(Fw_kN)
        base_overturning_Mw0_kNm = sum(Fw_kN[i] * stories[i].height_from_base_m for i in range(n))

        # 3. Wind Drift Calculation (Serviceability Limit H/400 = 0.0025)
        allowable_drift_ratio = 0.0025  # 1/400
        cum_disp_mm = 0.0
        max_drift_ratio = 0.0
        max_drift_story = ""
        overall_status = DesignStatus.PASS

        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)

            # Story shear deflection under wind service load (0.6W or service wind)
            # Typically evaluated at nominal wind speed or service factor
            inter_drift_mm = Vw_kN[i] / k_story
            cum_disp_mm += inter_drift_mm

            drift_ratio = inter_drift_mm / hsx_mm if hsx_mm > 0 else 0.0
            story_results[i].lateral_displacement_mm = cum_disp_mm
            story_results[i].story_drift_mm = inter_drift_mm
            story_results[i].drift_ratio = drift_ratio
            story_results[i].allowable_drift_ratio = allowable_drift_ratio

            is_pass = drift_ratio <= allowable_drift_ratio
            story_results[i].drift_status = DesignStatus.PASS if is_pass else DesignStatus.FAIL
            if not is_pass:
                overall_status = DesignStatus.FAIL

            if drift_ratio > max_drift_ratio:
                max_drift_ratio = drift_ratio
                max_drift_story = story.name

        inputs = {
            "basic_wind_speed_mps": params.basic_wind_speed_mps,
            "exposure_category": params.exposure_category.value,
            "G_gust_factor": params.G_gust_factor,
            "Cp_windward": params.Cp_windward,
            "Cp_leeward": params.Cp_leeward,
            "total_height_m": total_height_m
        }
        intermediate = {
            "qh_roof_pressure_N_m2": round(qh_N_m2, 2),
            "base_shear_Vw_kN": round(base_shear_Vw_kN, 2),
            "base_overturning_Mw0_kNm": round(base_overturning_Mw0_kNm, 2),
            "max_top_displacement_mm": round(cum_disp_mm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.ASCE_7.value,
            code_edition=edition.value,
            clause="ASCE 7-16 Chapters 26 & 27 (MWFRS Directional Procedure)",
            inputs=inputs,
            method="ASCE 7 Velocity Pressure qz & Directional MWFRS Design Wind Pressure p = q*G*Cp",
            intermediate_results=intermediate,
            final_result=f"Wind Base Shear = {round(base_shear_Vw_kN, 2)} kN, Base Overturning = {round(base_overturning_Mw0_kNm, 2)} kN*m",
            limit="Wind Drift Ratio <= 0.0025 (H/400)",
            status=overall_status
        )

        return WindAnalysisResult(
            code=LateralCode.ASCE_7,
            edition=edition,
            parameters=params,
            total_building_height_m=total_height_m,
            base_shear_Vw_kN=base_shear_Vw_kN,
            base_overturning_moment_Mw0_kNm=base_overturning_Mw0_kNm,
            max_top_displacement_mm=cum_disp_mm,
            max_drift_ratio=max_drift_ratio,
            max_drift_story=max_drift_story,
            overall_drift_status=overall_status,
            story_results=story_results,
            trace=trace
        )
