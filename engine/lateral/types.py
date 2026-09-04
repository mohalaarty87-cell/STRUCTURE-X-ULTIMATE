"""
STRUCTURE-X ULTIMATE — SEISMIC AND WIND ENGINE TYPES
Data structures, enums, calculation traces, and results for structural lateral load analysis
strictly complying with ASCE 7 (7-16/7-22), IBC (2024/2021/2018), Eurocode 8 (EN 1998-1:2004),
UBC 1997, and the Custom Code Framework.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class LateralCode(str, Enum):
    ASCE_7 = "ASCE 7"
    IBC = "IBC"
    EUROCODE_8 = "Eurocode 8"
    UBC = "UBC 1997"
    CUSTOM = "Custom Code"


class CodeEdition(str, Enum):
    ASCE_7_16 = "ASCE 7-16"
    ASCE_7_22 = "ASCE 7-22"
    IBC_2024 = "IBC 2024"
    IBC_2021 = "IBC 2021"
    IBC_2018 = "IBC 2018"
    EN_1998_1_2004 = "EN 1998-1:2004"
    EN_1991_1_4_2005 = "EN 1991-1-4:2005"
    UBC_1997 = "UBC 1997"
    CUSTOM_EDITION = "Custom Edition"


class LateralLoadType(str, Enum):
    SEISMIC = "Seismic"
    WIND = "Wind"


class DesignStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class SiteClass(str, Enum):
    """ASCE 7 / IBC Site Classes."""
    A = "Site Class A (Hard Rock)"
    B = "Site Class B (Rock)"
    C = "Site Class C (Very Dense Soil / Soft Rock)"
    D = "Site Class D (Stiff Soil - Default)"
    E = "Site Class E (Soft Clay)"
    F = "Site Class F (Requires Site Response Analysis)"


class GroundTypeEC8(str, Enum):
    """Eurocode 8 Ground Types."""
    A = "Ground Type A (Rock/Hard Rock)"
    B = "Ground Type B (Very Dense Sand/Gravel)"
    C = "Ground Type C (Deep Dense Sand/Gravel)"
    D = "Ground Type D (Soft-to-Medium Cohesive Soil)"
    E = "Ground Type E (Alluvial Soil Surface Layer)"


class SoilProfileUBC(str, Enum):
    """UBC 1997 Soil Profile Types."""
    SA = "SA (Hard Rock)"
    SB = "SB (Rock)"
    SC = "SC (Very Dense Soil and Soft Rock)"
    SD = "SD (Stiff Soil Profile)"
    SE = "SE (Soft Soil Profile)"
    SF = "SF (Soil Requiring Site-Specific Evaluation)"


class RiskCategory(str, Enum):
    I = "Risk Category I"
    II = "Risk Category II (Standard Occupancy)"
    III = "Risk Category III (Substantial Hazard / High Occupancy)"
    IV = "Risk Category IV (Essential Facilities / Hospitals / Police)"


class SeismicDesignCategory(str, Enum):
    A = "SDC A"
    B = "SDC B"
    C = "SDC C"
    D = "SDC D"
    E = "SDC E"
    F = "SDC F"


class ExposureCategory(str, Enum):
    """ASCE 7 / IBC Wind Exposure Categories."""
    B = "Exposure B (Urban, Suburban, Wooded Areas)"
    C = "Exposure C (Open Terrain with Scattered Obstructions)"
    D = "Exposure D (Flat, Unobstructed Coastal Areas)"


class TerrainCategoryEC1(str, Enum):
    """Eurocode 1 Wind Terrain Categories."""
    ZERO = "Terrain 0 (Sea or Coastal Area)"
    I = "Terrain I (Lakes, Flat Area Negligible Vegetation)"
    II = "Terrain II (Low Vegetation and Isolated Obstacles)"
    III = "Terrain III (Suburban/Industrial Area, Regular Forest)"
    IV = "Terrain IV (Urban Areas, >=15% Surface Covered with H>15m)"


@dataclass
class CalculationTrace:
    """
    Exposes mandatory traceability fields required for professional engineering review:
    - Code
    - Edition
    - Provision / Clause
    - Inputs
    - Result
    """
    design_code: str
    code_edition: str
    clause: str
    inputs: Dict[str, Any]
    method: str
    intermediate_results: Dict[str, Any]
    final_result: Any
    limit: Any
    status: DesignStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_code": self.design_code,
            "code_edition": self.code_edition,
            "clause": self.clause,
            "inputs": self.inputs,
            "method": self.method,
            "intermediate_results": self.intermediate_results,
            "final_result": self.final_result,
            "limit": self.limit,
            "status": self.status.value if isinstance(self.status, DesignStatus) else self.status
        }


@dataclass
class StoryLevel:
    """
    Defines a geometric story level in the multi-story structure.
    """
    level_index: int                 # 1 for bottom story, n for roof
    name: str                        # e.g., "Level 1", "Roof"
    height_from_base_m: float        # Elevation from ground/base (m) (hx)
    story_height_m: float            # Story height to level below (m) (hsx)
    weight_kN: float                 # Tributary seismic gravity weight (wx)
    width_m: float                   # Building face width exposed to wind (B)
    depth_m: float                   # Building depth parallel to wind (L)
    lateral_stiffness_kN_per_mm: float = 50.0  # Lateral frame/wall story shear stiffness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "name": self.name,
            "height_from_base_m": self.height_from_base_m,
            "story_height_m": self.story_height_m,
            "weight_kN": self.weight_kN,
            "width_m": self.width_m,
            "depth_m": self.depth_m,
            "lateral_stiffness_kN_per_mm": self.lateral_stiffness_kN_per_mm
        }


@dataclass
class SeismicParameters:
    """
    Unified Seismic Design Parameters container supporting ASCE 7, IBC, EC8, UBC, and Custom.
    """
    site_class: SiteClass = SiteClass.D
    Ss: float = 1.00                 # Mapped short-period spectral acceleration (g)
    S1: float = 0.40                 # Mapped 1-second spectral acceleration (g)
    Fa: float = 1.10                 # Short-period site coefficient
    Fv: float = 1.90                 # 1-second site coefficient
    SMS: float = 1.10                # Site-adjusted short-period spectral acceleration
    SM1: float = 0.76                # Site-adjusted 1-second spectral acceleration
    SDS: float = 0.733               # Design short-period spectral acceleration (2/3 * SMS)
    SD1: float = 0.507               # Design 1-second spectral acceleration (2/3 * SM1)
    R: float = 8.0                   # Response modification coefficient
    importance_factor: float = 1.00  # Seismic importance factor (Ie)
    Cd: float = 5.5                  # Deflection amplification factor
    Omega0: float = 3.0              # Overstrength factor
    TL: float = 8.0                  # Long-period transition period (s)
    risk_category: RiskCategory = RiskCategory.II
    sdc: SeismicDesignCategory = SeismicDesignCategory.D
    # Eurocode 8 specifics
    ground_type_ec8: GroundTypeEC8 = GroundTypeEC8.C
    ag_design: float = 0.25          # Design ground acceleration (g)
    q_behavior_factor: float = 4.0   # EC8 behavior factor q
    # UBC 1997 specifics
    soil_profile_ubc: SoilProfileUBC = SoilProfileUBC.SD
    seismic_zone_ubc: float = 4.0    # Zone 1, 2A, 2B, 3, 4
    Z_factor_ubc: float = 0.40       # Seismic zone factor Z
    Ca_ubc: float = 0.44             # Seismic coefficient Ca
    Cv_ubc: float = 0.64             # Seismic coefficient Cv
    Na_ubc: float = 1.0              # Near source factor Na
    Nv_ubc: float = 1.0              # Near source factor Nv

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_class": self.site_class.value if isinstance(self.site_class, SiteClass) else self.site_class,
            "Ss": self.Ss,
            "S1": self.S1,
            "Fa": round(self.Fa, 3),
            "Fv": round(self.Fv, 3),
            "SMS": round(self.SMS, 3),
            "SM1": round(self.SM1, 3),
            "SDS": round(self.SDS, 3),
            "SD1": round(self.SD1, 3),
            "R": self.R,
            "importance_factor": self.importance_factor,
            "Cd": self.Cd,
            "Omega0": self.Omega0,
            "TL": self.TL,
            "risk_category": self.risk_category.value if isinstance(self.risk_category, RiskCategory) else self.risk_category,
            "sdc": self.sdc.value if isinstance(self.sdc, SeismicDesignCategory) else self.sdc,
            "ground_type_ec8": self.ground_type_ec8.value if isinstance(self.ground_type_ec8, GroundTypeEC8) else self.ground_type_ec8,
            "ag_design": self.ag_design,
            "q_behavior_factor": self.q_behavior_factor,
            "soil_profile_ubc": self.soil_profile_ubc.value if isinstance(self.soil_profile_ubc, SoilProfileUBC) else self.soil_profile_ubc,
            "seismic_zone_ubc": self.seismic_zone_ubc,
            "Z_factor_ubc": self.Z_factor_ubc,
            "Ca_ubc": self.Ca_ubc,
            "Cv_ubc": self.Cv_ubc,
        }


@dataclass
class WindParameters:
    """
    Unified Wind Design Parameters container supporting ASCE 7, IBC, Eurocode 1, UBC, and Custom.
    """
    basic_wind_speed_mps: float = 45.0  # Basic wind speed V (m/s) (~100 mph = 44.7 m/s, ~115 mph = 51.4 m/s)
    exposure_category: ExposureCategory = ExposureCategory.C
    risk_category: RiskCategory = RiskCategory.II
    importance_factor_Iw: float = 1.00   # Wind importance factor
    Kd_directionality: float = 0.85      # Wind directionality factor (ASCE 7 Table 26.6-1)
    Kzt_topographic: float = 1.00        # Topographic factor (ASCE 7 Section 26.8)
    Ke_elevation: float = 1.00           # Ground elevation factor (ASCE 7 Section 26.9)
    G_gust_factor: float = 0.85          # Gust-effect factor (ASCE 7 Section 26.11)
    Cp_windward: float = 0.80            # Windward wall external pressure coefficient
    Cp_leeward: float = -0.50            # Leeward wall external pressure coefficient
    GCpi_internal: float = 0.18          # Internal pressure coefficient (+/- 0.18 for enclosed)
    # Eurocode 1 specifics
    terrain_category_ec1: TerrainCategoryEC1 = TerrainCategoryEC1.II
    air_density_kg_m3: float = 1.225     # Standard air density
    cs_cd_structural_factor: float = 1.0 # EC1 structural factor
    # UBC 1997 specifics
    Cq_ubc: float = 0.80                 # UBC wind pressure coefficient
    qs_ubc_N_per_m2: float = 980.0       # UBC basic wind stagnation pressure

    def to_dict(self) -> Dict[str, Any]:
        return {
            "basic_wind_speed_mps": self.basic_wind_speed_mps,
            "basic_wind_speed_mph": round(self.basic_wind_speed_mps * 2.23694, 1),
            "exposure_category": self.exposure_category.value if isinstance(self.exposure_category, ExposureCategory) else self.exposure_category,
            "risk_category": self.risk_category.value if isinstance(self.risk_category, RiskCategory) else self.risk_category,
            "importance_factor_Iw": self.importance_factor_Iw,
            "Kd_directionality": self.Kd_directionality,
            "Kzt_topographic": self.Kzt_topographic,
            "Ke_elevation": self.Ke_elevation,
            "G_gust_factor": self.G_gust_factor,
            "Cp_windward": self.Cp_windward,
            "Cp_leeward": self.Cp_leeward,
            "GCpi_internal": self.GCpi_internal,
        }


@dataclass
class StorySeismicResult:
    """
    Seismic forces, story shears, overturning moments, and drifts at an individual story level.
    """
    level_index: int
    name: str
    height_from_base_m: float
    story_height_m: float
    weight_kN: float
    Cvx_distribution_factor: float
    story_force_Fx_kN: float             # Lateral seismic force at this level (kN)
    story_shear_Vx_kN: float             # Total design shear force below this level (kN)
    story_overturning_Mx_kNm: float      # Cumulative overturning moment at this level (kN*m)
    elastic_displacement_dxe_mm: float   # First-order elastic deflection (mm)
    design_displacement_dx_mm: float     # Amplified inelastic deflection (Cd * dxe / Ie) (mm)
    story_drift_delta_mm: float          # Interstory design drift (mm)
    allowable_drift_delta_a_mm: float    # Code maximum allowable story drift (mm)
    drift_ratio: float                   # delta / hsx
    allowable_drift_ratio: float         # delta_a / hsx
    stability_coefficient_theta: float   # P-Delta stability coefficient
    drift_status: DesignStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "name": self.name,
            "height_from_base_m": self.height_from_base_m,
            "story_height_m": self.story_height_m,
            "weight_kN": round(self.weight_kN, 1),
            "Cvx_distribution_factor": round(self.Cvx_distribution_factor, 5),
            "story_force_Fx_kN": round(self.story_force_Fx_kN, 2),
            "story_shear_Vx_kN": round(self.story_shear_Vx_kN, 2),
            "story_overturning_Mx_kNm": round(self.story_overturning_Mx_kNm, 2),
            "elastic_displacement_dxe_mm": round(self.elastic_displacement_dxe_mm, 2),
            "design_displacement_dx_mm": round(self.design_displacement_dx_mm, 2),
            "story_drift_delta_mm": round(self.story_drift_delta_mm, 2),
            "allowable_drift_delta_a_mm": round(self.allowable_drift_delta_a_mm, 2),
            "drift_ratio": round(self.drift_ratio, 5),
            "allowable_drift_ratio": round(self.allowable_drift_ratio, 5),
            "stability_coefficient_theta": round(self.stability_coefficient_theta, 4),
            "drift_status": self.drift_status.value if isinstance(self.drift_status, DesignStatus) else self.drift_status
        }


@dataclass
class StoryWindResult:
    """
    Wind pressures, story forces, shears, overturning moments, and drifts at an individual level.
    """
    level_index: int
    name: str
    height_from_base_m: float
    story_height_m: float
    tributary_height_m: float
    width_m: float
    tributary_area_m2: float
    Kz_exposure_coeff: float
    velocity_pressure_qz_N_m2: float     # Velocity pressure at level (N/m2)
    windward_pressure_p_N_m2: float      # Net design pressure (N/m2)
    leeward_pressure_p_N_m2: float       # Leeward suction pressure (N/m2)
    net_design_pressure_N_m2: float      # Total combined horizontal pressure (N/m2)
    story_wind_force_Fw_kN: float        # Lateral wind force at this level (kN)
    story_wind_shear_Vw_kN: float        # Cumulative shear at this story (kN)
    story_overturning_Mw_kNm: float      # Overturning moment at this level (kN*m)
    lateral_displacement_mm: float       # Lateral displacement (mm)
    story_drift_mm: float                # Interstory drift (mm)
    drift_ratio: float                   # delta / hsx
    allowable_drift_ratio: float         # Serviceability limit (e.g. H/400 = 0.0025)
    drift_status: DesignStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "name": self.name,
            "height_from_base_m": self.height_from_base_m,
            "story_height_m": self.story_height_m,
            "tributary_height_m": round(self.tributary_height_m, 2),
            "width_m": self.width_m,
            "tributary_area_m2": round(self.tributary_area_m2, 1),
            "Kz_exposure_coeff": round(self.Kz_exposure_coeff, 3),
            "velocity_pressure_qz_N_m2": round(self.velocity_pressure_qz_N_m2, 1),
            "windward_pressure_p_N_m2": round(self.windward_pressure_p_N_m2, 1),
            "leeward_pressure_p_N_m2": round(self.leeward_pressure_p_N_m2, 1),
            "net_design_pressure_N_m2": round(self.net_design_pressure_N_m2, 1),
            "story_wind_force_Fw_kN": round(self.story_wind_force_Fw_kN, 2),
            "story_wind_shear_Vw_kN": round(self.story_wind_shear_Vw_kN, 2),
            "story_overturning_Mw_kNm": round(self.story_overturning_Mw_kNm, 2),
            "lateral_displacement_mm": round(self.lateral_displacement_mm, 2),
            "story_drift_mm": round(self.story_drift_mm, 2),
            "drift_ratio": round(self.drift_ratio, 5),
            "allowable_drift_ratio": round(self.allowable_drift_ratio, 5),
            "drift_status": self.drift_status.value if isinstance(self.drift_status, DesignStatus) else self.drift_status
        }


@dataclass
class SeismicAnalysisResult:
    """
    Complete seismic response calculation result package.
    """
    code: LateralCode
    edition: CodeEdition
    parameters: SeismicParameters
    fundamental_period_T_s: float
    period_upper_limit_T_max_s: float
    governing_period_s: float
    total_effective_weight_W_kN: float
    seismic_response_coeff_Cs: float
    Cs_governing_formula: str
    base_shear_V_kN: float
    base_overturning_moment_M0_kNm: float
    story_results: List[StorySeismicResult]
    max_drift_ratio: float
    max_drift_story: str
    max_stability_coefficient_theta: float
    overall_drift_status: DesignStatus
    trace: CalculationTrace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "edition": self.edition.value,
            "parameters": self.parameters.to_dict(),
            "fundamental_period_T_s": round(self.fundamental_period_T_s, 3),
            "period_upper_limit_T_max_s": round(self.period_upper_limit_T_max_s, 3),
            "governing_period_s": round(self.governing_period_s, 3),
            "total_effective_weight_W_kN": round(self.total_effective_weight_W_kN, 1),
            "seismic_response_coeff_Cs": round(self.seismic_response_coeff_Cs, 5),
            "Cs_governing_formula": self.Cs_governing_formula,
            "base_shear_V_kN": round(self.base_shear_V_kN, 2),
            "base_overturning_moment_M0_kNm": round(self.base_overturning_moment_M0_kNm, 2),
            "max_drift_ratio": round(self.max_drift_ratio, 5),
            "max_drift_story": self.max_drift_story,
            "max_stability_coefficient_theta": round(self.max_stability_coefficient_theta, 4),
            "overall_drift_status": self.overall_drift_status.value,
            "story_results": [s.to_dict() for s in self.story_results],
            "trace": self.trace.to_dict()
        }


@dataclass
class WindAnalysisResult:
    """
    Complete wind load calculation result package.
    """
    code: LateralCode
    edition: CodeEdition
    parameters: WindParameters
    total_building_height_m: float
    base_shear_Vw_kN: float
    base_overturning_moment_Mw0_kNm: float
    max_top_displacement_mm: float
    max_drift_ratio: float
    max_drift_story: str
    overall_drift_status: DesignStatus
    story_results: List[StoryWindResult]
    trace: CalculationTrace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "edition": self.edition.value,
            "parameters": self.parameters.to_dict(),
            "total_building_height_m": round(self.total_building_height_m, 2),
            "base_shear_Vw_kN": round(self.base_shear_Vw_kN, 2),
            "base_overturning_moment_Mw0_kNm": round(self.base_overturning_moment_Mw0_kNm, 2),
            "max_top_displacement_mm": round(self.max_top_displacement_mm, 2),
            "max_drift_ratio": round(self.max_drift_ratio, 5),
            "max_drift_story": self.max_drift_story,
            "overall_drift_status": self.overall_drift_status.value,
            "story_results": [s.to_dict() for s in self.story_results],
            "trace": self.trace.to_dict()
        }


@dataclass
class LateralComparisonResult:
    """
    Direct comparison between Seismic and Wind demands at every level and overall base actions.
    """
    governing_base_shear: str         # "SEISMIC" or "WIND"
    governing_base_shear_value_kN: float
    seismic_base_shear_kN: float
    wind_base_shear_kN: float
    ratio_seismic_to_wind_base_shear: float
    governing_overturning: str        # "SEISMIC" or "WIND"
    governing_overturning_value_kNm: float
    seismic_overturning_kNm: float
    wind_overturning_kNm: float
    governing_drift: str              # "SEISMIC" or "WIND"
    seismic_max_drift_ratio: float
    wind_max_drift_ratio: float
    level_comparisons: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "governing_base_shear": self.governing_base_shear,
            "governing_base_shear_value_kN": round(self.governing_base_shear_value_kN, 2),
            "seismic_base_shear_kN": round(self.seismic_base_shear_kN, 2),
            "wind_base_shear_kN": round(self.wind_base_shear_kN, 2),
            "ratio_seismic_to_wind_base_shear": round(self.ratio_seismic_to_wind_base_shear, 3),
            "governing_overturning": self.governing_overturning,
            "governing_overturning_value_kNm": round(self.governing_overturning_value_kNm, 2),
            "seismic_overturning_kNm": round(self.seismic_overturning_kNm, 2),
            "wind_overturning_kNm": round(self.wind_overturning_kNm, 2),
            "governing_drift": self.governing_drift,
            "seismic_max_drift_ratio": round(self.seismic_max_drift_ratio, 5),
            "wind_max_drift_ratio": round(self.wind_max_drift_ratio, 5),
            "level_comparisons": self.level_comparisons
        }
