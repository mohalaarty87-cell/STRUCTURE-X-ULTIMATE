"""
STRUCTURE-X ULTIMATE — MASTER LATERAL ENGINE (SEISMIC & WIND)
Unified interface for multi-code lateral force analysis supporting ASCE 7, IBC,
Eurocode 8, UBC 1997, and the Custom Code Framework.
"""

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
    LateralComparisonResult,
)
from .asce7 import ASCE7Engine
from .ibc import IBCEngine
from .eurocode8 import Eurocode8Engine
from .ubc import UBCEngine
from .custom_code import CustomCodeEngine


class LateralEngine:
    """
    Master Seismic and Wind Engineering analysis engine for Phase 12.
    """

    @staticmethod
    def generate_uniform_building(
        num_stories: int,
        story_height_m: float = 3.5,
        weight_per_story_kN: float = 3500.0,
        width_m: float = 30.0,
        depth_m: float = 24.0,
        stiffness_kN_per_mm: float = 60.0,
        roof_weight_kN: Optional[float] = None,
    ) -> List[StoryLevel]:
        """
        Convenience generator for standard regular multi-story structures.
        """
        stories: List[StoryLevel] = []
        for i in range(1, num_stories + 1):
            is_roof = (i == num_stories)
            w = (roof_weight_kN if (is_roof and roof_weight_kN is not None) else weight_per_story_kN)
            h_from_base = i * story_height_m
            name = f"Level {i}" if not is_roof else f"Level {i} (Roof)"

            stories.append(
                StoryLevel(
                    level_index=i,
                    name=name,
                    height_from_base_m=h_from_base,
                    story_height_m=story_height_m,
                    weight_kN=w,
                    width_m=width_m,
                    depth_m=depth_m,
                    lateral_stiffness_kN_per_mm=stiffness_kN_per_mm
                )
            )
        return stories

    @staticmethod
    def calculate_seismic(
        stories: List[StoryLevel],
        params: SeismicParameters,
        code: LateralCode = LateralCode.ASCE_7,
        edition: Optional[CodeEdition] = None,
        system_type: str = "STEEL_MOMENT_FRAME",
        custom_code_name: str = "Custom Code",
        custom_clause: str = "Section 1.0",
        custom_spectral_points: Optional[List[Tuple[float, float]]] = None,
    ) -> SeismicAnalysisResult:
        """
        Executes seismic analysis adhering strictly to the requested international standard.
        """
        if code == LateralCode.ASCE_7:
            ed = edition or CodeEdition.ASCE_7_16
            # 1. Site coefficients & spectral params
            Fa, Fv, _ = ASCE7Engine.get_site_coefficients(params.site_class, params.Ss, params.S1, ed)
            SMS, SM1, SDS, SD1, Ts, T0, _ = ASCE7Engine.calculate_design_spectral_parameters(
                params.Ss, params.S1, Fa, Fv, ed
            )
            params.Fa = Fa
            params.Fv = Fv
            params.SMS = SMS
            params.SM1 = SM1
            params.SDS = SDS
            params.SD1 = SD1

            # SDC
            sdc, _ = ASCE7Engine.determine_seismic_design_category(SDS, SD1, params.S1, params.risk_category, ed)
            params.sdc = sdc

            # Period
            hn = stories[-1].height_from_base_m
            Ta, _ = ASCE7Engine.calculate_approximate_period(hn, system_type, ed)
            Cu, T_max, _ = ASCE7Engine.calculate_period_upper_limit(Ta, SD1, ed)
            governing_T = min(Ta, T_max)

            # Cs
            Cs, cs_formula, _ = ASCE7Engine.calculate_seismic_response_coefficient_cs(
                SDS, SD1, params.S1, governing_T, params.R, params.importance_factor, params.TL, ed
            )

            # Base Shear V
            W = sum(s.weight_kN for s in stories)
            V = Cs * W

            # Vertical distribution
            Cvx, Fx, Vx, M0, _ = ASCE7Engine.calculate_seismic_vertical_distribution(V, stories, governing_T, ed)

            # Drifts and stability
            story_res, max_drift, max_story, max_theta, status, trace = ASCE7Engine.calculate_seismic_drifts_and_stability(
                stories, Fx, Vx, params.Cd, params.importance_factor, params.risk_category, edition=ed
            )

            # Set Cvx & Overturning
            n = len(stories)
            for i in range(n):
                story_res[i].Cvx_distribution_factor = Cvx[i]
                hx = stories[i].height_from_base_m
                story_res[i].story_overturning_Mx_kNm = sum(Fx[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))

            return SeismicAnalysisResult(
                code=code,
                edition=ed,
                parameters=params,
                fundamental_period_T_s=Ta,
                period_upper_limit_T_max_s=T_max,
                governing_period_s=governing_T,
                total_effective_weight_W_kN=W,
                seismic_response_coeff_Cs=Cs,
                Cs_governing_formula=cs_formula,
                base_shear_V_kN=V,
                base_overturning_moment_M0_kNm=M0,
                story_results=story_res,
                max_drift_ratio=max_drift,
                max_drift_story=max_story,
                max_stability_coefficient_theta=max_theta,
                overall_drift_status=status,
                trace=trace
            )

        elif code == LateralCode.IBC:
            ed = edition or CodeEdition.IBC_2024
            res, _, _ = IBCEngine.calculate_seismic_effects(stories, params, ed)
            return res

        elif code == LateralCode.EUROCODE_8:
            ed = edition or CodeEdition.EN_1998_1_2004
            return Eurocode8Engine.calculate_seismic_analysis(stories, params, system_type, ed)

        elif code == LateralCode.UBC:
            res, _ = UBCEngine.calculate_base_shear_and_distribution(stories, params, system_type)
            return res

        elif code == LateralCode.CUSTOM:
            return CustomCodeEngine.calculate_custom_seismic_analysis(
                stories=stories,
                params=params,
                custom_code_name=custom_code_name,
                custom_clause=custom_clause,
                spectral_points=custom_spectral_points
            )

        else:
            raise ValueError(f"Unsupported lateral code: {code}")

    @staticmethod
    def calculate_wind(
        stories: List[StoryLevel],
        params: WindParameters,
        code: LateralCode = LateralCode.ASCE_7,
        edition: Optional[CodeEdition] = None,
        custom_code_name: str = "Custom Wind Code",
        custom_clause: str = "Section 2.0",
    ) -> WindAnalysisResult:
        """
        Executes wind analysis adhering strictly to the requested international standard.
        """
        if code == LateralCode.ASCE_7:
            ed = edition or CodeEdition.ASCE_7_16
            return ASCE7Engine.calculate_wind_forces_and_drift(stories, params, ed)

        elif code == LateralCode.IBC:
            ed = edition or CodeEdition.IBC_2024
            return IBCEngine.calculate_wind_effects(stories, params, ed)

        elif code == LateralCode.EUROCODE_8:
            ed = edition or CodeEdition.EN_1991_1_4_2005
            return Eurocode8Engine.calculate_wind_analysis(stories, params, ed)

        elif code == LateralCode.UBC:
            return UBCEngine.calculate_wind_analysis(stories, params)

        elif code == LateralCode.CUSTOM:
            return CustomCodeEngine.calculate_custom_wind_analysis(
                stories=stories,
                params=params,
                custom_code_name=custom_code_name,
                custom_clause=custom_clause
            )

        else:
            raise ValueError(f"Unsupported lateral code: {code}")

    @staticmethod
    def compare_seismic_and_wind(
        seismic_res: SeismicAnalysisResult,
        wind_res: WindAnalysisResult,
    ) -> LateralComparisonResult:
        """
        Envelopes and directly compares Seismic vs. Wind demands across every story level:
        - Base Shear comparison & governing load identification
        - Overturning Moment comparison & governing load identification
        - Drift comparison & governing load identification
        - Story-by-story force and shear envelope table
        """
        gov_base_shear = "SEISMIC" if seismic_res.base_shear_V_kN >= wind_res.base_shear_Vw_kN else "WIND"
        gov_base_shear_val = max(seismic_res.base_shear_V_kN, wind_res.base_shear_Vw_kN)
        ratio_base_shear = seismic_res.base_shear_V_kN / max(wind_res.base_shear_Vw_kN, 0.001)

        gov_overturning = "SEISMIC" if seismic_res.base_overturning_moment_M0_kNm >= wind_res.base_overturning_moment_Mw0_kNm else "WIND"
        gov_overturning_val = max(seismic_res.base_overturning_moment_M0_kNm, wind_res.base_overturning_moment_Mw0_kNm)

        gov_drift = "SEISMIC" if seismic_res.max_drift_ratio >= wind_res.max_drift_ratio else "WIND"

        level_comparisons: List[Dict[str, Any]] = []
        n = min(len(seismic_res.story_results), len(wind_res.story_results))

        for i in range(n):
            s_story = seismic_res.story_results[i]
            w_story = wind_res.story_results[i]

            gov_force = "SEISMIC" if s_story.story_force_Fx_kN >= w_story.story_wind_force_Fw_kN else "WIND"
            gov_shear = "SEISMIC" if s_story.story_shear_Vx_kN >= w_story.story_wind_shear_Vw_kN else "WIND"
            gov_drift_level = "SEISMIC" if s_story.drift_ratio >= w_story.drift_ratio else "WIND"

            level_comparisons.append({
                "level_index": s_story.level_index,
                "name": s_story.name,
                "height_m": s_story.height_from_base_m,
                "seismic_force_Fx_kN": round(s_story.story_force_Fx_kN, 2),
                "wind_force_Fw_kN": round(w_story.story_wind_force_Fw_kN, 2),
                "governing_force": gov_force,
                "governing_force_value_kN": round(max(s_story.story_force_Fx_kN, w_story.story_wind_force_Fw_kN), 2),
                "seismic_shear_Vx_kN": round(s_story.story_shear_Vx_kN, 2),
                "wind_shear_Vw_kN": round(w_story.story_wind_shear_Vw_kN, 2),
                "governing_shear": gov_shear,
                "governing_shear_value_kN": round(max(s_story.story_shear_Vx_kN, w_story.story_wind_shear_Vw_kN), 2),
                "seismic_drift_ratio": round(s_story.drift_ratio, 5),
                "wind_drift_ratio": round(w_story.drift_ratio, 5),
                "governing_drift": gov_drift_level
            })

        return LateralComparisonResult(
            governing_base_shear=gov_base_shear,
            governing_base_shear_value_kN=gov_base_shear_val,
            seismic_base_shear_kN=seismic_res.base_shear_V_kN,
            wind_base_shear_kN=wind_res.base_shear_Vw_kN,
            ratio_seismic_to_wind_base_shear=ratio_base_shear,
            governing_overturning=gov_overturning,
            governing_overturning_value_kNm=gov_overturning_val,
            seismic_overturning_kNm=seismic_res.base_overturning_moment_M0_kNm,
            wind_overturning_kNm=wind_res.base_overturning_moment_Mw0_kNm,
            governing_drift=gov_drift,
            seismic_max_drift_ratio=seismic_res.max_drift_ratio,
            wind_max_drift_ratio=wind_res.max_drift_ratio,
            level_comparisons=level_comparisons
        )
