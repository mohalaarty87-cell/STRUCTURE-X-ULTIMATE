"""
STRUCTURE-X ULTIMATE — STEEL COMPRESSION & BUCKLING CAPACITY CHECK
Evaluates flexural buckling (inelastic & elastic Euler), torsional/flexural-torsional buckling,
slenderness limits (KL/r <= 200), and slender-element reduction factors (Q).
Strictly complies with AISC 360-16 (Chapter E) and Eurocode 3 (EN 1993-1-1 Clause 6.3.1).
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
    SectionCompactness,
)
from .materials import SteelMaterial
from .sections import SteelSection


class CompressionCheck:
    """
    Modular structural steel compressive strength & buckling evaluator.
    """

    @staticmethod
    def check_aisc_360_16(
        section: SteelSection,
        material: SteelMaterial,
        Pu_kN: float,                    # Factored compression demand (kN)
        Lx_mm: float,                    # Unbraced length for buckling about X axis (mm)
        Ly_mm: float,                    # Unbraced length for buckling about Y axis (mm)
        Kx: float = 1.0,                 # Effective length factor about X
        Ky: float = 1.0,                 # Effective length factor about Y
        Lz_mm: Optional[float] = None,   # Unbraced length for torsional buckling (mm)
        Kz: float = 1.0,                 # Effective length factor for torsional buckling
        method: DesignMethod = DesignMethod.LRFD,
    ) -> SteelCheckResult:
        """
        AISC 360-16 Chapter E: Design of Members for Compression.
        Sections E1, E2, E3 (flexural buckling), E4 (torsional buckling), E7 (slender elements).
        """
        Ag = section.Ag
        Fy = material.Fy
        E = material.E
        G = material.G

        if Lz_mm is None or Lz_mm <= 0:
            Lz_mm = Ly_mm

        # 1. Slenderness ratios about major (X) and minor (Y) axes
        kl_r_x = (Kx * Lx_mm) / max(section.rx, 0.1)
        kl_r_y = (Ky * Ly_mm) / max(section.ry, 0.1)
        kl_r_max = max(kl_r_x, kl_r_y)
        slenderness_valid = kl_r_max <= 200.0  # AISC Section E2 recommendation

        # 2. Elastic critical flexural buckling stress Fe (Eq. E3-4)
        Fe_x = (math.pi ** 2 * E) / (kl_r_x ** 2) if kl_r_x > 0 else 1.0e6
        Fe_y = (math.pi ** 2 * E) / (kl_r_y ** 2) if kl_r_y > 0 else 1.0e6
        Fe_flexural = min(Fe_x, Fe_y)

        # 3. Torsional buckling stress Fe_z (Eq. E4-2) for doubly symmetric sections
        # Fe_z = [ (pi^2 * E * Cw) / (Kz*Lz)^2 + G*J ] * (1 / (Ix + Iy))
        if section.Ix > 0 and section.Iy > 0 and (section.Cw > 0 or section.J > 0):
            term_cw = (math.pi ** 2 * E * section.Cw) / ((Kz * Lz_mm) ** 2)
            term_gj = G * section.J
            Fe_torsional = (term_cw + term_gj) / (section.Ix + section.Iy)
        else:
            Fe_torsional = 1.0e9

        # Governing elastic buckling stress Fe
        if Fe_torsional < Fe_flexural:
            Fe = Fe_torsional
            buckling_mode = "Torsional Buckling (Eq. E4-2)"
        elif kl_r_x >= kl_r_y:
            Fe = Fe_x
            buckling_mode = "Major-Axis Flexural Buckling (X-X)"
        else:
            Fe = Fe_y
            buckling_mode = "Minor-Axis Flexural Buckling (Y-Y)"

        # 4. Check for slender elements (Section E7)
        compactness, comp_details = section.check_compression_compactness_aisc(material)
        if compactness == SectionCompactness.SLENDER:
            # Reduction factor Q
            # For slender unstiffened flanges: Qs per Section E7.1
            b_t = section.b_over_2tf
            sqrt_E_Fy = math.sqrt(E / Fy)
            if b_t <= 0.56 * sqrt_E_Fy:
                Qs = 1.0
            elif b_t < 1.03 * sqrt_E_Fy:
                Qs = 1.415 - 0.74 * b_t * math.sqrt(Fy / E)
            else:
                Qs = (0.69 * E) / (Fy * (b_t ** 2))
            Q = min(max(Qs, 0.4), 1.0)
            Fy_effective = Q * Fy
            slender_note = f"Slender element reduction Q = {round(Q, 3)}"
        else:
            Q = 1.0
            Fy_effective = Fy
            slender_note = "Non-slender (Q = 1.0)"

        # 5. Critical buckling stress Fcr (Section E3 / E7)
        # Limiting slenderness threshold: 4.71 * sqrt(E / Fy_eff)
        transition_slenderness = 4.71 * math.sqrt(E / Fy_effective)
        fy_over_fe = Fy_effective / Fe

        if kl_r_max <= transition_slenderness and fy_over_fe <= 2.25:
            # Inelastic buckling (Eq. E3-2)
            Fcr = (0.658 ** fy_over_fe) * Fy_effective
            buckling_regime = "Inelastic Buckling (Eq. E3-2)"
        else:
            # Elastic Euler buckling (Eq. E3-3)
            Fcr = 0.877 * Fe
            Fcr = min(Fcr, Fy_effective)
            buckling_regime = "Elastic Euler Buckling (Eq. E3-3)"

        # 6. Nominal compressive strength Pn (Eq. E3-1)
        Pn_N = Fcr * Ag
        Pn_kN = Pn_N / 1000.0

        if method == DesignMethod.LRFD:
            phi_c = 0.90
            available_Pn_kN = phi_c * Pn_kN
            factor_label = "phi = 0.90 (LRFD)"
        else:
            omega_c = 1.67
            available_Pn_kN = Pn_kN / omega_c
            factor_label = "Omega = 1.67 (ASD)"

        demand_kN = abs(Pu_kN)
        dc_ratio = demand_kN / available_Pn_kN if available_Pn_kN > 0 else 999.0
        status = DesignStatus.PASS if (dc_ratio <= 1.0 and slenderness_valid) else DesignStatus.FAIL

        governing_limit_state = f"{buckling_mode} ({buckling_regime})"

        inputs: Dict[str, Any] = {
            "Pu_kN": Pu_kN,
            "section": section.name,
            "Ag_mm2": Ag,
            "Fy_MPa": Fy,
            "E_MPa": E,
            "Lx_mm": Lx_mm,
            "Ly_mm": Ly_mm,
            "Kx": Kx,
            "Ky": Ky,
            "method": method.value
        }

        intermediate: Dict[str, Any] = {
            "KL_r_x": round(kl_r_x, 2),
            "KL_r_y": round(kl_r_y, 2),
            "KL_r_governing": round(kl_r_max, 2),
            "slenderness_limit": 200.0,
            "slenderness_pass": slenderness_valid,
            "Fe_x_MPa": round(Fe_x, 2),
            "Fe_y_MPa": round(Fe_y, 2),
            "Fe_torsional_MPa": round(Fe_torsional, 2) if Fe_torsional < 1.0e8 else "N/A",
            "Fe_governing_MPa": round(Fe, 2),
            "transition_slenderness": round(transition_slenderness, 2),
            "Fcr_critical_MPa": round(Fcr, 2),
            "Pn_nominal_kN": round(Pn_kN, 2),
            "available_strength_kN": round(available_Pn_kN, 2),
            "design_factor": factor_label,
            "buckling_mode": buckling_mode,
            "buckling_regime": buckling_regime,
            "slender_reduction": slender_note
        }

        trace = CalculationTrace(
            design_code=DesignCode.AISC_360.value,
            code_edition=CodeEdition.AISC_360_16.value,
            clause="AISC 360-16 Sections E1, E2, E3, E4, E7",
            inputs=inputs,
            method=f"AISC {method.value} Column Compressive Strength & Column Curve (Fcr * Ag)",
            intermediate_results=intermediate,
            final_result=f"Compressive Capacity = {round(available_Pn_kN, 2)} kN ({governing_limit_state})",
            limit=f"Compression Demand Pu = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"Compression check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(available_Pn_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.COMPRESSION,
            demand=demand_kN,
            capacity=available_Pn_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=governing_limit_state,
            trace=trace,
            units="kN",
            summary_message=summary
        )

    @staticmethod
    def check_eurocode_3(
        section: SteelSection,
        material: SteelMaterial,
        NEd_kN: float,                   # Design axial compression force (kN)
        Lcr_y_mm: float,                  # Buckling length about y axis (mm)
        Lcr_z_mm: float,                  # Buckling length about z axis (mm)
        buckling_curve: str = "b",        # 'a0', 'a', 'b', 'c', 'd'
        gamma_M0: float = 1.0,
        gamma_M1: float = 1.0,
    ) -> SteelCheckResult:
        """
        Eurocode 3 (EN 1993-1-1:2005) Clause 6.3.1: Flexural Buckling of Columns.
        """
        A = section.Ag
        fy = material.Fy
        E = material.E

        # Cross-section plastic resistance (Eq. 6.10)
        Nc_Rd_N = (A * fy) / gamma_M0
        Nc_Rd_kN = Nc_Rd_N / 1000.0

        # Euler critical forces about y and z
        # Ncr = pi^2 * E * I / Lcr^2
        Ncr_y_N = (math.pi ** 2 * E * section.Ix) / (Lcr_y_mm ** 2) if Lcr_y_mm > 0 else 1.0e12
        Ncr_z_N = (math.pi ** 2 * E * section.Iy) / (Lcr_z_mm ** 2) if Lcr_z_mm > 0 else 1.0e12
        Ncr_N = min(Ncr_y_N, Ncr_z_N)

        # Non-dimensional slenderness (Eq. 6.49)
        lambda_bar = math.sqrt((A * fy) / Ncr_N)

        # Imperfection factor alpha from Table 6.1
        alpha_map = {"a0": 0.13, "a": 0.21, "b": 0.34, "c": 0.49, "d": 0.76}
        alpha = alpha_map.get(buckling_curve.lower(), 0.34)

        # Value of phi (Eq. 6.49)
        phi_val = 0.5 * (1.0 + alpha * (lambda_bar - 0.2) + lambda_bar ** 2)

        # Reduction factor chi (Eq. 6.49)
        disc = phi_val ** 2 - lambda_bar ** 2
        if disc >= 0.0:
            chi = 1.0 / (phi_val + math.sqrt(disc))
        else:
            chi = 1.0 / phi_val
        chi = min(1.0, max(0.05, chi))

        # Design buckling resistance Nb,Rd (Eq. 6.47)
        Nb_Rd_N = (chi * A * fy) / gamma_M1
        Nb_Rd_kN = Nb_Rd_N / 1000.0

        demand_kN = abs(NEd_kN)
        dc_ratio = demand_kN / Nb_Rd_kN if Nb_Rd_kN > 0 else 999.0
        status = DesignStatus.PASS if dc_ratio <= 1.0 else DesignStatus.FAIL

        governing_axis = "Minor Axis (z-z)" if Ncr_z_N <= Ncr_y_N else "Major Axis (y-y)"

        inputs: Dict[str, Any] = {
            "NEd_kN": NEd_kN,
            "section": section.name,
            "A_mm2": A,
            "fy_MPa": fy,
            "E_MPa": E,
            "Lcr_y_mm": Lcr_y_mm,
            "Lcr_z_mm": Lcr_z_mm,
            "buckling_curve": buckling_curve
        }

        intermediate: Dict[str, Any] = {
            "Nc_Rd_kN": round(Nc_Rd_kN, 2),
            "Ncr_y_kN": round(Ncr_y_N / 1000.0, 2),
            "Ncr_z_kN": round(Ncr_z_N / 1000.0, 2),
            "lambda_bar": round(lambda_bar, 3),
            "alpha_imperfection": alpha,
            "chi_reduction_factor": round(chi, 4),
            "Nb_Rd_kN": round(Nb_Rd_kN, 2),
            "governing_axis": governing_axis
        }

        trace = CalculationTrace(
            design_code=DesignCode.EUROCODE_3.value,
            code_edition=CodeEdition.EN_1993_1_1_2005.value,
            clause="EN 1993-1-1:2005 Clause 6.3.1 (Eq. 6.47 - 6.49)",
            inputs=inputs,
            method="EC3 Column Buckling Reduction Factor chi Curve Method",
            intermediate_results=intermediate,
            final_result=f"Capacity Nb,Rd = {round(Nb_Rd_kN, 2)} kN ({governing_axis})",
            limit=f"Demand NEd = {round(demand_kN, 2)} kN (D/C = {round(dc_ratio, 4)})",
            status=status
        )

        summary = f"EC3 Compression check ({section.name}): Demand = {round(demand_kN, 1)} kN, Capacity = {round(Nb_Rd_kN, 1)} kN, D/C = {round(dc_ratio, 3)} [{status.value}]"

        return SteelCheckResult(
            check_type=SteelCheckType.COMPRESSION,
            demand=demand_kN,
            capacity=Nb_Rd_kN,
            dc_ratio=dc_ratio,
            status=status,
            governing_limit_state=f"EC3 Flexural Buckling {governing_axis} (Curve {buckling_curve})",
            trace=trace,
            units="kN",
            summary_message=summary
        )
