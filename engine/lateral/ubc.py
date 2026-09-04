"""
STRUCTURE-X ULTIMATE — UBC 1997 SEISMIC & WIND ENGINE
Modular implementation strictly complying with Uniform Building Code (UBC 1997)
Chapter 16: Structural Forces (Division IV - Earthquake, Division III - Wind).
"""

import math
from typing import Dict, Any, List, Optional, Tuple

from .types import (
    LateralCode,
    CodeEdition,
    SoilProfileUBC,
    RiskCategory,
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


class UBCEngine:
    """
    Uniform Building Code (UBC 1997) Seismic and Wind Engine.
    Implements Zone Factor Z, Soil Profile Ca & Cv, Near-Source Na/Nv,
    Base Shear Bounds (Eqs. 30-4, 30-5, 30-6, 30-7), Top Force Ft,
    and Inelastic Drift Delta_M = 0.70 * R * Delta_S.
    """

    # -------------------------------------------------------------------------
    # UBC 1997 SEISMIC (Section 1626 - 1634)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_seismic_coefficients(
        zone_factor_Z: float,
        soil_profile: SoilProfileUBC,
        Na: float = 1.0,
        Nv: float = 1.0,
    ) -> Tuple[float, float, CalculationTrace]:
        """
        Determines seismic coefficients Ca and Cv per UBC 1997 Tables 16-Q and 16-R.
        """
        # Table 16-Q (Ca)
        if zone_factor_Z >= 0.40:  # Zone 4
            ca_table = {
                SoilProfileUBC.SA: 0.32 * Na,
                SoilProfileUBC.SB: 0.40 * Na,
                SoilProfileUBC.SC: 0.40 * Na,
                SoilProfileUBC.SD: 0.44 * Na,
                SoilProfileUBC.SE: 0.36 * Na,
                SoilProfileUBC.SF: 0.44 * Na,
            }
        elif zone_factor_Z >= 0.30:  # Zone 3
            ca_table = {
                SoilProfileUBC.SA: 0.24,
                SoilProfileUBC.SB: 0.30,
                SoilProfileUBC.SC: 0.33,
                SoilProfileUBC.SD: 0.36,
                SoilProfileUBC.SE: 0.36,
                SoilProfileUBC.SF: 0.36,
            }
        elif zone_factor_Z >= 0.20:  # Zone 2B
            ca_table = {
                SoilProfileUBC.SA: 0.16,
                SoilProfileUBC.SB: 0.20,
                SoilProfileUBC.SC: 0.24,
                SoilProfileUBC.SD: 0.28,
                SoilProfileUBC.SE: 0.34,
                SoilProfileUBC.SF: 0.28,
            }
        else:  # Zone 1
            ca_table = {
                SoilProfileUBC.SA: 0.06,
                SoilProfileUBC.SB: 0.08,
                SoilProfileUBC.SC: 0.09,
                SoilProfileUBC.SD: 0.12,
                SoilProfileUBC.SE: 0.19,
                SoilProfileUBC.SF: 0.12,
            }

        Ca = ca_table.get(soil_profile, 0.44 * Na)

        # Table 16-R (Cv)
        if zone_factor_Z >= 0.40:  # Zone 4
            cv_table = {
                SoilProfileUBC.SA: 0.32 * Nv,
                SoilProfileUBC.SB: 0.40 * Nv,
                SoilProfileUBC.SC: 0.56 * Nv,
                SoilProfileUBC.SD: 0.64 * Nv,
                SoilProfileUBC.SE: 0.96 * Nv,
                SoilProfileUBC.SF: 0.64 * Nv,
            }
        elif zone_factor_Z >= 0.30:  # Zone 3
            cv_table = {
                SoilProfileUBC.SA: 0.24,
                SoilProfileUBC.SB: 0.30,
                SoilProfileUBC.SC: 0.45,
                SoilProfileUBC.SD: 0.54,
                SoilProfileUBC.SE: 0.84,
                SoilProfileUBC.SF: 0.54,
            }
        elif zone_factor_Z >= 0.20:  # Zone 2B
            cv_table = {
                SoilProfileUBC.SA: 0.16,
                SoilProfileUBC.SB: 0.20,
                SoilProfileUBC.SC: 0.32,
                SoilProfileUBC.SD: 0.40,
                SoilProfileUBC.SE: 0.64,
                SoilProfileUBC.SF: 0.40,
            }
        else:  # Zone 1
            cv_table = {
                SoilProfileUBC.SA: 0.06,
                SoilProfileUBC.SB: 0.08,
                SoilProfileUBC.SC: 0.13,
                SoilProfileUBC.SD: 0.18,
                SoilProfileUBC.SE: 0.35,
                SoilProfileUBC.SF: 0.18,
            }

        Cv = cv_table.get(soil_profile, 0.64 * Nv)

        inputs = {
            "zone_factor_Z": zone_factor_Z,
            "soil_profile": soil_profile.value,
            "Na": Na,
            "Nv": Nv
        }
        intermediate = {
            "Ca_coefficient": round(Ca, 3),
            "Cv_coefficient": round(Cv, 3)
        }

        trace = CalculationTrace(
            design_code=LateralCode.UBC.value,
            code_edition=CodeEdition.UBC_1997.value,
            clause="UBC 1997 Section 1629 (Tables 16-Q and 16-R)",
            inputs=inputs,
            method="UBC 1997 Seismic Coefficients Ca and Cv from Soil Profile & Zone Factor",
            intermediate_results=intermediate,
            final_result=f"Ca = {round(Ca, 3)}, Cv = {round(Cv, 3)}",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return Ca, Cv, trace

    @staticmethod
    def calculate_approximate_period(
        total_height_m: float,
        system_type: str = "STEEL_MOMENT_FRAME",
    ) -> Tuple[float, CalculationTrace]:
        """
        Calculates fundamental period T per UBC 1997 Section 1630.2.2 (Method A Eq. 30-8):
        T = Ct * (hn)^0.75 (hn in meters)
        """
        sys_upper = system_type.upper()
        if "STEEL_MOMENT" in sys_upper or "SMRF" in sys_upper:
            Ct = 0.0853  # (0.035 in feet)
            desc = "Steel Moment-Resisting Frames"
        elif "CONCRETE_MOMENT" in sys_upper:
            Ct = 0.0731  # (0.030 in feet)
            desc = "Reinforced Concrete Moment-Resisting Frames"
        else:
            Ct = 0.0488  # (0.020 in feet)
            desc = "All Other Buildings"

        T = Ct * (total_height_m ** 0.75)

        inputs = {"total_height_hn_m": total_height_m, "Ct": Ct, "system": desc}
        trace = CalculationTrace(
            design_code=LateralCode.UBC.value,
            code_edition=CodeEdition.UBC_1997.value,
            clause="UBC 1997 Section 1630.2.2 (Method A, Eq. 30-8)",
            inputs=inputs,
            method=f"Fundamental Period Method A: T = Ct * hn^0.75 ({desc})",
            intermediate_results={"Ct": Ct, "hn_m": total_height_m},
            final_result=f"T = {round(T, 4)} s",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return T, trace

    @staticmethod
    def calculate_base_shear_and_distribution(
        stories: List[StoryLevel],
        params: SeismicParameters,
        system_type: str = "STEEL_MOMENT_FRAME",
    ) -> Tuple[SeismicAnalysisResult, CalculationTrace]:
        """
        Executes UBC 1997 Section 1630 Static Force Procedure:
        - Base Shear Equations:
          Eq. 30-4: V = (Cv * I) / (R * T) * W
          Eq. 30-5: V <= (2.5 * Ca * I) / R * W
          Eq. 30-6: V >= 0.11 * Ca * I * W
          Eq. 30-7: In Zone 4, V >= (0.8 * Z * Nv * I) / R * W
        - Vertical distribution with top force Ft:
          If T > 0.7 s: Ft = 0.07 * T * V <= 0.25 * V
          Fx = (V - Ft) * (wx * hx) / sum(wi * hi)
          (At roof: F_roof = F_roof + Ft)
        - Inelastic drift Delta_M = 0.70 * R * Delta_S
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m
        total_weight_W = sum(s.weight_kN for s in stories)

        # 1. Seismic Coefficients Ca, Cv
        Ca, Cv, _ = UBCEngine.get_seismic_coefficients(
            params.Z_factor_ubc, params.soil_profile_ubc, params.Na_ubc, params.Nv_ubc
        )
        params.Ca_ubc = Ca
        params.Cv_ubc = Cv

        # 2. Fundamental Period
        T, _ = UBCEngine.calculate_approximate_period(total_height_m, system_type)

        R = params.R
        I = params.importance_factor
        Z = params.Z_factor_ubc
        Nv = params.Nv_ubc

        # 3. Design Base Shear Limits
        # Eq. 30-4: Base formula
        v_base_ratio = (Cv * I) / max(R * T, 0.01)
        # Eq. 30-5: Upper limit
        v_max_ratio = (2.5 * Ca * I) / R
        # Eq. 30-6: Lower limit 1
        v_min1_ratio = 0.11 * Ca * I
        # Eq. 30-7: Lower limit in Zone 4
        v_min2_ratio = (0.80 * Z * Nv * I) / R if Z >= 0.40 else 0.0

        v_min_ratio = max(v_min1_ratio, v_min2_ratio)

        # Apply bounds
        v_ratio = min(v_base_ratio, v_max_ratio)
        v_ratio = max(v_ratio, v_min_ratio)

        governing_formula = "Eq. 30-4 (Standard Base Shear)"
        if v_base_ratio > v_max_ratio:
            governing_formula = "Eq. 30-5 (Upper Bound: 2.5*Ca*I/R)"
        elif v_ratio == v_min2_ratio and v_min2_ratio > 0:
            governing_formula = "Eq. 30-7 (Zone 4 Near-Source Lower Bound: 0.8*Z*Nv*I/R)"
        elif v_ratio == v_min1_ratio:
            governing_formula = "Eq. 30-6 (Absolute Lower Bound: 0.11*Ca*I)"

        base_shear_V_kN = v_ratio * total_weight_W

        # 4. Vertical Distribution (Section 1630.5)
        # Top concentrated force Ft
        if T > 0.70:
            Ft_kN = min(0.07 * T * base_shear_V_kN, 0.25 * base_shear_V_kN)
        else:
            Ft_kN = 0.0

        V_minus_Ft = base_shear_V_kN - Ft_kN

        # Triangular distribution of (V - Ft)
        w_h = [s.weight_kN * s.height_from_base_m for s in stories]
        sum_w_h = sum(w_h) if sum(w_h) > 0 else 1.0

        Fx_kN = [(wh / sum_w_h) * V_minus_Ft for wh in w_h]
        # Add Ft to top level
        Fx_kN[-1] += Ft_kN

        # Story Shears and Overturning
        Vx_kN = [0.0] * n
        Mx_kNm = [0.0] * n
        for i in range(n):
            Vx_kN[i] = sum(Fx_kN[j] for j in range(i, n))
            hx = stories[i].height_from_base_m
            Mx_kNm[i] = sum(Fx_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))

        base_overturning_M0_kNm = sum(Fx_kN[i] * stories[i].height_from_base_m for i in range(n))

        # 5. Inelastic Story Drift Delta_M = 0.70 * R * Delta_S (Section 1630.10)
        # Allowable drift: 0.025 * hsx for T < 0.7s, 0.020 * hsx for T >= 0.7s
        allowable_ratio = 0.020 if T >= 0.70 else 0.025

        story_results: List[StorySeismicResult] = []
        cum_delta_s = 0.0
        max_drift_ratio = 0.0
        max_drift_story = ""
        max_theta = 0.0
        overall_status = DesignStatus.PASS

        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)

            # Elastic story drift Delta_S
            inter_delta_s = Vx_kN[i] / k_story
            cum_delta_s += inter_delta_s

            # Inelastic design story drift Delta_M = 0.70 * R * Delta_S
            inter_delta_M = 0.70 * R * inter_delta_s
            cum_delta_M = 0.70 * R * cum_delta_s

            drift_ratio = inter_delta_M / hsx_mm if hsx_mm > 0 else 0.0
            if drift_ratio > max_drift_ratio:
                max_drift_ratio = drift_ratio
                max_drift_story = story.name

            # P-Delta check theta
            Ptot_kN = sum(stories[j].weight_kN for j in range(i, n))
            denom = Vx_kN[i] * hsx_mm
            theta = (Ptot_kN * inter_delta_M) / denom if denom > 0 else 0.0
            if theta > max_theta:
                max_theta = theta

            is_pass = drift_ratio <= allowable_ratio
            if not is_pass:
                overall_status = DesignStatus.FAIL

            story_results.append(
                StorySeismicResult(
                    level_index=story.level_index,
                    name=story.name,
                    height_from_base_m=story.height_from_base_m,
                    story_height_m=story.story_height_m,
                    weight_kN=story.weight_kN,
                    Cvx_distribution_factor=(w_h[i] / sum_w_h),
                    story_force_Fx_kN=Fx_kN[i],
                    story_shear_Vx_kN=Vx_kN[i],
                    story_overturning_Mx_kNm=Mx_kNm[i],
                    elastic_displacement_dxe_mm=cum_delta_s,
                    design_displacement_dx_mm=cum_delta_M,
                    story_drift_delta_mm=inter_delta_M,
                    allowable_drift_delta_a_mm=allowable_ratio * hsx_mm,
                    drift_ratio=drift_ratio,
                    allowable_drift_ratio=allowable_ratio,
                    stability_coefficient_theta=theta,
                    drift_status=DesignStatus.PASS if is_pass else DesignStatus.FAIL
                )
            )

        inputs = {
            "Z_factor": Z,
            "soil_profile": params.soil_profile_ubc.value,
            "R": R,
            "I": I,
            "Na": params.Na_ubc,
            "Nv": params.Nv_ubc,
            "total_weight_W_kN": round(total_weight_W, 1)
        }
        intermediate = {
            "Ca": round(Ca, 3),
            "Cv": round(Cv, 3),
            "period_T_s": round(T, 3),
            "Ft_kN": round(Ft_kN, 2),
            "base_shear_ratio": round(v_ratio, 5),
            "governing_equation": governing_formula,
            "base_shear_V_kN": round(base_shear_V_kN, 2),
            "base_overturning_M0_kNm": round(base_overturning_M0_kNm, 2),
            "max_inelastic_drift_ratio": round(max_drift_ratio, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.UBC.value,
            code_edition=CodeEdition.UBC_1997.value,
            clause="UBC 1997 Section 1630 (Eqs. 30-4, 30-5, 30-6, 30-7, 30-15, 30-17)",
            inputs=inputs,
            method="UBC 1997 Static Base Shear V and Inelastic Drift Delta_M = 0.70*R*Delta_S",
            intermediate_results=intermediate,
            final_result=f"Base Shear V = {round(base_shear_V_kN, 2)} kN ({governing_formula}), Base Overturning = {round(base_overturning_M0_kNm, 2)} kN*m",
            limit=f"Delta_M <= {allowable_ratio}*hsx",
            status=overall_status
        )

        analysis_res = SeismicAnalysisResult(
            code=LateralCode.UBC,
            edition=CodeEdition.UBC_1997,
            parameters=params,
            fundamental_period_T_s=T,
            period_upper_limit_T_max_s=T * 1.3,
            governing_period_s=T,
            total_effective_weight_W_kN=total_weight_W,
            seismic_response_coeff_Cs=v_ratio,
            Cs_governing_formula=governing_formula,
            base_shear_V_kN=base_shear_V_kN,
            base_overturning_moment_M0_kNm=base_overturning_M0_kNm,
            story_results=story_results,
            max_drift_ratio=max_drift_ratio,
            max_drift_story=max_drift_story,
            max_stability_coefficient_theta=max_theta,
            overall_drift_status=overall_status,
            trace=trace
        )

        return analysis_res, trace

    # -------------------------------------------------------------------------
    # UBC 1997 WIND (Section 1615 - 1625)
    # -------------------------------------------------------------------------

    @staticmethod
    def calculate_wind_analysis(
        stories: List[StoryLevel],
        params: WindParameters,
    ) -> WindAnalysisResult:
        """
        Executes UBC 1997 Division III Wind Design (Section 1618 Eq. 18-1):
        P = Ce * Cq * qs * Iw
        Generates:
        - Story Wind Forces (Fw)
        - Story Shear (Vw)
        - Base Shear
        - Overturning
        - Drift
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m

        # Stagnation pressure qs per Table 16-F
        qs = params.qs_ubc_N_per_m2
        Cq = params.Cq_ubc
        Iw = params.importance_factor_Iw

        story_results: List[StoryWindResult] = []
        Fw_kN = [0.0] * n
        Vw_kN = [0.0] * n
        Mw_kNm = [0.0] * n

        for i in range(n):
            story = stories[i]
            z = story.height_from_base_m

            # Combined height, exposure and gust factor Ce (Table 16-G)
            # Interpolation function for Ce in Exposure C:
            # 0-4.5m: 1.06, 9m: 1.19, 18m: 1.34, 30m: 1.47, 48m: 1.61, 60m: 1.68
            Ce = 1.06 * ((max(z, 4.5) / 4.5) ** (2.0 / 9.5))

            # Tributary area
            h_below = story.story_height_m
            h_above = (stories[i + 1].height_from_base_m - z) if i < n - 1 else (story.story_height_m * 0.5)
            h_trib = (h_below * 0.5) + (h_above * 0.5) if i < n - 1 else (h_below * 0.5)
            if i == 0:
                h_trib = story.story_height_m * 0.5 + (stories[1].height_from_base_m - z) * 0.5 if n > 1 else story.story_height_m

            trib_area_m2 = story.width_m * h_trib

            # Design wind pressure P = Ce * Cq * qs * Iw (N/m2)
            P_design_N_m2 = Ce * Cq * qs * Iw
            force_kN = (P_design_N_m2 * trib_area_m2) / 1000.0
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
                    Kz_exposure_coeff=Ce,
                    velocity_pressure_qz_N_m2=qs,
                    windward_pressure_p_N_m2=P_design_N_m2 * 0.6,
                    leeward_pressure_p_N_m2=P_design_N_m2 * 0.4,
                    net_design_pressure_N_m2=P_design_N_m2,
                    story_wind_force_Fw_kN=force_kN,
                    story_wind_shear_Vw_kN=0.0,
                    story_overturning_Mw_kNm=0.0,
                    lateral_displacement_mm=0.0,
                    story_drift_mm=0.0,
                    drift_ratio=0.0,
                    allowable_drift_ratio=0.0025,
                    drift_status=DesignStatus.PASS
                )
            )

        for i in range(n):
            Vw_kN[i] = sum(Fw_kN[j] for j in range(i, n))
            hx = stories[i].height_from_base_m
            Mw_kNm[i] = sum(Fw_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))
            story_results[i].story_wind_shear_Vw_kN = Vw_kN[i]
            story_results[i].story_overturning_Mw_kNm = Mw_kNm[i]

        base_shear_Vw_kN = sum(Fw_kN)
        base_overturning_Mw0_kNm = sum(Fw_kN[i] * stories[i].height_from_base_m for i in range(n))

        # Drift
        allowable_drift_ratio = 0.0025
        cum_disp_mm = 0.0
        max_drift_ratio = 0.0
        max_drift_story = ""
        overall_status = DesignStatus.PASS

        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)

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
            "qs_stagnation_pressure_N_m2": qs,
            "Cq_coefficient": Cq,
            "Iw_importance": Iw,
            "total_height_m": total_height_m
        }
        intermediate = {
            "base_shear_Vw_kN": round(base_shear_Vw_kN, 2),
            "base_overturning_Mw0_kNm": round(base_overturning_Mw0_kNm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.UBC.value,
            code_edition=CodeEdition.UBC_1997.value,
            clause="UBC 1997 Section 1618 (Eq. 18-1: P = Ce * Cq * qs * Iw)",
            inputs=inputs,
            method="UBC 1997 Wind Design Pressure P and Story Forces Fw",
            intermediate_results=intermediate,
            final_result=f"Wind Base Shear = {round(base_shear_Vw_kN, 2)} kN, Base Overturning = {round(base_overturning_Mw0_kNm, 2)} kN*m",
            limit="Wind Drift Ratio <= 0.0025 (H/400)",
            status=overall_status
        )

        return WindAnalysisResult(
            code=LateralCode.UBC,
            edition=CodeEdition.UBC_1997,
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
