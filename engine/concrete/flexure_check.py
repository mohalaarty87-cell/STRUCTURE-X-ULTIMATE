"""
STRUCTURE-X ULTIMATE — FLEXURAL CAPACITY & DESIGN CHECK
Evaluates bending strength, required and provided flexural reinforcement, strain compatibility,
and tension-control limits for Beams, Slabs, and Walls.
Strictly complies with ACI 318-19 (Clauses 22.2, 22.3, 9.6.1) and Eurocode 2 (Clauses 6.1 & 9.2.1.1).
"""

import math
from typing import Optional, Dict, Any
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


class FlexureCheck:
    """
    Modular flexural strength and reinforcement design engine.
    """

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Mu_kNm: float,  # Factored design bending moment (kN*m)
        b_mm: float,  # Width of compression face (mm)
        d_mm: float,  # Effective depth to tension rebar centroid (mm)
        h_mm: float,  # Total section depth (mm)
        As_provided_mm2: float,  # Provided tension reinforcement (mm^2)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        As_comp_provided_mm2: float = 0.0,  # Compression steel (optional, mm^2)
        d_prime_mm: float = 50.0,  # Depth to compression steel centroid (mm)
    ) -> DesignCheckResult:
        """
        ACI 318-19 Flexural Strength & Reinforcement Design Check:
        Clauses 22.2, 22.3, 9.6.1, and Table 21.2.2.
        """
        fc = concrete.fc_prime
        fy = rebar.fy
        Es = rebar.Es
        ey = fy / Es
        beta1 = concrete.get_beta1_aci()

        inputs: Dict[str, Any] = {
            "Mu_kNm": Mu_kNm,
            "b_mm": b_mm,
            "d_mm": d_mm,
            "h_mm": h_mm,
            "As_provided_mm2": As_provided_mm2,
            "fc_prime_MPa": fc,
            "fy_MPa": fy,
            "Es_MPa": Es,
            "beta1": beta1,
            "As_comp_mm2": As_comp_provided_mm2
        }

        intermediate: Dict[str, Any] = {}

        # 1. Minimum and Maximum flexural reinforcement
        if member_type == MemberType.SLAB:
            # ACI 318-19 Clause 24.4.3.2: Shrinkage and temperature steel rho = 0.0018
            As_min_mm2 = 0.0018 * b_mm * h_mm
            min_clause = "ACI 318-19 Clause 24.4.3.2 (rho_min = 0.0018 for slabs)"
        else:
            # ACI 318-19 Clause 9.6.1.2: Beams
            As_min1 = (0.25 * math.sqrt(fc) / fy) * b_mm * d_mm
            As_min2 = (1.4 / fy) * b_mm * d_mm
            As_min_mm2 = max(As_min1, As_min2)
            min_clause = "ACI 318-19 Clause 9.6.1.2: max(0.25*sqrt(f'c)/fy, 1.4/fy) * b * d"

        # 2. Section Analysis with Provided As
        # Stress block depth a = (As*fy - As'*fs') / (0.85 * f'c * b)
        # Check compression steel yielding
        fs_prime = 0.0
        if As_comp_provided_mm2 > 0.0:
            # Iterative or direct trial: assume compression steel yields first
            a_trial = (As_provided_mm2 * fy - As_comp_provided_mm2 * fy) / (0.85 * fc * b_mm)
            c_trial = a_trial / beta1
            eps_s_prime = 0.003 * (c_trial - d_prime_mm) / max(c_trial, 1e-6)
            if eps_s_prime >= ey:
                fs_prime = fy
                a = a_trial
            else:
                fs_prime = max(0.0, min(fy, eps_s_prime * Es))
                a = (As_provided_mm2 * fy - As_comp_provided_mm2 * fs_prime) / (0.85 * fc * b_mm)
        else:
            a = (As_provided_mm2 * fy) / (0.85 * fc * b_mm)

        a = max(a, 0.0)
        c = a / beta1
        eps_t = 0.003 * (d_mm - c) / max(c, 1e-6)

        # Strength reduction factor phi (Table 21.2.2)
        if eps_t >= 0.005:
            phi = 0.90
            section_behavior = "Tension-Controlled (eps_t >= 0.005)"
        elif eps_t <= ey:
            phi = 0.65
            section_behavior = "Compression-Controlled (eps_t <= eps_ty)"
        else:
            phi = 0.65 + 0.25 * ((eps_t - ey) / (0.005 - ey))
            section_behavior = "Transition Zone"

        # Nominal moment capacity Mn
        if As_comp_provided_mm2 > 0 and fs_prime > 0:
            Cc = 0.85 * fc * a * b_mm
            Cs = As_comp_provided_mm2 * fs_prime
            Mn_Nmm = Cc * (d_mm - a / 2.0) + Cs * (d_mm - d_prime_mm)
        else:
            Mn_Nmm = As_provided_mm2 * fy * (d_mm - a / 2.0)

        Mn_kNm = Mn_Nmm / 1.0e6
        phi_Mn_kNm = phi * Mn_kNm

        # 3. Calculate Required Reinforcement As_req for design demand Mu
        Mu_Nmm = abs(Mu_kNm) * 1.0e6
        # Assume phi = 0.90 for required steel calculation
        phi_assumed = 0.90
        Rn = Mu_Nmm / (phi_assumed * b_mm * (d_mm ** 2))
        disc = 1.0 - (2.0 * Rn) / (0.85 * fc)
        if disc >= 0.0:
            rho_req = (0.85 * fc / fy) * (1.0 - math.sqrt(disc))
            As_req_calc = rho_req * b_mm * d_mm
        else:
            # Over-reinforced; section requires larger depth or compression steel
            As_req_calc = (0.85 * fc * beta1 * (0.375 * d_mm) * b_mm) / fy

        As_required_mm2 = max(As_req_calc, As_min_mm2)

        # Maximum permitted steel area for ductile behavior (ACI 318-19 Cl. 9.3.3.1: eps_t >= 0.004)
        c_max = (3.0 / 7.0) * d_mm  # corresponding to eps_t = 0.004
        a_max = beta1 * c_max
        As_max_mm2 = (0.85 * fc * a_max * b_mm) / fy

        intermediate["a_stress_block_depth_mm"] = round(a, 2)
        intermediate["c_neutral_axis_depth_mm"] = round(c, 2)
        intermediate["c_over_d_ratio"] = round(c / d_mm, 4)
        intermediate["eps_t_tension_strain"] = round(eps_t, 6)
        intermediate["phi_strength_factor"] = round(phi, 3)
        intermediate["behavior"] = section_behavior
        intermediate["Mn_nominal_kNm"] = round(Mn_kNm, 2)
        intermediate["phi_Mn_design_kNm"] = round(phi_Mn_kNm, 2)
        intermediate["As_min_mm2"] = round(As_min_mm2, 2)
        intermediate["As_max_mm2 (eps_t=0.004)"] = round(As_max_mm2, 2)
        intermediate["min_code_clause"] = min_clause

        capacity_kNm = phi_Mn_kNm
        demand_kNm = abs(Mu_kNm)
        dc_ratio = demand_kNm / capacity_kNm if capacity_kNm > 0 else 999.0

        is_ductile = eps_t >= 0.004
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and is_ductile and As_provided_mm2 >= As_min_mm2 * 0.99) else DesignStatus.FAIL

        rho_prov = As_provided_mm2 / (b_mm * d_mm)
        reinf = ReinforcementResult(
            required_area_mm2=As_required_mm2,
            provided_area_mm2=As_provided_mm2,
            reinforcement_ratio=rho_prov,
            min_area_mm2=As_min_mm2,
            max_area_mm2=As_max_mm2,
            bar_callout=f"{round(As_provided_mm2)} mm² provided (rho = {round(rho_prov * 100, 3)}%)"
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause="ACI 318-19 Clauses 22.2, 22.3, 9.6.1 & Table 21.2.2",
            inputs=inputs,
            method="Whitney Equivalent Rectangular Stress Block Strain Compatibility",
            intermediate_results=intermediate,
            final_result=f"Capacity phi*Mn = {round(capacity_kNm, 2)} kN*m",
            limit=f"Demand Mu = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Flexure check: Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(capacity_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.FLEXURE,
            member_type=member_type,
            demand=demand_kNm,
            capacity=capacity_kNm,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN*m",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_2(
        member_type: MemberType,
        MEd_kNm: float,  # Design bending moment (kN*m)
        b_mm: float,  # Section width (mm)
        d_mm: float,  # Effective depth (mm)
        h_mm: float,  # Overall depth (mm)
        As_provided_mm2: float,  # Provided reinforcement (mm^2)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        alpha_cc: float = 0.85,
    ) -> DesignCheckResult:
        """
        Eurocode 2 (EN 1992-1-1:2004) Flexural Design Check:
        Clauses 6.1 & 9.2.1.1.
        """
        fck = concrete.fc_prime
        fcd = concrete.get_design_strength_ec2(gamma_c=1.5, alpha_cc=alpha_cc)
        fctm = concrete.get_fctm_ec2()
        fyk = rebar.fy
        fyd = rebar.get_design_yield_strength_ec2(gamma_s=1.15)
        lambda_ec, eta_ec = concrete.get_ec2_stress_block_factors()

        inputs: Dict[str, Any] = {
            "MEd_kNm": MEd_kNm,
            "b_mm": b_mm,
            "d_mm": d_mm,
            "h_mm": h_mm,
            "As_provided_mm2": As_provided_mm2,
            "fck_MPa": fck,
            "fcd_MPa": round(fcd, 2),
            "fyk_MPa": fyk,
            "fyd_MPa": round(fyd, 2),
            "fctm_MPa": round(fctm, 2),
            "gamma_c": 1.5,
            "gamma_s": 1.15
        }

        intermediate: Dict[str, Any] = {}

        # Minimum & Maximum Reinforcement (EC2 Cl. 9.2.1.1)
        As_min1 = 0.26 * (fctm / fyk) * b_mm * d_mm
        As_min2 = 0.0013 * b_mm * d_mm
        As_min_mm2 = max(As_min1, As_min2)
        As_max_mm2 = 0.04 * b_mm * h_mm

        # Capacity with provided As
        # Equilibrium: F_c = F_s -> eta * fcd * b * (lambda * x) = As * fyd
        x = (As_provided_mm2 * fyd) / (eta_ec * fcd * b_mm * lambda_ec)
        z = d_mm - 0.5 * lambda_ec * x
        MRd_Nmm = As_provided_mm2 * fyd * z
        MRd_kNm = MRd_Nmm / 1.0e6

        # Required As for demand MEd
        MEd_Nmm = abs(MEd_kNm) * 1.0e6
        mu = MEd_Nmm / (b_mm * (d_mm ** 2) * fcd)
        mu_lim = 0.167  # standard ductility limit without redistribution

        if mu <= mu_lim:
            z_req = (d_mm / 2.0) * (1.0 + math.sqrt(max(0.0, 1.0 - 2.0 * mu)))
            z_req = min(z_req, 0.95 * d_mm)
            As_req_calc = MEd_Nmm / (fyd * z_req)
        else:
            z_req = (d_mm / 2.0) * (1.0 + math.sqrt(max(0.0, 1.0 - 2.0 * mu_lim)))
            As_req_calc = MEd_Nmm / (fyd * z_req)

        As_required_mm2 = max(As_req_calc, As_min_mm2)

        intermediate["fcd_MPa"] = round(fcd, 2)
        intermediate["fyd_MPa"] = round(fyd, 2)
        intermediate["neutral_axis_depth_x_mm"] = round(x, 2)
        intermediate["x_over_d"] = round(x / d_mm, 4)
        intermediate["lever_arm_z_mm"] = round(z, 2)
        intermediate["normalized_moment_mu"] = round(mu, 4)
        intermediate["MRd_capacity_kNm"] = round(MRd_kNm, 2)
        intermediate["As_min_mm2"] = round(As_min_mm2, 2)
        intermediate["As_max_mm2"] = round(As_max_mm2, 2)

        capacity_kNm = MRd_kNm
        demand_kNm = abs(MEd_kNm)
        dc_ratio = demand_kNm / capacity_kNm if capacity_kNm > 0 else 999.0
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and As_provided_mm2 >= As_min_mm2 * 0.99) else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=As_required_mm2,
            provided_area_mm2=As_provided_mm2,
            reinforcement_ratio=As_provided_mm2 / (b_mm * d_mm),
            min_area_mm2=As_min_mm2,
            max_area_mm2=As_max_mm2,
            bar_callout=f"{round(As_provided_mm2)} mm² provided"
        )

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_2.value,
            code_edition=CodeEdition.EN_1992_1_1_2004.value,
            clause="EN 1992-1-1:2004 Clauses 6.1 & 9.2.1.1",
            inputs=inputs,
            method="Eurocode 2 Parabolic-Rectangular / Rectangular Stress Block Limit State",
            intermediate_results=intermediate,
            final_result=f"Capacity MRd = {round(capacity_kNm, 2)} kN*m",
            limit=f"Demand MEd = {round(demand_kNm, 2)} kN*m (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC2 Flexure check: Demand = {round(demand_kNm, 1)} kN*m, Capacity = {round(capacity_kNm, 1)} kN*m, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.FLEXURE,
            member_type=member_type,
            demand=demand_kNm,
            capacity=capacity_kNm,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN*m",
            summary_message=summary
        )
