"""
STRUCTURE-X ULTIMATE — STEEL DESIGN ENGINE MASTER INTERFACE
Unified orchestrator for all structural steel design checks (Tension, Compression,
Flexure, Shear, Combined Forces, Buckling, Lateral Torsional Buckling, Interaction)
and automated Multi-Criteria Section Optimization (Strength, Weight, Cost).
"""

from typing import Dict, Any, List, Optional
from .types import (
    DesignCode,
    CodeEdition,
    DesignMethod,
    SteelMemberType,
    SteelCheckType,
    DesignStatus,
    OptimizationCriterion,
    SteelCheckResult,
    SteelMemberDesignSummary,
)
from .materials import SteelMaterial
from .sections import SteelSection, SteelSectionDatabase
from .tension_check import TensionCheck
from .compression_check import CompressionCheck
from .flexure_check import FlexureCheck
from .shear_check import ShearCheck
from .interaction_check import InteractionCheck
from .optimizer import SteelSectionOptimizer


class SteelDesignEngine:
    """
    Main structural steel design and verification engine.
    """

    def __init__(self, default_code: DesignCode = DesignCode.AISC_360, default_method: DesignMethod = DesignMethod.LRFD):
        self.default_code = default_code
        self.default_method = default_method
        self.optimizer = SteelSectionOptimizer()

    def check_member(
        self,
        member_id: str,
        section: SteelSection,
        material: SteelMaterial,
        member_type: SteelMemberType,
        Pu_kN: float,                    # Factored axial force (+ compression, - tension)
        Mux_kNm: float,                  # Factored major bending moment
        Muy_kNm: float = 0.0,            # Factored minor bending moment
        Vu_x_kN: float = 0.0,            # Factored major shear force
        Vu_y_kN: float = 0.0,            # Factored minor shear force
        Lx_mm: float = 3000.0,           # Unbraced length for major axis buckling
        Ly_mm: float = 3000.0,           # Unbraced length for minor axis buckling
        Lb_mm: Optional[float] = None,   # Unbraced length for LTB
        Kx: float = 1.0,
        Ky: float = 1.0,
        Cb: float = 1.0,
        length_m: Optional[float] = None,
        code: Optional[DesignCode] = None,
        method: Optional[DesignMethod] = None,
    ) -> SteelMemberDesignSummary:
        """
        Executes complete multi-limit-state verification on a structural steel member.
        """
        use_code = code or self.default_code
        use_method = method or self.default_method

        if Lb_mm is None or Lb_mm <= 0:
            Lb_mm = Ly_mm

        if length_m is None or length_m <= 0:
            length_m = max(Lx_mm, Ly_mm) / 1000.0

        checks: List[SteelCheckResult] = []

        if use_code == DesignCode.AISC_360:
            # 1. Axial Check (Tension or Compression)
            if Pu_kN < -0.01:
                t_res = TensionCheck.check_aisc_360_16(
                    section=section,
                    material=material,
                    Pu_kN=abs(Pu_kN),
                    L_mm=max(Lx_mm, Ly_mm),
                    method=use_method
                )
                checks.append(t_res)
            elif Pu_kN > 0.01:
                c_res = CompressionCheck.check_aisc_360_16(
                    section=section,
                    material=material,
                    Pu_kN=Pu_kN,
                    Lx_mm=Lx_mm,
                    Ly_mm=Ly_mm,
                    Kx=Kx,
                    Ky=Ky,
                    method=use_method
                )
                checks.append(c_res)

            # 2. Major Axis Flexure & LTB
            fx_res = FlexureCheck.check_aisc_360_16_major(
                section=section,
                material=material,
                Mu_kNm=Mux_kNm,
                Lb_mm=Lb_mm,
                Cb=Cb,
                method=use_method
            )
            checks.append(fx_res)

            # 3. Minor Axis Flexure
            fy_res = FlexureCheck.check_aisc_360_16_minor(
                section=section,
                material=material,
                Mu_y_kNm=Muy_kNm,
                method=use_method
            )
            checks.append(fy_res)

            # 4. Major Shear (Web)
            vx_res = ShearCheck.check_aisc_360_16_major(
                section=section,
                material=material,
                Vu_kN=Vu_x_kN,
                method=use_method
            )
            checks.append(vx_res)

            # 5. Minor Shear (Flange)
            vy_res = ShearCheck.check_aisc_360_16_minor(
                section=section,
                material=material,
                Vu_y_kN=Vu_y_kN,
                method=use_method
            )
            checks.append(vy_res)

            # 6. Combined Forces & Interaction
            int_res = InteractionCheck.check_aisc_360_16(
                section=section,
                material=material,
                Pu_kN=Pu_kN,
                Mux_kNm=Mux_kNm,
                Muy_kNm=Muy_kNm,
                Lx_mm=Lx_mm,
                Ly_mm=Ly_mm,
                Lb_mm=Lb_mm,
                Kx=Kx,
                Ky=Ky,
                Cb=Cb,
                method=use_method
            )
            checks.append(int_res)

        else:
            # Eurocode 3 Checks
            if Pu_kN < -0.01:
                t_res = TensionCheck.check_eurocode_3(
                    section=section,
                    material=material,
                    NEd_kN=abs(Pu_kN),
                    L_mm=max(Lx_mm, Ly_mm)
                )
                checks.append(t_res)
            elif Pu_kN > 0.01:
                c_res = CompressionCheck.check_eurocode_3(
                    section=section,
                    material=material,
                    NEd_kN=Pu_kN,
                    Lcr_y_mm=Lx_mm,
                    Lcr_z_mm=Ly_mm
                )
                checks.append(c_res)

            fl_res = FlexureCheck.check_eurocode_3(
                section=section,
                material=material,
                MEd_kNm=Mux_kNm,
                L_mm=Lb_mm,
                C1=Cb
            )
            checks.append(fl_res)

            sh_res = ShearCheck.check_eurocode_3(
                section=section,
                material=material,
                VEd_kN=Vu_x_kN
            )
            checks.append(sh_res)

            ec3_int = InteractionCheck.check_eurocode_3(
                section=section,
                material=material,
                NEd_kN=Pu_kN,
                My_Ed_kNm=Mux_kNm,
                Mz_Ed_kNm=Muy_kNm,
                Lcr_y_mm=Lx_mm,
                Lcr_z_mm=Ly_mm,
                L_ltb_mm=Lb_mm
            )
            checks.append(ec3_int)

        governing = max(checks, key=lambda c: c.dc_ratio)
        overall_status = DesignStatus.PASS if governing.dc_ratio <= 1.0 else DesignStatus.FAIL
        total_weight_kg = section.weight_kg_m * length_m

        return SteelMemberDesignSummary(
            member_id=member_id,
            section_name=section.name,
            member_type=member_type,
            checks=checks,
            governing_check=governing.check_type,
            max_dc_ratio=governing.dc_ratio,
            overall_status=overall_status,
            weight_kg=total_weight_kg,
            critical_clause=governing.trace.clause
        )

    def optimize_section(
        self,
        current_section: SteelSection,
        material: SteelMaterial,
        member_type: SteelMemberType,
        Pu_kN: float,
        Mux_kNm: float,
        Muy_kNm: float = 0.0,
        Vu_x_kN: float = 0.0,
        Vu_y_kN: float = 0.0,
        Lx_mm: float = 3000.0,
        Ly_mm: float = 3000.0,
        Lb_mm: Optional[float] = None,
        Kx: float = 1.0,
        Ky: float = 1.0,
        Cb: float = 1.0,
        length_m: Optional[float] = None,
        criterion: OptimizationCriterion = OptimizationCriterion.WEIGHT,
        section_pool: Optional[List[SteelSection]] = None,
        code: Optional[DesignCode] = None,
        method: Optional[DesignMethod] = None,
    ) -> Dict[str, Any]:
        """
        Runs automated section optimization based on Strength, Weight, or Cost.
        """
        use_code = code or self.default_code
        use_method = method or self.default_method

        return self.optimizer.optimize(
            current_section=current_section,
            material=material,
            member_type=member_type,
            Pu_kN=Pu_kN,
            Mux_kNm=Mux_kNm,
            Muy_kNm=Muy_kNm,
            Vu_x_kN=Vu_x_kN,
            Vu_y_kN=Vu_y_kN,
            Lx_mm=Lx_mm,
            Ly_mm=Ly_mm,
            Lb_mm=Lb_mm,
            Kx=Kx,
            Ky=Ky,
            Cb=Cb,
            length_m=length_m,
            criterion=criterion,
            section_pool=section_pool,
            code=use_code,
            method=use_method
        )
