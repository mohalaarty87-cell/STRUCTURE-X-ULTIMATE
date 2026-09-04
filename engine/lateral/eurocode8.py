"""
STRUCTURE-X ULTIMATE — EUROCODE 8 & EUROCODE 1 ENGINE
Modular implementation of Seismic Analysis (EN 1998-1:2004) and
Wind Actions (EN 1991-1-4:2005) strictly complying with European standards.
"""

import math
from typing import Dict, Any, List, Optional, Tuple

from .types import (
    LateralCode,
    CodeEdition,
    GroundTypeEC8,
    TerrainCategoryEC1,
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


class Eurocode8Engine:
    """
    Eurocode 8 (EN 1998-1:2004) Seismic and Eurocode 1 (EN 1991-1-4:2005) Wind Engine.
    """

    # -------------------------------------------------------------------------
    # EUROCODE 8 SEISMIC (EN 1998-1:2004 Section 3.2 & Section 4.3)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_ground_parameters(ground_type: GroundTypeEC8, spectrum_type: int = 1) -> Tuple[float, float, float, float]:
        """
        Returns soil factor S and corner periods TB, TC, TD per EN 1998-1:2004 Table 3.2 (Type 1 spectrum).
        """
        if spectrum_type == 1:  # Type 1: Ms > 5.5 (standard moderate-to-high seismicity)
            if ground_type == GroundTypeEC8.A:
                return 1.00, 0.15, 0.40, 2.00
            elif ground_type == GroundTypeEC8.B:
                return 1.20, 0.15, 0.50, 2.00
            elif ground_type == GroundTypeEC8.C:
                return 1.15, 0.20, 0.60, 2.00
            elif ground_type == GroundTypeEC8.D:
                return 1.35, 0.20, 0.80, 2.00
            elif ground_type == GroundTypeEC8.E:
                return 1.40, 0.15, 0.50, 2.00
            else:
                return 1.15, 0.20, 0.60, 2.00
        else:  # Type 2: Ms <= 5.5 (low seismicity)
            if ground_type == GroundTypeEC8.A:
                return 1.00, 0.05, 0.25, 1.20
            elif ground_type == GroundTypeEC8.B:
                return 1.35, 0.05, 0.25, 1.20
            elif ground_type == GroundTypeEC8.C:
                return 1.50, 0.10, 0.25, 1.20
            elif ground_type == GroundTypeEC8.D:
                return 1.80, 0.10, 0.30, 1.20
            elif ground_type == GroundTypeEC8.E:
                return 1.60, 0.05, 0.25, 1.20
            else:
                return 1.50, 0.10, 0.25, 1.20

    @staticmethod
    def calculate_design_spectral_acceleration(
        T_s: float,
        ag_design: float,
        ground_type: GroundTypeEC8 = GroundTypeEC8.C,
        q_behavior: float = 4.0,
        beta_lower_bound: float = 0.20,
    ) -> Tuple[float, str, CalculationTrace]:
        """
        Calculates design spectral acceleration Sd(T) per EN 1998-1:2004 Section 3.2.2.5:
        - 0 <= T <= TB: Sd(T) = ag * S * [2/3 + (T/TB) * (2.5/q - 2/3)]
        - TB <= T <= TC: Sd(T) = ag * S * (2.5 / q)
        - TC <= T <= TD: Sd(T) = max(ag * S * (2.5 / q) * (TC / T), beta * ag)
        - T >= TD: Sd(T) = max(ag * S * (2.5 / q) * (TC * TD / T^2), beta * ag)
        """
        S, TB, TC, TD = Eurocode8Engine.get_ground_parameters(ground_type)
        q = max(q_behavior, 1.5)
        T = max(T_s, 0.001)

        if T <= TB:
            sd = ag_design * S * ( (2.0 / 3.0) + (T / TB) * ((2.5 / q) - (2.0 / 3.0)) )
            clause = "EN 1998-1:2004 Eq. (3.13) (0 <= T <= TB)"
        elif T <= TC:
            sd = ag_design * S * (2.5 / q)
            clause = "EN 1998-1:2004 Eq. (3.14) (TB <= T <= TC Plateau)"
        elif T <= TD:
            branch = ag_design * S * (2.5 / q) * (TC / T)
            lower = beta_lower_bound * ag_design
            sd = max(branch, lower)
            clause = "EN 1998-1:2004 Eq. (3.15) (TC <= T <= TD)" if branch >= lower else "EN 1998-1:2004 Eq. (3.15) Lower Bound (beta*ag)"
        else:
            branch = ag_design * S * (2.5 / q) * (TC * TD / (T ** 2))
            lower = beta_lower_bound * ag_design
            sd = max(branch, lower)
            clause = "EN 1998-1:2004 Eq. (3.16) (T >= TD)" if branch >= lower else "EN 1998-1:2004 Eq. (3.16) Lower Bound (beta*ag)"

        inputs = {
            "period_T_s": T_s,
            "ag_design_g": ag_design,
            "ground_type": ground_type.value,
            "q_behavior": q,
            "beta_lower_bound": beta_lower_bound
        }
        intermediate = {
            "S_soil_factor": S,
            "TB_s": TB,
            "TC_s": TC,
            "TD_s": TD,
            "Sd_g": round(sd, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.EUROCODE_8.value,
            code_edition=CodeEdition.EN_1998_1_2004.value,
            clause=clause,
            inputs=inputs,
            method="Eurocode 8 Design Spectrum Sd(T) for Elastic Analysis with Behavior Factor q",
            intermediate_results=intermediate,
            final_result=f"Sd(T) = {round(sd, 5)} g",
            limit=f">= {round(beta_lower_bound * ag_design, 4)} g",
            status=DesignStatus.PASS
        )

        return sd, clause, trace

    @staticmethod
    def calculate_approximate_period(
        total_height_m: float,
        system_type: str = "STEEL_MOMENT_FRAME"
    ) -> Tuple[float, CalculationTrace]:
        """
        Calculates fundamental period T1 per EN 1998-1:2004 Section 4.3.3.2.2 Eq. (4.6):
        T1 = Ct * H^(3/4)
        """
        sys_upper = system_type.upper()
        if "STEEL_MOMENT" in sys_upper:
            Ct = 0.085
            desc = "Moment Resisting Space Steel Frames"
        elif "CONCRETE_MOMENT" in sys_upper:
            Ct = 0.075
            desc = "Moment Resisting Space Concrete Frames"
        else:
            Ct = 0.050
            desc = "All Other Structures"

        T1 = Ct * (total_height_m ** 0.75)

        inputs = {
            "total_height_H_m": total_height_m,
            "Ct": Ct,
            "system_type": desc
        }

        trace = CalculationTrace(
            design_code=LateralCode.EUROCODE_8.value,
            code_edition=CodeEdition.EN_1998_1_2004.value,
            clause="EN 1998-1:2004 Section 4.3.3.2.2 (Eq. 4.6)",
            inputs=inputs,
            method="Fundamental Period T1 = Ct * H^(3/4)",
            intermediate_results={"Ct": Ct, "H_m": total_height_m},
            final_result=f"T1 = {round(T1, 4)} s",
            limit="N/A",
            status=DesignStatus.PASS
        )

        return T1, trace

    @staticmethod
    def calculate_seismic_analysis(
        stories: List[StoryLevel],
        params: SeismicParameters,
        system_type: str = "STEEL_MOMENT_FRAME",
        edition: CodeEdition = CodeEdition.EN_1998_1_2004,
    ) -> SeismicAnalysisResult:
        """
        Performs full Eurocode 8 Lateral Force Method of Analysis (Section 4.3.3.2):
        1. Fundamental period T1
        2. Design spectrum acceleration Sd(T1)
        3. Base shear Fb = Sd(T1) * m * lambda (Eq. 4.5)
        4. Vertical force distribution Fi = Fb * (zi * mi) / sum(zj * mj) (Eq. 4.10)
        5. Story shear Vi and overturning moments Mi
        6. Interstorey drift sensitivity coefficient theta = (Ptot * dr) / (Vtot * h) (Eq. 4.28)
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m

        # 1. Fundamental period
        T1, _ = Eurocode8Engine.calculate_approximate_period(total_height_m, system_type)

        # 2. Design acceleration Sd(T1)
        S, TB, TC, TD = Eurocode8Engine.get_ground_parameters(params.ground_type_ec8)
        Sd, clause_sd, _ = Eurocode8Engine.calculate_design_spectral_acceleration(
            T_s=T1,
            ag_design=params.ag_design,
            ground_type=params.ground_type_ec8,
            q_behavior=params.q_behavior_factor
        )

        # 3. Correction factor lambda (Section 4.3.3.2.2 Eq. 4.5)
        # lambda = 0.85 if T1 <= 2*TC and building has more than 2 storeys; otherwise 1.00
        lambda_corr = 0.85 if (T1 <= 2.0 * TC and n > 2) else 1.00

        # Total mass / effective weight
        total_weight_W = sum(s.weight_kN for s in stories)
        # Base shear Fb = Sd * W * lambda (in kN)
        base_shear_Fb_kN = Sd * total_weight_W * lambda_corr

        # 4. Vertical Distribution (Eq. 4.10)
        # Fi = Fb * (zi * mi) / sum(zj * mj)
        z_w = [story.height_from_base_m * story.weight_kN for story in stories]
        sum_z_w = sum(z_w) if sum(z_w) > 0 else 1.0
        Cvx = [zw / sum_z_w for zw in z_w]
        Fx_kN = [cv * base_shear_Fb_kN for cv in Cvx]

        # 5. Story Shear and Overturning Moments
        Vx_kN = [0.0] * n
        Mx_kNm = [0.0] * n
        for i in range(n):
            Vx_kN[i] = sum(Fx_kN[j] for j in range(i, n))
            hx = stories[i].height_from_base_m
            Mx_kNm[i] = sum(Fx_kN[j] * (stories[j].height_from_base_m - hx) for j in range(i, n))

        base_overturning_M0_kNm = sum(Fx_kN[i] * stories[i].height_from_base_m for i in range(n))

        # 6. Interstorey Drift Sensitivity theta = Ptot * dr / (Vtot * h) (Eq. 4.28)
        # and Damage Limitation Check dr * nu <= 0.0075 * h
        story_results: List[StorySeismicResult] = []
        cum_dxe = 0.0
        max_drift_ratio = 0.0
        max_drift_story = ""
        max_theta = 0.0
        overall_status = DesignStatus.PASS

        # Damage limitation limit ratio
        allowable_drift_ratio = 0.0075  # typical EC8 damage limitation for non-structural ductile elements

        for i in range(n):
            story = stories[i]
            hsx_mm = story.story_height_m * 1000.0
            k_story = max(story.lateral_stiffness_kN_per_mm, 0.1)

            # Elastic displacement
            inter_de = Vx_kN[i] / k_story
            cum_dxe += inter_de

            # Design displacement in EC8: ds = q * de
            ds_mm = params.q_behavior_factor * cum_dxe
            prev_ds = params.q_behavior_factor * (cum_dxe - inter_de) if i > 0 else 0.0
            dr_mm = ds_mm - prev_ds  # Design interstorey drift dr

            drift_ratio = dr_mm / hsx_mm if hsx_mm > 0 else 0.0
            if drift_ratio > max_drift_ratio:
                max_drift_ratio = drift_ratio
                max_drift_story = story.name

            # Ptot: total gravity load at and above level x
            Ptot_kN = sum(stories[j].weight_kN for j in range(i, n))

            # Stability coefficient theta = (Ptot * dr) / (Vtot * h)
            denom = Vx_kN[i] * hsx_mm
            theta = (Ptot_kN * dr_mm) / denom if denom > 0 else 0.0

            if theta > max_theta:
                max_theta = theta

            # EC8 Section 4.4.2.2: theta <= 0.30 absolute limit; if > 0.20 structural redesign is mandatory
            is_pass = (drift_ratio <= allowable_drift_ratio) and (theta <= 0.20)
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
                    design_displacement_dx_mm=ds_mm,
                    story_drift_delta_mm=dr_mm,
                    allowable_drift_delta_a_mm=allowable_drift_ratio * hsx_mm,
                    drift_ratio=drift_ratio,
                    allowable_drift_ratio=allowable_drift_ratio,
                    stability_coefficient_theta=theta,
                    drift_status=DesignStatus.PASS if is_pass else DesignStatus.FAIL
                )
            )

        inputs = {
            "ag_design_g": params.ag_design,
            "ground_type": params.ground_type_ec8.value,
            "q_behavior": params.q_behavior_factor,
            "total_height_m": total_height_m,
            "total_weight_W_kN": round(total_weight_W, 1)
        }
        intermediate = {
            "T1_fundamental_period_s": round(T1, 3),
            "Sd_acceleration_g": round(Sd, 5),
            "lambda_factor": lambda_corr,
            "base_shear_Fb_kN": round(base_shear_Fb_kN, 2),
            "base_overturning_M0_kNm": round(base_overturning_M0_kNm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5),
            "max_stability_theta": round(max_theta, 4)
        }

        trace = CalculationTrace(
            design_code=LateralCode.EUROCODE_8.value,
            code_edition=edition.value,
            clause="EN 1998-1:2004 Section 4.3.3.2 (Lateral Force Method) & Section 4.4.2.2 (P-Delta theta)",
            inputs=inputs,
            method="Eurocode 8 Base Shear Fb = Sd(T1)*m*lambda and Vertical Distribution Fi = Fb*(zi*mi)/sum(zj*mj)",
            intermediate_results=intermediate,
            final_result=f"Base Shear Fb = {round(base_shear_Fb_kN, 2)} kN, Base Overturning M0 = {round(base_overturning_M0_kNm, 2)} kN*m, Max theta = {round(max_theta, 4)}",
            limit="theta <= 0.20 (Second-order limit), dr/h <= 0.0075 (Damage limitation)",
            status=overall_status
        )

        return SeismicAnalysisResult(
            code=LateralCode.EUROCODE_8,
            edition=edition,
            parameters=params,
            fundamental_period_T_s=T1,
            period_upper_limit_T_max_s=T1 * 1.4,
            governing_period_s=T1,
            total_effective_weight_W_kN=total_weight_W,
            seismic_response_coeff_Cs=Sd * lambda_corr,
            Cs_governing_formula="EN 1998-1:2004 Eq. 4.5 (Sd * lambda)",
            base_shear_V_kN=base_shear_Fb_kN,
            base_overturning_moment_M0_kNm=base_overturning_M0_kNm,
            story_results=story_results,
            max_drift_ratio=max_drift_ratio,
            max_drift_story=max_drift_story,
            max_stability_coefficient_theta=max_theta,
            overall_drift_status=overall_status,
            trace=trace
        )

    # -------------------------------------------------------------------------
    # EUROCODE 1 WIND ACTIONS (EN 1991-1-4:2005)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_terrain_parameters(terrain: TerrainCategoryEC1) -> Tuple[float, float]:
        """
        Roughness length z0 and minimum height zmin per EN 1991-1-4:2005 Table 4.1.
        """
        if terrain == TerrainCategoryEC1.ZERO:
            return 0.003, 1.0
        elif terrain == TerrainCategoryEC1.I:
            return 0.01, 1.0
        elif terrain == TerrainCategoryEC1.II:
            return 0.05, 2.0
        elif terrain == TerrainCategoryEC1.III:
            return 0.30, 5.0
        elif terrain == TerrainCategoryEC1.IV:
            return 1.00, 10.0
        else:
            return 0.05, 2.0

    @staticmethod
    def calculate_peak_velocity_pressure(
        z_m: float,
        vb_mps: float,
        terrain: TerrainCategoryEC1 = TerrainCategoryEC1.II,
        rho_air: float = 1.225,
    ) -> Tuple[float, float, float]:
        """
        Calculates roughness factor cr(z), turbulence intensity Iv(z), and
        peak velocity pressure qp(z) per EN 1991-1-4:2005 Sections 4.3 - 4.5:
        kr = 0.19 * (z0 / 0.05)^0.07
        cr(z) = kr * ln(max(z, zmin) / z0)
        vm(z) = cr(z) * vb
        Iv(z) = 1.0 / (ln(max(z, zmin) / z0))
        qp(z) = [1 + 7 * Iv(z)] * 0.5 * rho * vm(z)^2
        """
        z0, zmin = Eurocode8Engine.get_terrain_parameters(terrain)
        kr = 0.19 * ((z0 / 0.05) ** 0.07)
        eff_z = max(z_m, zmin)
        cr = kr * math.log(eff_z / z0)
        vm = cr * vb_mps
        Iv = 1.0 / max(math.log(eff_z / z0), 0.5)
        # qp(z) in N/m2
        qp = (1.0 + 7.0 * Iv) * 0.5 * rho_air * (vm ** 2)
        return qp, vm, cr

    @staticmethod
    def calculate_wind_analysis(
        stories: List[StoryLevel],
        params: WindParameters,
        edition: CodeEdition = CodeEdition.EN_1991_1_4_2005,
    ) -> WindAnalysisResult:
        """
        Executes Eurocode 1 (EN 1991-1-4:2005) Wind Analysis:
        Generates:
        - Story Wind Forces (Fw)
        - Story Shear (Vw)
        - Base Shear
        - Overturning
        - Drift
        """
        n = len(stories)
        total_height_m = stories[-1].height_from_base_m

        # External pressure coefficients per EN 1991-1-4 Table 7.1
        cpe_windward = 0.80
        cpe_leeward = -0.50
        cs_cd = params.cs_cd_structural_factor

        story_results: List[StoryWindResult] = []
        Fw_kN = [0.0] * n
        Vw_kN = [0.0] * n
        Mw_kNm = [0.0] * n

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

            qp, vm, cr = Eurocode8Engine.calculate_peak_velocity_pressure(
                z, params.basic_wind_speed_mps, params.terrain_category_ec1, params.air_density_kg_m3
            )

            p_windward = qp * cpe_windward
            p_leeward = qp * cpe_leeward
            net_pressure = cs_cd * (p_windward - p_leeward)

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
                    Kz_exposure_coeff=cr,
                    velocity_pressure_qz_N_m2=qp,
                    windward_pressure_p_N_m2=p_windward,
                    leeward_pressure_p_N_m2=p_leeward,
                    net_design_pressure_N_m2=net_pressure,
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

        # Wind Drift
        allowable_drift_ratio = 0.0025  # H/400
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
            "basic_wind_velocity_vb_mps": params.basic_wind_speed_mps,
            "terrain_category": params.terrain_category_ec1.value,
            "cs_cd_factor": cs_cd,
            "total_height_m": total_height_m
        }
        intermediate = {
            "base_shear_Vw_kN": round(base_shear_Vw_kN, 2),
            "base_overturning_Mw0_kNm": round(base_overturning_Mw0_kNm, 2),
            "max_drift_ratio": round(max_drift_ratio, 5)
        }

        trace = CalculationTrace(
            design_code=LateralCode.EUROCODE_8.value,
            code_edition=edition.value,
            clause="EN 1991-1-4:2005 Sections 4.5 & 7.2 (Peak Velocity Pressure qp & Pressure Coefficients cpe)",
            inputs=inputs,
            method="Eurocode 1 Wind Load Analysis (qp(z), Windward/Leeward Actions, Story Shear & Drift)",
            intermediate_results=intermediate,
            final_result=f"Wind Base Shear = {round(base_shear_Vw_kN, 2)} kN, Base Overturning = {round(base_overturning_Mw0_kNm, 2)} kN*m",
            limit="Interstorey Drift <= 0.0025 (H/400)",
            status=overall_status
        )

        return WindAnalysisResult(
            code=LateralCode.EUROCODE_8,
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
