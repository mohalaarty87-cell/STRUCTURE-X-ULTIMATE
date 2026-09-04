"""
STRUCTURE-X ULTIMATE — MODULAR STEEL DESIGN ENGINE
Phase 11: Structural Steel Design (AISC 360-16 & Eurocode 3 EN 1993-1-1:2005)
Multi-Criteria Section Optimization (Strength, Weight, Cost).
"""

from .types import (
    DesignCode,
    CodeEdition,
    DesignMethod,
    SteelMemberType,
    SteelSectionType,
    SteelCheckType,
    DesignStatus,
    SectionCompactness,
    OptimizationCriterion,
    CalculationTrace,
    SteelCheckResult,
    SteelMemberDesignSummary,
    OptimizedCandidate,
)
from .materials import SteelMaterial
from .sections import SteelSection, SteelSectionDatabase
from .tension_check import TensionCheck
from .compression_check import CompressionCheck
from .flexure_check import FlexureCheck
from .shear_check import ShearCheck
from .interaction_check import InteractionCheck
from .optimizer import SteelSectionOptimizer
from .engine import SteelDesignEngine


def run_all_steel_benchmarks():
    from .verification_tests import run_all_steel_benchmarks as _run
    return _run()


__all__ = [
    "DesignCode",
    "CodeEdition",
    "DesignMethod",
    "SteelMemberType",
    "SteelSectionType",
    "SteelCheckType",
    "DesignStatus",
    "SectionCompactness",
    "OptimizationCriterion",
    "CalculationTrace",
    "SteelCheckResult",
    "SteelMemberDesignSummary",
    "OptimizedCandidate",
    "SteelMaterial",
    "SteelSection",
    "SteelSectionDatabase",
    "TensionCheck",
    "CompressionCheck",
    "FlexureCheck",
    "ShearCheck",
    "InteractionCheck",
    "SteelSectionOptimizer",
    "SteelDesignEngine",
    "run_all_steel_benchmarks",
]
