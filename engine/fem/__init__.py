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
    "run_all_benchmarks",
    "run_all_shell_benchmarks"
]
