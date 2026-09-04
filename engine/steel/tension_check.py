"""
STRUCTURE-X ULTIMATE — STEEL TENSION CAPACITY & DESIGN CHECK
Evaluates gross section yielding, net section fracture/rupture, shear lag factor U,
and maximum slenderness ratio L/r <= 300.
Strictly complies with AISC 360-16 (Chapter D) and Eurocode 3 (EN 1993-1-1 Clause 6.2.3).
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


class TensionCheck:
    """
    Modular structural steel tensile strength evaluator.
    """

    @staticmethod
    def check_aisc_360_16(
        section: SteelSection,
        material: SteelMaterial,
        Pu_kN: float,                    # Factored tension demand (kN)
        L_mm: float,                      # Unbraced length of member (mm)
        net_area_ratio: float = 0.85,     # An / Ag ratio (1.0 for welded, ~0.85 for bolted)
        U_shear_lag: float = 0.90,        # Shear lag factor U (AISC Table D3.1)
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Chapter D: Design of Members for Tension.
        Sections D1 (slenderness), D2 (yielding and rupture), D3 (effective net area).
        """
        Ag = section.Ag
        Fy = material.Fy
        Fu = material.Fu
        r_min = min(section.rx, section.ry) if (section.rx > 0 and section.ry > 0) else max(section.rx, section.ry, 1.0)

        # 1. Gross section yielding (Eq. D2-1)
        Pn_yield_N = Fy * Ag
        Pn_yield_kN = Pn_yield_N / 1000.0

        if method == DesignMethod.LRFD:
            phi_yield = 0.90
            phi_Pn_yield_kN = phi_yield * Pn_yield_kN
        else:
            omega_yield = 1.67
            phi_Pn_yield_kN = Pn_yield_kN / omega_yield

        # 2. Net section rupture (Eq. D2-2)
        An = Ag * net_area_ratio
        Ae = An * U_shear_lag
        Pn_rupture_N = Fu * Ae
        Pn_rupture_kN = Pn_rupture_N / 1000.0

        if method == DesignMethod.LRFD:
            phi_rupture = 0.75
            phi_Pn_rupture_kN = phi_rupture * Pn_rupture_kN
        else:
            omega_rupture = 2.00
            phi_Pn_rupture_kN = Pn_rupture_kN / omega_rupture

        # Governing tensile capacity
        if phi_Pn_yield_kN <= phi_Pn_rupture_kN:
            governing_capacity_kN = phi_Pn_yield_kN
            governing_state = "Tensile Yielding in Gross Section (D2-1)"
        else:
            governing_capacity_kN = phi_Pn_rupture_kN
            governing_state = "Tensile Rupture in Net Section (D2-2)"

        # 3. Slenderness limitation (Section D1: L/r <= 300)
        slenderness = L_mm / r_min if r_min > 0 else 0.0
        slenderness_pass = slenderness <= 300.0

        demand_kN = abs(Pu_kN)
        dc_ratio = demand_kN / governing_capacity_kN if governing_capacity_kN > 0 else 999.0
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and slenderness_pass) else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "Pu_kN": Pu_kN,
            "section": section.name,
            "Ag_mm2": Ag,
            "Fy_MPa": Fy,
            "Fu_MPa": Fu,
            "L_mm": L_mm,
            "r_min_mm": round(r_min, 1),
            "net_area_ratio": net_area_ratio,
            "U_shear_lag": U_shear_lag,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "Pn_yield_nominal_kN": round(Pn_yield_kN, 2),
            "available_yield_kN": round(phi_Pn_yield_kN, 2),
            "An_net_area_mm2": round(An, 1),
            "Ae_effective_area_mm2": round(Ae, 1),
            "Pn_rupture_nominal_kN": round(Pn_rupture_kN, 2),
            "available_rupture_kN": round(phi_Pn_rupture_kN, 2),
            "slenderness_L_over_r": round(slenderness, 1),
            "slenderness_limit": 300.0,
            "slenderness_pass": slenderness_pass,
            "governing_state": governing_state
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Sections D1, D2, D3",
            inputs=inputs,
            method=f"AISC {method.value} Tension Member Strength (Yielding Pn=Fy*Ag, Rupture Pn=Fu*Ae)",
            intermediate_results=intermediate,
            final_result=f"Tensile Capacity = {round(governing_capacity_kN, 2)} kN ({governing_state})",
            limit=f"Tension Demand Pu = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Tension check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(governing_capacity_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.TENSION,
            demand=demand_kN,
            capacity=governing_capacity_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=governing_state,
            trace=trace,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_3(
        section: SteelSection,
        material: SteelMaterial,
        NEd_kN: float,                   # Design tensile force (kN)
        L_mm: float,                      # Member length (mm)
        net_area_ratio: float = 0.85,
        gamma_M0: float = 1.0,
        gamma_M2: float = 1.25,
    ) -> SteelCheckResult:
        """
        Eurocode 3 (EN 1993-1-1:2005) Clause 6.2.3: Tension.
        """
        A = section.Ag
        A_net = A * net_area_ratio
        fy = material.Fy
        fu = material.Fu

        # Plastic resistance of gross section (Eq. 6.6)
        Npl_Rd_N = (A * fy) / gamma_M0
        Npl_Rd_kN = Npl_Rd_N / 1000.0

        # Ultimate resistance of net section (Eq. 6.7)
        Nu_Rd_N = (0.9 * A_net * fu) / gamma_M2
        Nu_Rd_kN = Nu_Rd_N / 1000.0

        if Npl_Rd_kN <= Nu_Rd_kN:
            Nt_Rd_kN = Npl_Rd_kN
            governing_state = "Gross Plastic Yielding Npl,Rd (Eq. 6.6)"
        else:
            Nt_Rd_kN = Nu_Rd_kN
            governing_state = "Net Ultimate Rupture Nu,Rd (Eq. 6.7)"

        r_min = min(section.rx, section.ry) if (section.rx > 0 and section.ry > 0) else max(section.rx, section.ry, 1.0)
        slenderness = L_mm / r_min

        demand_kN = abs(NEd_kN)
        dc_ratio = demand_kN / Nt_Rd_kN if Nt_Rd_kN > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        inputs: Dict[str, Any] = {
            "NEd_kN": NEd_kN,
            "section": section.name,
            "A_mm2": A,
            "fy_MPa": fy,
            "fu_MPa": fu,
            "gamma_M0": gamma_M0,
            "gamma_M2": gamma_M2
        }

        intermediate: Dict[str, Any] = {
            "Npl_Rd_kN": round(Npl_Rd_kN, 2),
            "Nu_Rd_kN": round(Nu_Rd_kN, 2),
            "slenderness": round(slenderness, 1),
            "governing_state": governing_state
        }

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_3.value,
            code_edition=CodeEdition.EN_1993_1_1_2005.value,
            clause="EN 1993-1-1:2005 Clause 6.2.3",
            inputs=inputs,
            method="EC3 Design Tension Resistance Nt,Rd = min(Npl,Rd, Nu,Rd)",
            intermediate_results=intermediate,
            final_result=f"Capacity Nt,Rd = {round(Nt_Rd_kN, 2)} kN",
            limit=f"Demand NEd = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC3 Tension check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(Nt_Rd_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.TENSION,
            demand=demand_kN,
            capacity=Nt_Rd_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=governing_state,
            trace=trace,
            units="kN",
            summary_message=summary
        )
