"""
STRUCTURE-X ULTIMATE — AXIAL CAPACITY & DESIGN CHECK
Evaluates axial compression and pure axial tension for Columns, Walls, and Frame Members.
Complies strictly with ACI 318-19 (Clause 22.4) and Eurocode 2 (Clause 6.1 & 9.5.2).
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


class AxialCheck:
    """
    Modular axial strength evaluator for reinforced concrete members.
    """

    @staticmethod
    def check_aci_318_19(
        member_type: MemberType,
        Pu_kN: float,  # Factored axial demand (kN, positive = compression, negative = tension)
        Ag_mm2: float,  # Gross cross-sectional area (mm^2)
        Ast_provided_mm2: float,  # Provided longitudinal reinforcement area (mm^2)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        tie_type: str = "Ties",  # "Ties" or "Spiral"
    ) -> DesignCheckResult:
        """
        ACI 318-19 Axial Design Check:
        Compression: Clauses 22.4.2, 10.6.2, 10.6.3, Table 22.4.2.1, Table 21.2.2.
        Tension: Clause 22.4.3.1.
        """
        is_compression = Pu_kN >= 0.0
        abs_Pu_N = abs(Pu_kN) * 1000.0

        fc = concrete.fc_prime
        fy = rebar.fy

        inputs: Dict[str, Any] = {
            "Pu_kN": Pu_kN,
            "Ag_mm2": Ag_mm2,
            "Ast_provided_mm2": Ast_provided_mm2,
            "fc_prime_MPa": fc,
            "fy_MPa": fy,
            "tie_type": tie_type,
            "loading_type": "Compression" if is_compression else "Tension"
        }

        intermediate: Dict[str, Any] = {}

        if is_compression:
            # Compression provisions
            if tie_type.lower() == "spiral":
                phi = 0.75  # ACI 318-19 Table 21.2.2
                k_max = 0.85  # ACI 318-19 Table 22.4.2.1 for spirals
                clause = "ACI 318-19 Table 22.4.2.1 & Table 21.2.2 (Spiral Column)"
            else:
                phi = 0.65  # ACI 318-19 Table 21.2.2
                k_max = 0.80  # ACI 318-19 Table 22.4.2.1 for tied members
                clause = "ACI 318-19 Table 22.4.2.1 & Table 21.2.2 (Tied Member)"

            # Pure concentric axial strength P0: ACI 318-19 Eq. 22.4.2.2
            # P0 = 0.85 * f'c * (Ag - Ast) + fy * Ast
            net_Ac = max(Ag_mm2 - Ast_provided_mm2, 0.0)
            P0_N = 0.85 * fc * net_Ac + fy * Ast_provided_mm2
            Pn_max_N = k_max * P0_N
            phi_Pn_max_N = phi * Pn_max_N
            phi_Pn_max_kN = phi_Pn_max_N / 1000.0

            # Minimum and maximum longitudinal steel limits (ACI 318-19 Cl. 10.6.1.1)
            Ast_min_mm2 = 0.01 * Ag_mm2
            Ast_max_mm2 = 0.04 * Ag_mm2  # Practical 4% limit (code allows up to 8% non-lapped)

            # Required reinforcement to resist Pu
            # Pu <= phi * k_max * [ 0.85 * f'c * (Ag - Ast) + fy * Ast ]
            target_P0_N = abs_Pu_N / (phi * k_max)
            denom = fy - 0.85 * fc
            if denom > 0:
                Ast_req_calc = (target_P0_N - 0.85 * fc * Ag_mm2) / denom
            else:
                Ast_req_calc = 0.0
            Ast_required_mm2 = max(Ast_req_calc, Ast_min_mm2)

            intermediate["P0_kN"] = round(P0_N / 1000.0, 2)
            intermediate["Pn_max_kN"] = round(Pn_max_N / 1000.0, 2)
            intermediate["phi"] = phi
            intermediate["k_max_accidental_eccentricity"] = k_max
            intermediate["concrete_net_area_Ac_mm2"] = round(net_Ac, 1)
            intermediate["Ast_min_mm2 (1.0% Ag)"] = round(Ast_min_mm2, 1)
            intermediate["Ast_max_mm2 (4.0% Ag)"] = round(Ast_max_mm2, 1)

            capacity_kN = phi_Pn_max_kN
            demand_kN = Pu_kN
            dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0
            method = "ACI 318-19 Whitney Rectangular Stress Block with Accidental Eccentricity Cap"

        else:
            # Pure tension provisions: ACI 318-19 Cl. 22.4.3.1
            clause = "ACI 318-19 Clause 22.4.3.1 & Table 21.2.2 (Pure Tension)"
            phi = 0.90  # Tension-controlled
            Pnt_N = Ast_provided_mm2 * fy
            phi_Pnt_N = phi * Pnt_N
            phi_Pnt_kN = phi_Pnt_N / 1000.0

            Ast_min_mm2 = 0.005 * Ag_mm2
            Ast_max_mm2 = 0.04 * Ag_mm2
            Ast_required_mm2 = abs_Pu_N / (phi * fy)

            intermediate["Pnt_nominal_tension_kN"] = round(Pnt_N / 1000.0, 2)
            intermediate["phi"] = phi
            intermediate["Ast_min_mm2"] = round(Ast_min_mm2, 1)

            capacity_kN = phi_Pnt_kN
            demand_kN = abs(Pu_kN)
            dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0
            method = "ACI 318-19 Direct Tension in Reinforcing Steel"

        status = DesignStatus.PASS if (dc_ratio <= 1.0 and Ast_provided_mm2 >= intermediate.get("Ast_min_mm2 (1.0% Ag)", Ast_min_mm2) * 0.99) else DesignStatus.FAIL

        rho_prov = Ast_provided_mm2 / Ag_mm2 if Ag_mm2 > 0 else 0.0
        reinf = ReinforcementResult(
            required_area_mm2=Ast_required_mm2,
            provided_area_mm2=Ast_provided_mm2,
            reinforcement_ratio=rho_prov,
            min_area_mm2=Ast_min_mm2,
            max_area_mm2=Ast_max_mm2,
            bar_callout=f"{round(Ast_provided_mm2)} mm² provided"
        )

        trace = CalculationTrace(
            design_code=DesignCode.ACI_318.value,
            code_edition=CodeEdition.ACI_318_19.value,
            clause=clause,
            inputs=inputs,
            method=method,
            intermediate_results=intermediate,
            final_result=f"Capacity = {round(capacity_kN, 2)} kN",
            limit=f"Demand Pu = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Axial check: Demand = {round(demand_kN, 1)} kN, Capacity = {round(capacity_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.AXIAL,
            member_type=member_type,
            demand=demand_kN,
            capacity=capacity_kN,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_2(
        member_type: MemberType,
        NEd_kN: float,  # Design axial load (kN, positive = compression, negative = tension)
        Ac_mm2: float,  # Concrete area (mm^2)
        As_provided_mm2: float,  # Total longitudinal reinforcement (mm^2)
        concrete: ConcreteMaterial,
        rebar: RebarMaterial,
        alpha_cc: float = 0.85,
    ) -> DesignCheckResult:
        """
        Eurocode 2 (EN 1992-1-1:2004) Axial Design Check:
        Clauses 6.1 & 9.5.2.
        """
        is_compression = NEd_kN >= 0.0
        abs_NEd_N = abs(NEd_kN) * 1000.0

        fcd = concrete.get_design_strength_ec2(gamma_c=1.5, alpha_cc=alpha_cc)
        fyd = rebar.get_design_yield_strength_ec2(gamma_s=1.15)

        inputs: Dict[str, Any] = {
            "NEd_kN": NEd_kN,
            "Ac_mm2": Ac_mm2,
            "As_provided_mm2": As_provided_mm2,
            "fck_MPa": concrete.fc_prime,
            "fcd_MPa": round(fcd, 2),
            "fyk_MPa": rebar.fy,
            "fyd_MPa": round(fyd, 2),
            "gamma_c": 1.5,
            "gamma_s": 1.15
        }

        intermediate: Dict[str, Any] = {}

        if is_compression:
            clause = "EN 1992-1-1:2004 Clause 6.1 & Clause 9.5.2"
            # NRd = Ac * fcd + As * fyd
            net_Ac = max(Ac_mm2 - As_provided_mm2, 0.0)
            NRd_N = net_Ac * fcd + As_provided_mm2 * fyd
            NRd_kN = NRd_N / 1000.0

            # Minimum and maximum steel (EC2 Cl. 9.5.2(2))
            As_min_mm2 = max(0.10 * abs_NEd_N / fyd, 0.002 * Ac_mm2)
            As_max_mm2 = 0.04 * Ac_mm2

            # Required reinforcement
            target_N = abs_NEd_N
            if fyd > fcd:
                As_req_calc = (target_N - Ac_mm2 * fcd) / (fyd - fcd)
            else:
                As_req_calc = 0.0
            As_required_mm2 = max(As_req_calc, As_min_mm2)

            intermediate["fcd_MPa"] = round(fcd, 2)
            intermediate["fyd_MPa"] = round(fyd, 2)
            intermediate["net_concrete_Ac_mm2"] = round(net_Ac, 1)
            intermediate["NRd_kN"] = round(NRd_kN, 2)
            intermediate["As_min_mm2"] = round(As_min_mm2, 1)
            intermediate["As_max_mm2 (0.04 Ac)"] = round(As_max_mm2, 1)

            capacity_kN = NRd_kN
            demand_kN = NEd_kN
            dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0
            method = "Eurocode 2 Section Equilibrium NRd = Ac*fcd + As*fyd"

        else:
            clause = "EN 1992-1-1:2004 Clause 6.1 (Pure Tension)"
            NRd_N = As_provided_mm2 * fyd
            NRd_kN = NRd_N / 1000.0
            As_min_mm2 = 0.002 * Ac_mm2
            As_max_mm2 = 0.04 * Ac_mm2
            As_required_mm2 = abs_NEd_N / fyd

            intermediate["fyd_MPa"] = round(fyd, 2)
            intermediate["NRd_tension_kN"] = round(NRd_kN, 2)
            intermediate["As_min_mm2"] = round(As_min_mm2, 1)

            capacity_kN = NRd_kN
            demand_kN = abs(NEd_kN)
            dc_ratio = demand_kN / capacity_kN if capacity_kN > 0 else 999.0
            method = "Eurocode 2 Direct Tension in Reinforcement NRd = As*fyd"

        status = DesignStatus.PASS if (dc_ratio <= 1.0 and As_provided_mm2 >= As_min_mm2 * 0.99) else DesignStatus.FAIL

        reinf = ReinforcementResult(
            required_area_mm2=As_required_mm2,
            provided_area_mm2=As_provided_mm2,
            reinforcement_ratio=As_provided_mm2 / Ac_mm2 if Ac_mm2 > 0 else 0.0,
            min_area_mm2=As_min_mm2,
            max_area_mm2=As_max_mm2,
            bar_callout=f"{round(As_provided_mm2)} mm² provided"
        )

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_2.value,
            code_edition=CodeEdition.EN_1992_1_1_2004.value,
            clause=clause,
            inputs=inputs,
            method=method,
            intermediate_results=intermediate,
            final_result=f"Capacity NRd = {round(capacity_kN, 2)} kN",
            limit=f"Demand NEd = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC2 Axial check: Demand = {round(demand_kN, 1)} kN, Capacity = {round(capacity_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return DesignCheckResult(
            check_type=CheckType.AXIAL,
            member_type=member_type,
            demand=demand_kN,
            capacity=capacity_kN,
            dc_ratio=dc_ratio,
            status=status,
            trace=trace,
            reinforcement=reinf,
            units="kN",
            summary_message=summary
        )
