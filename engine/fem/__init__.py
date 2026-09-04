"""
STRUCTURE-X ULTIMATE — 3D FINITE ELEMENT ANALYSIS CORE
Phase 04: 3D Direct Stiffness Frame FEM Engine
Phase 05: 3D Flat Shell (Slabs & Shear Walls) FEM Engine
"""

from .dof_system import NodeDOFSystem
from .materials import Material
from .sections import CrossSection
from .frame_element_3d import FrameElement3D
from .shell_element_3d import ShellElement3D, ShellSurfaceLoad, ShellStressResult
from .meshing import ShellMeshGenerator, MeshedAreaEntity, MeshQualityReport
from .solver_core import FEMSolver3D, AnalysisResult
from .modal_analysis import ModalSolver, ModalAnalysisResult, ModalParticipationResult
from .p_delta_analysis import PDeltaSolver, PDeltaResult, StabilityDiagnostics, StoryStabilityResult
from .response_spectrum_analysis import (
    ResponseSpectrumSolver,
    ResponseSpectrumDefinition,
    ResponseSpectrumAnalysisResult,
    StoryResponseResult,
    ModalResponseData
)
from .time_history_analysis import (
    TimeHistorySolver,
    TimeHistoryResult,
    TimeHistoryStepRecord
)
from .pushover_analysis import (
    PushoverSolver,
    PushoverResult,
    PushoverStepRecord,
    PushoverCapacityCurvePoint,
    PlasticHingeProperty,
    HingeState,
    MemberHingeState
)
from .verification_benchmarks import run_all_benchmarks
from .shell_benchmarks import run_all_shell_benchmarks

__all__ = [
    "NodeDOFSystem",
    "Material",
    "CrossSection",
    "FrameElement3D",
    "ShellElement3D",
    "ShellSurfaceLoad",
    "ShellStressResult",
    "ShellMeshGenerator",
    "MeshedAreaEntity",
    "MeshQualityReport",
    "FEMSolver3D",
    "AnalysisResult",
    "ModalSolver",
    "ModalAnalysisResult",
    "ModalParticipationResult",
    "PDeltaSolver",
    "PDeltaResult",
    "StabilityDiagnostics",
    "StoryStabilityResult",
    "ResponseSpectrumSolver",
    "ResponseSpectrumDefinition",
    "ResponseSpectrumAnalysisResult",
    "StoryResponseResult",
    "ModalResponseData",
    "TimeHistorySolver",
    "TimeHistoryResult",
    "TimeHistoryStepRecord",
    "PushoverSolver",
    "PushoverResult",
    "PushoverStepRecord",
    "PushoverCapacityCurvePoint",
    "PlasticHingeProperty",
    "HingeState",
    "MemberHingeState",
    "run_all_benchmarks",
    "run_all_shell_benchmarks"
]
