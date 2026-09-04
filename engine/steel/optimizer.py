"""
STRUCTURE-X ULTIMATE — STEEL SECTION OPTIMIZATION ENGINE
Performs automated structural cross-section selection and optimization based on:
1. STRENGTH: Optimal structural utilization (highest safe efficiency <= 1.0, minimizing over-design)
2. WEIGHT: Minimum steel tonnage (lowest linear mass kg/m passing all limit states)
3. COST: Minimum total installed cost ($) incorporating steel material price, fabrication complexity,
         and surface coating/fireproofing surface area costs.
"""

from typing import List, Dict, Any, Optional, Tuple
from .types import (
    DesignCode,
    DesignMethod,
    SteelMemberType,
    SteelSectionType,
    SteelCheckType,
    DesignStatus,
    OptimizationCriterion,
    OptimizedCandidate,
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


class SteelSectionOptimizer:
    """
    Automated optimization and selection engine for structural steel members.
    """

    def __init__(
        self,
        unit_steel_cost_usd_per_kg: float = 1.80,     # Raw steel supply price ($/kg)
        coating_cost_usd_per_m2: float = 12.00,        # Surface prep, painting & fireproofing ($/m^2)
        fabrication_base_usd_per_ton: float = 650.0,   # Cutting, drilling & welding base ($/ton)
    ):
        self.steel_price_kg = unit_steel_cost_usd_per_kg
        self.coating_price_m2 = coating_cost_usd_per_m2
        self.fab_price_ton = fabrication_base_usd_per_ton

    def evaluate_section(
        self,
        section: SteelSection,
        material: SteelMaterial,
        member_type: SteelMemberType,
        Pu_kN: float,
        Mux_kNm: float,
        Muy_kNm: float,
        Vu_x_kN: float,
        Vu_y_kN: float,
        Lx_mm: float,
        Ly_mm: float,
        Lb_mm: Optional[float] = None,
        Kx: float = 1.0,
        Ky: float = 1.0,
        Cb: float = 1.0,
        length_m: Optional[float] = None,
        code: DesignCode = DesignCode.AISC_360,
        method: DesignMethod = DesignMethod.LRFD,
    ) -> Tuple[SteelMemberDesignSummary, float, float]:
        """
        Runs all relevant limit state checks on the proposed candidate section and computes its cost.
        """
        if Lb_mm is None or Lb_mm <= 0:
            Lb_mm = Ly_mm

        if length_m is None or length_m <= 0:
            length_m = max(Lx_mm, Ly_mm) / 1000.0

        checks: List[SteelCheckResult] = []

        # 1. Axial Check (Tension or Compression + Buckling)
        if Pu_kN < -0.1:
            # Tension
            tens_res = TensionCheck.check_aisc_360_16(
                section=section,
                material=material,
                Pu_kN=abs(Pu_kN),
                L_mm=max(Lx_mm, Ly_mm),
                method=method
            )
            checks.append(tens_res)
        elif Pu_kN > 0.1:
            # Compression + Buckling
            comp_res = CompressionCheck.check_aisc_360_16(
                section=section,
                material=material,
                Pu_kN=Pu_kN,
                Lx_mm=Lx_mm,
                Ly_mm=Ly_mm,
                Kx=Kx,
                Ky=Ky,
                method=method
            )
            checks.append(comp_res)

        # 2. Major Axis Flexure & LTB Check
        flex_x = FlexureCheck.check_aisc_360_16_major(
            section=section,
            material=material,
            Mu_kNm=Mux_kNm,
            Lb_mm=Lb_mm,
            Cb=Cb,
            method=method
        )
        checks.append(flex_x)

        # 3. Minor Axis Flexure Check
        flex_y = FlexureCheck.check_aisc_360_16_minor(
            section=section,
            material=material,
            Mu_y_kNm=Muy_kNm,
            method=method
        )
        checks.append(flex_y)

        # 4. Major Shear Check (Web)
        shear_x = ShearCheck.check_aisc_360_16_major(
            section=section,
            material=material,
            Vu_kN=Vu_x_kN,
            method=method
        )
        checks.append(shear_x)

        # 5. Minor Shear Check (Flanges)
        shear_y = ShearCheck.check_aisc_360_16_minor(
            section=section,
            material=material,
            Vu_y_kN=Vu_y_kN,
            method=method
        )
        checks.append(shear_y)

        # 6. Combined Forces & P-M Interaction Check
        inter_res = InteractionCheck.check_aisc_360_16(
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
            method=method
        )
        checks.append(inter_res)

        # Determine governing check
        governing_check = max(checks, key=lambda c: c.dc_ratio)
        max_dc = governing_check.dc_ratio
        overall_status = DesignStatus.PASS if max_dc <= 1.0 else DesignStatus.FAIL

        total_weight_kg = section.weight_kg_m * length_m

        # Compute cost
        # Surface area = perimeter * length
        surface_m2 = (section.perimeter_mm / 1000.0) * length_m
        mat_cost = total_weight_kg * self.steel_price_kg
        coat_cost = surface_m2 * self.coating_price_m2
        fab_cost = (total_weight_kg / 1000.0) * self.fab_price_ton * section.fabrication_factor
        total_cost_usd = mat_cost + coat_cost + fab_cost

        summary = SteelMemberDesignSummary(
            member_id=f"OPT-{section.name}",
            section_name=section.name,
            member_type=member_type,
            checks=checks,
            governing_check=governing_check.check_type,
            max_dc_ratio=max_dc,
            overall_status=overall_status,
            weight_kg=total_weight_kg,
            critical_clause=governing_check.trace.clause
        )

        return summary, total_weight_kg, total_cost_usd

    def optimize(
        self,
        current_section: SteelSection,
        material: SteelMaterial,
        member_type: SteelMemberType,
        Pu_kN: float,
        Mux_kNm: float,
        Muy_kNm: float,
        Vu_x_kN: float,
        Vu_y_kN: float,
        Lx_mm: float,
        Ly_mm: float,
        Lb_mm: Optional[float] = None,
        Kx: float = 1.0,
        Ky: float = 1.0,
        Cb: float = 1.0,
        length_m: Optional[float] = None,
        criterion: OptimizationCriterion = OptimizationCriterion.WEIGHT,
        section_pool: Optional[List[SteelSection]] = None,
        target_max_dc: float = 1.00,
        target_min_dc: float = 0.50,
        code: DesignCode = DesignCode.AISC_360,
        method: DesignMethod = DesignMethod.LRFD,
    ) -> Dict[str, Any]:
        """
        Evaluates the catalog of candidate sections and selects the optimal profile according to:
        - STRENGTH: Optimal utilization (highest safe D/C <= 1.0)
        - WEIGHT: Minimum total mass (lowest kg/m among passing sections)
        - COST: Minimum total installed expense ($)
        """
        if section_pool is None or len(section_pool) == 0:
            # Default to all sections of same family or all wide flanges
            section_pool = SteelSectionDatabase.all_sections()

        if length_m is None or length_m <= 0:
            length_m = max(Lx_mm, Ly_mm) / 1000.0

        # Baseline evaluation with current section
        base_summary, base_wt, base_cost = self.evaluate_section(
            section=current_section,
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
            code=code,
            method=method
        )

        candidates: List[OptimizedCandidate] = []

        for sec in section_pool:
            summary, wt, cost = self.evaluate_section(
                section=sec,
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
                code=code,
                method=method
            )

            # Calculate savings vs baseline
            wt_savings = ((base_wt - wt) / base_wt * 100.0) if base_wt > 0 else 0.0
            cost_savings = ((base_cost - cost) / base_cost * 100.0) if base_cost > 0 else 0.0

            cand = OptimizedCandidate(
                section_name=sec.name,
                section_type=sec.section_type,
                weight_kg_m=sec.weight_kg_m,
                total_weight_kg=wt,
                estimated_cost_usd=cost,
                max_dc_ratio=summary.max_dc_ratio,
                governing_check=summary.governing_check,
                status=summary.overall_status,
                strength_efficiency=summary.max_dc_ratio,
                weight_savings_percent=wt_savings,
                cost_savings_percent=cost_savings,
                details={
                    "critical_clause": summary.critical_clause,
                    "depth_mm": sec.d,
                    "width_mm": sec.bf
                }
            )
            candidates.append(cand)

        # Filter strictly passing candidates (D/C <= target_max_dc)
        passing_candidates = [c for c in candidates if c.status == DesignStatus.PASS and c.max_dc_ratio <= target_max_dc]

        if not passing_candidates:
            # Fallback to candidate with minimum D/C if none strictly pass
            best_candidate = min(candidates, key=lambda c: c.max_dc_ratio)
            ranked = sorted(candidates, key=lambda c: c.max_dc_ratio)
        else:
            if criterion == OptimizationCriterion.WEIGHT:
                # Minimum linear mass / total weight
                ranked = sorted(passing_candidates, key=lambda c: c.total_weight_kg)
                best_candidate = ranked[0]
            elif criterion == OptimizationCriterion.COST:
                # Minimum total installed cost
                ranked = sorted(passing_candidates, key=lambda c: c.estimated_cost_usd)
                best_candidate = ranked[0]
            elif criterion == OptimizationCriterion.STRENGTH:
                # Highest safe structural efficiency (closest to target without exceeding)
                # Maximize max_dc_ratio <= target_max_dc
                ranked = sorted(passing_candidates, key=lambda c: -c.max_dc_ratio)
                best_candidate = ranked[0]
            else:
                ranked = sorted(passing_candidates, key=lambda c: c.total_weight_kg)
                best_candidate = ranked[0]

        return {
            "criterion": criterion.value,
            "baseline": {
                "section": current_section.name,
                "weight_kg": round(base_wt, 2),
                "cost_usd": round(base_cost, 2),
                "max_dc_ratio": round(base_summary.max_dc_ratio, 4),
                "governing_check": base_summary.governing_check.value,
                "status": base_summary.overall_status.value
            },
            "optimal_section": best_candidate.to_dict(),
            "top_candidates": [c.to_dict() for c in ranked[:5]],
            "total_candidates_evaluated": len(candidates),
            "passing_candidates_count": len(passing_candidates)
        }
