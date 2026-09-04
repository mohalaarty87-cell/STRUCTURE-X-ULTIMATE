"""
STRUCTURE-X ULTIMATE — STEEL DESIGN ENGINE TYPES
Data structures, enums, calculation traces, and check results for structural steel design
strictly complying with AISC 360-16 (LRFD/ASD) and Eurocode 3 (EN 1993-1-1:2005).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class DesignCode(str, Enum):
    AISC_360 = "AISC 360"
    EUROCODE_3 = "Eurocode 3"


class CodeEdition(str, Enum):
    AISC_360_16 = "AISC 360-16"
    EN_1993_1_1_2005 = "EN 1993-1-1:2005"


class DesignMethod(str, Enum):
    LRFD = "LRFD"  # Load and Resistance Factor Design (phi factors)
    ASD = "ASD"    # Allowable Strength Design (Omega factors)
    LIMIT_STATE = "Limit State"  # Eurocode partial factor design (gamma_M)


class SteelMemberType(str, Enum):
    BEAM = "Beam"
    COLUMN = "Column"
    BEAM_COLUMN = "Beam-Column"
    BRACE = "Brace"
    TENSION_MEMBER = "Tension Member"
    TRUSS_CHORD = "Truss Chord"


class SteelSectionType(str, Enum):
    I_SHAPE = "I-Shape (W/UB/UC/IPE/HE)"
    HSS_RECTANGULAR = "HSS Rectangular/Square"
    HSS_ROUND = "HSS Round/Pipe"
    CHANNEL = "Channel (C/MC/UPN)"
    ANGLE = "Angle (L)"
    TEE = "Tee (WT)"


class SteelCheckType(str, Enum):
    TENSION = "Tension"
    COMPRESSION = "Compression"
    FLEXURAL_BUCKLING = "Flexural Buckling"
    TORSIONAL_BUCKLING = "Torsional Buckling"
    FLEXURE_MAJOR = "Flexure Major Axis (X-X/Z-Z)"
    FLEXURE_MINOR = "Flexure Minor Axis (Y-Y)"
    LATERAL_TORSIONAL_BUCKLING = "Lateral-Torsional Buckling (LTB)"
    SHEAR_MAJOR = "Shear Major (Y-Y)"
    SHEAR_MINOR = "Shear Minor (Z-Z)"
    COMBINED_FORCES = "Combined Forces"
    INTERACTION = "P-M Interaction"
    LOCAL_BUCKLING = "Local Slenderness (Flange/Web)"


class DesignStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class SectionCompactness(str, Enum):
    COMPACT = "Compact"
    NON_COMPACT = "Non-Compact"
    SLENDER = "Slender"
    CLASS_1 = "Class 1 (Plastic)"
    CLASS_2 = "Class 2 (Compact)"
    CLASS_3 = "Class 3 (Semi-Compact)"
    CLASS_4 = "Class 4 (Slender)"


class OptimizationCriterion(str, Enum):
    STRENGTH = "Strength"
    WEIGHT = "Weight"
    COST = "Cost"


@dataclass
class CalculationTrace:
    """
    Exposes mandatory traceability fields required for professional engineering review.
    Every calculation step exposes:
    - Design Code & Edition
    - Governing Code Clause
    - Input parameters
    - Mathematical Method & Formulations
    - Intermediate calculated values
    - Final capacity result
    - Design demand and limit
    - PASS/FAIL status
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
class SteelCheckResult:
    """
    Full calculation result for an individual structural check:
    Demand, Capacity, D/C Ratio, Governing Limit State, Status (PASS/FAIL), and Audit Trace.
    """
    check_type: SteelCheckType
    demand: float
    capacity: float
    dc_ratio: float
    status: DesignStatus
    governing_limit_state: str
    trace: CalculationTrace
    units: str = "kN"
    summary_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type.value if isinstance(self.check_type, SteelCheckType) else self.check_type,
            "demand": round(self.demand, 3),
            "capacity": round(self.capacity, 3),
            "dc_ratio": round(self.dc_ratio, 4),
            "status": self.status.value if isinstance(self.status, DesignStatus) else self.status,
            "governing_limit_state": self.governing_limit_state,
            "units": self.units,
            "summary_message": self.summary_message,
            "trace": self.trace.to_dict()
        }


@dataclass
class SteelMemberDesignSummary:
    """
    Aggregated structural summary for an entire steel member across all performed checks.
    """
    member_id: str
    section_name: str
    member_type: SteelMemberType
    checks: List[SteelCheckResult]
    governing_check: SteelCheckType
    max_dc_ratio: float
    overall_status: DesignStatus
    weight_kg: float = 0.0
    critical_clause: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id": self.member_id,
            "section_name": self.section_name,
            "member_type": self.member_type.value if isinstance(self.member_type, SteelMemberType) else self.member_type,
            "governing_check": self.governing_check.value if isinstance(self.governing_check, SteelCheckType) else self.governing_check,
            "max_dc_ratio": round(self.max_dc_ratio, 4),
            "overall_status": self.overall_status.value if isinstance(self.overall_status, DesignStatus) else self.overall_status,
            "weight_kg": round(self.weight_kg, 2),
            "critical_clause": self.critical_clause,
            "checks": [c.to_dict() for c in self.checks]
        }


@dataclass
class OptimizedCandidate:
    """
    Output candidate from section optimization.
    """
    section_name: str
    section_type: SteelSectionType
    weight_kg_m: float
    total_weight_kg: float
    estimated_cost_usd: float
    max_dc_ratio: float
    governing_check: SteelCheckType
    status: DesignStatus
    strength_efficiency: float  # e.g., max_dc_ratio / 1.0 (closer to 1.0 without exceeding = highest efficiency)
    weight_savings_percent: float = 0.0
    cost_savings_percent: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_name": self.section_name,
            "section_type": self.section_type.value if isinstance(self.section_type, SteelSectionType) else self.section_type,
            "weight_kg_m": round(self.weight_kg_m, 2),
            "total_weight_kg": round(self.total_weight_kg, 2),
            "estimated_cost_usd": round(self.estimated_cost_usd, 2),
            "max_dc_ratio": round(self.max_dc_ratio, 4),
            "governing_check": self.governing_check.value if isinstance(self.governing_check, SteelCheckType) else self.governing_check,
            "status": self.status.value if isinstance(self.status, DesignStatus) else self.status,
            "strength_efficiency": round(self.strength_efficiency, 4),
            "weight_savings_percent": round(self.weight_savings_percent, 1),
            "cost_savings_percent": round(self.cost_savings_percent, 1),
            "details": self.details
        }
