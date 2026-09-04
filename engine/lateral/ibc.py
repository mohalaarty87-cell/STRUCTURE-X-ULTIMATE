"""
STRUCTURE-X ULTIMATE — IBC SEISMIC & WIND ENGINE
Implementation strictly complying with International Building Code (IBC 2024, 2021, and 2018)
Chapter 16: Structural Design (Sections 1604, 1605, 1609, 1613).
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
from .asce7 import ASCE7Engine


class IBCEngine:
    """
    IBC 2024 / 2021 / 2018 Seismic and Wind analysis engine.
    Applies IBC Chapter 16 specific provisions, risk categorization,
    vertical seismic component Ev = 0.2*SDS*D, overstrength Em = Omega0*QE,
    and ultimate/nominal wind conversions.
    """

    @staticmethod
    def calculate_seismic_effects(
        stories: List[StoryLevel],
        params: SeismicParameters,
        edition: CodeEdition = CodeEdition.IBC_2024,
        redundancy_factor_rho: float = 1.0,
    ) -> Tuple[SeismicAnalysisResult, Dict[str, Any], CalculationTrace]:
        """
        Executes IBC Section 1613 Seismic Design:
        1. Evaluates Fa, Fv, SMS, SM1, SDS, SD1 per IBC Section 1613.2 / ASCE 7
        2. Evaluates approximate period Ta and upper limit Cu * Ta
        3. Computes seismic response coefficient Cs
        4. Calculates base shear V, vertical distribution Fx, story shear Vx, overturning Mx
        5. Computes vertical seismic component Ev = 0.2 * SDS * W (IBC Eq. 16-13 / Section 1605.1)
        6. Computes overstrength design load Em = Omega0 * QE (IBC Section 1613 / Section 1605.1.1)
        7. Evaluates design drifts delta and P-Delta stability theta
        """
        # 1. Site Coefficients and Spectral Accelerations
        Fa, Fv, _ = ASCE7Engine.get_site_coefficients(params.site_class, params.Ss, params.S1)
        SMS, SM1, SDS, SD1, Ts, T0, _ = ASCE7Engine.calculate_design_spectral_parameters(
            params.Ss, params.S1, Fa, Fv
        )

        params.Fa = Fa
        params.Fv = Fv
        params.SMS = SMS
        params.SM1 = SM1
        params.SDS = SDS
        params.SD1 = SD1

        # SDC per IBC Section 1613.2.5
        sdc, _ = ASCE7Engine.determine_seismic_design_category(
            SDS, SD1, params.S1, params.risk_category
        )
        params.sdc = sdc

        # 2. Fundamental Period
        total_height_m = stories[-1].height_from_base_m
        Ta, _ = ASCE7Engine.calculate_approximate_period(total_height_m)
        Cu, T_max, _ = ASCE7Engine.calculate_period_upper_limit(Ta, SD1)
        governing_T = min(Ta, T_max)

        # 3. Seismic Response Coefficient Cs
        Cs, cs_formula, _ = ASCE7Engine.calculate_seismic_response_coefficient_cs(
            SDS=SDS,
            SD1=SD1,
            S1=params.S1,
            T_s=governing_T,
            R=params.R,
            Ie=params.importance_factor,
            TL_s=params.TL
        )

        # 4. Total Seismic Weight & Base Shear
        total_weight_W = sum(s.weight_kN for s in stories)
        base_shear_V = Cs * total_weight_W

        # 5. Vertical Distribution & Overturning
        Cvx, Fx_kN, Vx_kN, M0_kNm, _ = ASCE7Engine.calculate_seismic_vertical_distribution(
            base_shear_V_kN=base_shear_V,
            stories=stories,
            T_s=governing_T
        )

        # 6. Story Drifts & P-Delta Stability
        story_results, max_drift_ratio, max_drift_story, max_theta, overall_drift_status, _ = (
            ASCE7Engine.calculate_seismic_drifts_and_stability(
                stories=stories,
                Fx_kN=Fx_kN,
                Vx_kN=Vx_kN,
                Cd=params.Cd,
                Ie=params.importance_factor,
                risk_category=params.risk_category
            )
        )

        # Update Cvx and Overturning Moments in story results
        n = len(stories)
        for i in range(n):
            story_results[i].Cvx_distribution_factor = Cvx[i]
            hx = stories[i].height_from_base_m
            story_results[i].story_overturning_Mx_kNm = sum(
                Fx_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n)
            )

        # 7. IBC Specific Seismic Load Combinations:
        # Vertical component Ev = 0.2 * SDS * D
        # Horizontal seismic load Eh = rho * QE = rho * Fx
        # Maximum seismic force with overstrength: Em = Omega0 * QE
        Ev_factor = 0.20 * SDS
        Ev_kN = [Ev_factor * story.weight_kN for story in stories]
        Em_base_shear_kN = params.Omega0 * base_shear_V

        ibc_load_effects = {
            "redundancy_factor_rho": redundancy_factor_rho,
            "Ev_vertical_factor": round(Ev_factor, 4),
            "Ev_total_kN": round(sum(Ev_kN), 2),
            "Omega0_overstrength": params.Omega0,
            "Em_overstrength_base_shear_kN": round(Em_base_shear_kN, 2),
            "LRFD_comb_1_2D_1_0E": f"1.2D + {round(Ev_factor, 3)}D + {redundancy_factor_rho}Eh",
            "LRFD_comb_0_9D_1_0E": f"0.9D - {round(Ev_factor, 3)}D + {redundancy_factor_rho}Eh"
        }

        clause_ref = "IBC 2024 Section 1613 & Section 1605 (ASCE 7-22 Chapters 11 & 12)"
        if edition == CodeEdition.IBC_2021:
            clause_ref = "IBC 2021 Section 1613 & Section 1605 (ASCE 7-16 Chapters 11 & 12)"
        elif edition == CodeEdition.IBC_2018:
            clause_ref = "IBC 2018 Section 1613 & Section 1605 (ASCE 7-16 Chapters 11 & 12)"

        inputs = {
            "Ss": params.Ss,
            "S1": params.S1,
            "site_class": params.site_class.value,
            "R": params.R,
            "importance_factor_Ie": params.importance_factor,
            "Cd": params.Cd,
            "Omega0": params.Omega0,
            "risk_category": params.risk_category.value,
            "total_building_weight_W_kN": round(total_weight_W, 1)
        }
        intermediate = {
            "Fa": round(Fa, 3),
            "Fv": round(Fv, 3),
            "SDS": round(SDS, 3),
            "SD1": round(SD1, 3),
            "SDC": sdc.value,
            "period_Ta_s": round(Ta, 3),
            "period_T_governing_s": round(governing_T, 3),
            "Cs": round(Cs, 5),
            "Cs_governing_equation": cs_formula,
            "base_shear_V_kN": round(base_shear_V, 2),
            "base_overturning_M0_kNm": round(M0_kNm, 2),
            "Ev_total_kN": round(sum(Ev_kN), 2),
            "Em_overstrength_base_shear_kN": round(Em_base_shear_kN, 2)
        }

        trace = CalculationTrace(
            design_code=LateralCode.IBC.value,
            code_edition=edition.value,
            clause=clause_ref,
            inputs=inputs,
            method="IBC Section 1613 Equivalent Lateral Force Procedure with Ev and Overstrength Omega0",
            intermediate_results=intermediate,
            final_result=f"Base Shear V = {round(base_shear_V, 2)} kN, Base Overturning M0 = {round(M0_kNm, 2)} kN*m, SDC = {sdc.value}",
            limit="Story Drift Delta <= Delta_a, Stability theta <= theta_max",
            status=overall_drift_status
        )

        analysis_result = SeismicAnalysisResult(
            code=LateralCode.IBC,
            edition=edition,
            parameters=params,
            fundamental_period_T_s=Ta,
            period_upper_limit_T_max_s=T_max,
            governing_period_s=governing_T,
            total_effective_weight_W_kN=total_weight_W,
            seismic_response_coeff_Cs=Cs,
            Cs_governing_formula=cs_formula,
            base_shear_V_kN=base_shear_V,
            base_overturning_moment_M0_kNm=M0_kNm,
            story_results=story_results,
            max_drift_ratio=max_drift_ratio,
            max_drift_story=max_drift_story,
            max_stability_coefficient_theta=max_theta,
            overall_drift_status=overall_drift_status,
            trace=trace
        )

        return analysis_result, ibc_load_effects, trace

    @staticmethod
    def calculate_wind_effects(
        stories: List[StoryLevel],
        params: WindParameters,
        edition: CodeEdition = CodeEdition.IBC_2024,
    ) -> WindAnalysisResult:
        """
        Executes IBC Section 1609 Wind Loads:
        Uses ASCE 7 MWFRS directional methodology with IBC ultimate design wind speeds V_ult
        and calculates story forces, story shear, base shear, overturning, and drift.
        """
        res = ASCE7Engine.calculate_wind_forces_and_drift(stories, params)

        clause_ref = "IBC 2024 Section 1609 (Wind Loads)"
        if edition == CodeEdition.IBC_2021:
            clause_ref = "IBC 2021 Section 1609 (Wind Loads)"
        elif edition == CodeEdition.IBC_2018:
            clause_ref = "IBC 2018 Section 1609 (Wind Loads)"

        # Update trace to reflect IBC
        res.code = LateralCode.IBC
        res.edition = edition
        res.trace.design_code = LateralCode.IBC.value
        res.trace.code_edition = edition.value
        res.trace.clause = clause_ref

        return res
