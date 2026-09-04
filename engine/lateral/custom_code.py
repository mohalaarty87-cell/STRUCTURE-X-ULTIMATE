"""
STRUCTURE-X ULTIMATE — CUSTOM CODE FRAMEWORK
Modular framework allowing structural engineers to define custom seismic hazard curves,
arbitrary response spectra, user-defined vertical distribution exponents,
and customized wind profiles with full engineering audit traceability.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Callable

from .types import (
    LateralCode,
    CodeEdition,
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


class CustomCodeEngine:
    """
    Custom Code Framework for site-specific seismic hazard assessment and non-standard wind regimes.
    """

    @staticmethod
    def evaluate_custom_spectrum(
        T_s: float,
        spectral_points: Optional[List[Tuple[float, float]]] = None,
        PGA: float = 0.30,
        Ss: float = 0.75,
        S1: float = 0.35,
        R_custom: float = 5.0,
        I_custom: float = 1.0,
    ) -> float:
        """
        Evaluates spectral acceleration Sa(T) from either discrete (T, Sa) points via linear interpolation,
        or a parametric 3-branch spectrum.
        """
        if spectral_points and len(spectral_points) > 1:
            # Sort by period T
            sorted_pts = sorted(spectral_points, key=lambda p: p[0])
            if T_s <= sorted_pts[0][0]:
                return sorted_pts[0][1] / (R_custom / I_custom)
            if T_s >= sorted_pts[-1][0]:
                return sorted_pts[-1][1] / (R_custom / I_custom)
            for i in range(len(sorted_pts) - 1):
                t1, sa1 = sorted_pts[i]
                t2, sa2 = sorted_pts[i + 1]
                if t1 <= T_s <= t2:
                    slope = (sa2 - sa1) / (t2 - t1) if (t2 - t1) > 0 else 0
                    sa_elastic = sa1 + slope * (T_s - t1)
                    return sa_elastic / (R_custom / I_custom)

        # Default parametric spectrum
        Ts = S1 / max(Ss, 0.01)
        T0 = 0.2 * Ts
        if T_s <= T0:
            sa = PGA + (Ss - PGA) * (T_s / max(T0, 0.01))
        elif T_s <= Ts:
            sa = Ss
        else:
            sa = S1 / max(T_s, 0.01)

        return sa / (R_custom / I_custom)

    @staticmethod
    def calculate_custom_seismic_analysis(
        stories: List[StoryLevel],
        params: SeismicParameters,
        custom_code_name: str = "Client Project Specific Criteria",
        custom_clause: str = "Section 4.1 Site-Specific PSHA",
        spectral_points: Optional[List[Tuple[float, float]]] = None,
        custom_k_exponent: Optional[float] = None,
        target_drift_limit: float = 0.015,
    ) -> SeismicAnalysisResult:
        """
        Executes Seismic Analysis using the Custom Code Framework:
        1. Evaluates Sa from custom spectrum
        2. Calculates base shear V = Sa * W
        3. Distributes lateral forces Fx per custom exponent k
        4. Calculates story shears, overturning, and drift
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m
        total_weight_W = sum(s.weight_kN for s in stories)

        # Approximate period
        T_s = 0.05 * (total_height_m ** 0.8)

        # Custom spectral acceleration
        Cs_custom = CustomCodeEngine.evaluate_custom_spectrum(
            T_s=T_s,
            spectral_points=spectral_points,
            PGA=params.ag_design,
            Ss=params.Ss,
            S1=params.S1,
            R_custom=params.R,
            I_custom=params.importance_factor
        )

        base_shear_V_kN = Cs_custom * total_weight_W

        # Vertical distribution exponent k
        if custom_k_exponent is not None:
            k = custom_k_exponent
        else:
            k = 1.0 if T_s <= 0.5 else (2.0 if T_s >= 2.5 else 1.0 + (T_s - 0.5) * 0.5)

        w_h_k = [story.weight_kN * (story.height_from_base_m ** k) for story in stories]
        denom = sum(w_h_k) if sum(w_h_k) > 0 else 1.0
        Cvx = [val / denom for val in w_h_k]
        Fx_kN = [c * base_shear_V_kN for c in Cvx]

        Vx_kN = [0.0] * n
        Mx_kNm = [0.0] * n
        for i in range(n):
            Vx_kN[i] = sum(Fx_kN[j] for j in range(i, n))
            hx = stories[i].height_from_base_m
            Mx_kNm[i] = sum(Fx_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))

        base_overturning_M0_kNm = sum(Fx_kN[i] * stories[i].height_from_base_m for i in range(n))

        # Drift and stability
        story_results: List[StorySeismicResult] = []
        cum_dxe = 0.0
        max_drift_ratio = 0.0
        max_drift_story = ""
        max_theta = 0.0
        overall_status = DesignStatus.PASS

        Cd = params.Cd
        Ie = params.importance_factor

        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)

            inter_dxe = Vx_kN[i] / k_story
            cum_dxe += inter_dxe
            dx_mm = (Cd * cum_dxe) / max(Ie, 0.1)

            prev_dx = (Cd * (cum_dxe - inter_dxe)) / max(Ie, 0.1) if i > 0 else 0.0
            delta_mm = dx_mm - prev_dx

            drift_ratio = delta_mm / hsx_mm if hsx_mm > 0 else 0.0
            if drift_ratio > max_drift_ratio:
                max_drift_ratio = drift_ratio
                max_drift_story = story.name

            Px_kN = sum(stories[j].weight_kN for j in range(i, n))
            denom_theta = Vx_kN[i] * hsx_mm * Cd
            theta = (Px_kN * delta_mm * Ie) / denom_theta if denom_theta > 0 else 0.0
            if theta > max_theta:
                max_theta = theta

            is_pass = (drift_ratio <= target_drift_limit) and (theta <= 0.25)
            if not is_pass:
                overall_status = DesignStatus.FAIL

            story_results.append(
                StorySeismicResult(
                    level_index=story.level_index,
                    name=story.name,
                    height_from_base_m=story.height_from_base_m,
                    story_height_m=story.story_height_m,
                    weight_kN=story.weight_kN,
                    Cvx_distribution_factor=Cvx[i],
                    story_force_Fx_kN=Fx_kN[i],
                    story_shear_Vx_kN=Vx_kN[i],
                    story_overturning_Mx_kNm=Mx_kNm[i],
                    elastic_displacement_dxe_mm=cum_dxe,
                    design_displacement_dx_mm=dx_mm,
                    story_drift_delta_mm=delta_mm,
                    allowable_drift_delta_a_mm=target_drift_limit * hsx_mm,
                    drift_ratio=drift_ratio,
                    allowable_drift_ratio=target_drift_limit,
                    stability_coefficient_theta=theta,
                    drift_status=DesignStatus.PASS if is_pass else DesignStatus.FAIL
                )
            )

        inputs = {
            "custom_code_name": custom_code_name,
            "period_T_s": round(T_s, 3),
            "R": params.R,
            "I": params.importance_factor,
            "distribution_exponent_k": round(k, 3),
            "target_drift_limit": target_drift_limit,
            "total_weight_W_kN": round(total_weight_W, 1)
        }
        intermediate = {
            "Cs_spectral_coefficient": round(Cs_custom, 5),
            "base_shear_V_kN": round(base_shear_V_kN, 2),
            "base_overturning_M0_kNm": round(base_overturning_M0_kNm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5),
            "max_theta": round(max_theta, 4)
        }

        trace = CalculationTrace(
            design_code=LateralCode.CUSTOM.value,
            code_edition=CodeEdition.CUSTOM_EDITION.value,
            clause=custom_clause,
            inputs=inputs,
            method="Custom Code Spectrum Evaluation & Exponent-Weighted Lateral Force Distribution",
            intermediate_results=intermediate,
            final_result=f"Base Shear V = {round(base_shear_V_kN, 2)} kN, Base Overturning M0 = {round(base_overturning_M0_kNm, 2)} kN*m",
            limit=f"Drift Ratio <= {target_drift_limit}",
            status=overall_status
        )

        return SeismicAnalysisResult(
            code=LateralCode.CUSTOM,
            edition=CodeEdition.CUSTOM_EDITION,
            parameters=params,
            fundamental_period_T_s=T_s,
            period_upper_limit_T_max_s=T_s * 1.4,
            governing_period_s=T_s,
            total_effective_weight_W_kN=total_weight_W,
            seismic_response_coeff_Cs=Cs_custom,
            Cs_governing_formula="Custom Response Spectrum Function",
            base_shear_V_kN=base_shear_V_kN,
            base_overturning_moment_M0_kNm=base_overturning_M0_kNm,
            story_results=story_results,
            max_drift_ratio=max_drift_ratio,
            max_drift_story=max_drift_story,
            max_stability_coefficient_theta=max_theta,
            overall_drift_status=overall_status,
            trace=trace
        )

    @staticmethod
    def calculate_custom_wind_analysis(
        stories: List[StoryLevel],
        params: WindParameters,
        custom_code_name: str = "Client Project Specific Wind Criteria",
        custom_clause: str = "Section 5.2 Boundary Layer Wind Tunnel / CFD Synthesis",
        wind_pressure_function: Optional[Callable[[float], float]] = None,
        allowable_drift_ratio: float = 0.0020,
    ) -> WindAnalysisResult:
        """
        Executes Wind Analysis using the Custom Code Framework:
        Allows custom height-dependent wind pressure function p(z) or boundary layer profile.
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m

        story_results: List[StoryWindResult] = []
        Fw_kN = [0.0] * n
        Vw_kN = [0.0] * n
        Mw_kNm = [0.0] * n

        for i in range(n):
            story = stories[i]
            z = story.height_from_base_m

            h_below = story.story_height_m
            h_above = (stories[i + 1].height_from_base_m - z) if i < n - 1 else (story.story_height_m * 0.5)
            h_trib = (h_below * 0.5) + (h_above * 0.5) if i < n - 1 else (h_below * 0.5)
            if i == 0:
                h_trib = story.story_height_m * 0.5 + (stories[1].height_from_base_m - z) * 0.5 if n > 1 else story.story_height_m

            trib_area_m2 = story.width_m * h_trib

            if wind_pressure_function is not None:
                p_net = wind_pressure_function(z)
            else:
                # Default power law profile
                qz_ref = 0.5 * 1.225 * (params.basic_wind_speed_mps ** 2)
                p_net = qz_ref * 1.3 * ((max(z, 5.0) / 10.0) ** 0.28)

            force_kN = (p_net * trib_area_m2) / 1000.0
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
                    Kz_exposure_coeff=1.0,
                    velocity_pressure_qz_N_m2=p_net / 1.3,
                    windward_pressure_p_N_m2=p_net * 0.65,
                    leeward_pressure_p_N_m2=p_net * 0.35,
                    net_design_pressure_N_m2=p_net,
                    story_wind_force_Fw_kN=force_kN,
                    story_wind_shear_Vw_kN=0.0,
                    story_overturning_Mw_kNm=0.0,
                    lateral_displacement_mm=0.0,
                    story_drift_mm=0.0,
                    drift_ratio=0.0,
                    allowable_drift_ratio=allowable_drift_ratio,
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
            "custom_code_name": custom_code_name,
            "basic_wind_speed_mps": params.basic_wind_speed_mps,
            "allowable_drift_ratio": allowable_drift_ratio,
            "total_height_m": total_height_m
        }
        intermediate = {
            "base_shear_Vw_kN": round(base_shear_Vw_kN, 2),
            "base_overturning_Mw0_kNm": round(base_overturning_Mw0_kNm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.CUSTOM.value,
            code_edition=CodeEdition.CUSTOM_EDITION.value,
            clause=custom_clause,
            inputs=inputs,
            method="Custom Wind Pressure Profile Analysis and Story Shear / Drift Evaluation",
            intermediate_results=intermediate,
            final_result=f"Wind Base Shear = {round(base_shear_Vw_kN, 2)} kN, Base Overturning = {round(base_overturning_Mw0_kNm, 2)} kN*m",
            limit=f"Drift Ratio <= {allowable_drift_ratio}",
            status=overall_status
        )

        return WindAnalysisResult(
            code=LateralCode.CUSTOM,
            edition=CodeEdition.CUSTOM_EDITION,
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
