"""
STRUCTURE-X ULTIMATE — CONCRETE DESIGN ENGINE TYPES
Modular data definitions for structural concrete calculations, compliance, and auditing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class DesignCode(str, Enum):
    ACI_318 = "ACI 318"
    EUROCODE_2 = "Eurocode 2"


class CodeEdition(str, Enum):
    ACI_318_19 = "ACI 318-19"
    EN_1992_1_1_2004 = "EN 1992-1-1:2004+A1:2014"


class MemberType(str, Enum):
    BEAM = "Beam"
    COLUMN = "Column"
    SLAB = "Slab"
    SHEAR_WALL = "Shear Wall"


class CheckType(str, Enum):
    AXIAL = "Axial"
    FLEXURE = "Flexure"
    BIAXIAL_FLEXURE = "Biaxial Flexure"
    SHEAR = "Shear"
    TORSION = "Torsion"
    PUNCHING_SHEAR = "Punching Shear"
    INTERACTION = "Interaction"


class DesignStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class CalculationTrace:
    """
    Exposes mandatory traceability fields required for professional engineering review.
    Every calculation must expose:
    - Design Code
    - Code Edition
    - Clause
    - Inputs
    - Method
    - Intermediate Results
    - Final Result
    - Limit
    - PASS/FAIL
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
class ReinforcementResult:
    """
    Reinforcement quantities, ratio, detailing requirements, and callouts.
    """
    required_area_mm2: float
    provided_area_mm2: float
    reinforcement_ratio: float
    min_area_mm2: float = 0.0
    max_area_mm2: float = 0.0
    bar_callout: str = ""
    spacing_mm: Optional[float] = None
    legs: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_area_mm2": round(self.required_area_mm2, 2),
            "provided_area_mm2": round(self.provided_area_mm2, 2),
            "reinforcement_ratio": round(self.reinforcement_ratio, 6),
            "min_area_mm2": round(self.min_area_mm2, 2),
            "max_area_mm2": round(self.max_area_mm2, 2),
            "bar_callout": self.bar_callout,
            "spacing_mm": round(self.spacing_mm, 1) if self.spacing_mm is not None else None,
            "legs": self.legs
        }


@dataclass
class DesignCheckResult:
    """
    Full output of a single check: Demand, Capacity, D/C Ratio, Reinforcement, Trace, and PASS/FAIL status.
    """
    check_type: CheckType
    member_type: MemberType
    demand: float
    capacity: float
    dc_ratio: float
    status: DesignStatus
    trace: CalculationTrace
    reinforcement: Optional[ReinforcementResult] = None
    units: str = "kN"
    summary_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type.value if isinstance(self.check_type, CheckType) else self.check_type,
            "member_type": self.member_type.value if isinstance(self.member_type, MemberType) else self.member_type,
            "demand": round(self.demand, 3),
            "capacity": round(self.capacity, 3),
            "dc_ratio": round(self.dc_ratio, 4),
            "status": self.status.value if isinstance(self.status, DesignStatus) else self.status,
            "units": self.units,
            "summary_message": self.summary_message,
            "reinforcement": self.reinforcement.to_dict() if self.reinforcement else None,
            "trace": self.trace.to_dict()
        }


@dataclass
class MemberDesignSummary:
    """
    Aggregated summary for an entire member across all performed structural checks.
    """
    member_id: str
    member_type: MemberType
    checks: List[DesignCheckResult]
    governing_check: CheckType
    max_dc_ratio: float
    overall_status: DesignStatus
    required_reinforcement: Dict[str, float] = field(default_factory=dict)
    provided_reinforcement: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_id": self.member_id,
            "member_type": self.member_type.value,
            "governing_check": self.governing_check.value,
            "max_dc_ratio": round(self.max_dc_ratio, 4),
            "overall_status": self.overall_status.value,
            "required_reinforcement": {k: round(v, 2) for k, v in self.required_reinforcement.items()},
            "provided_reinforcement": {k: round(v, 2) for k, v in self.provided_reinforcement.items()},
            "checks": [c.to_dict() for c in self.checks]
        }
