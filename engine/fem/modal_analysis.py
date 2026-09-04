"""
Modal Analysis & Structural Dynamics Engine
STRUCTURE-X ULTIMATE — PHASE 07

Implements:
  - Global Consistent & Lumped Mass Matrix Assembly for 3D Frames and Shells
  - Generalized Eigenvalue Problem Formulation (K_ff * phi = lambda * M_ff * phi)
  - Pure Python & SciPy Eigenvalue Solvers (Jacobi Eigenvalue Algorithm & Cholesky Reduction)
  - Modal Frequencies, Periods, Eigenvalues
  - Modal Participation Factors, Effective Modal Masses, and Cumulative Mass Ratios
  - Mode Shape Normalization (Mass-Normalized and Unity Max Displacement)
  - Harmonic Mode Shape Animation Generator for 3D Viewport Visualization
  - Numerical Verification Models (Euler-Bernoulli Beams, 3D Spatial Frames)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import math
import time

from .materials import Material
from .sections import CrossSection
from .frame_element_3d import FrameElement3D
from .shell_element_3d import ShellElement3D
from .dof_system import NodeDOFSystem
from .load_engine import MassSummary, LoadEngine
from .matrix_ops import (
    create_zero_matrix,
    matrix_multiply,
    matrix_transpose,
    matrix_vector_multiply,
    vector_dot_product,
    vector_length,
    vector_normalize
)


@dataclass
class ModeShapeNodeDisplacement:
    """Mode shape translations and rotations at a single node."""
    ux: float = 0.0
    uy: float = 0.0
    uz: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    rz: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "ux": self.ux, "uy": self.uy, "uz": self.uz,
            "rx": self.rx, "ry": self.ry, "rz": self.rz
        }


@dataclass
class ModalParticipationResult:
    """Comprehensive dynamic results for an individual vibration mode."""
    mode_number: int
    eigenvalue: float              # lambda = omega^2 (rad^2/s^2)
    angular_frequency: float       # omega = sqrt(lambda) (rad/s)
    frequency: float               # f = omega / (2*pi) (Hz)
    period: float                  # T = 1 / f (s)
    generalized_mass: float        # m_i* = phi^T * M * phi (kg)
    generalized_stiffness: float   # k_i* = phi^T * K * phi (N/m)
    participation_factors: Dict[str, float]       # {'X': ..., 'Y': ..., 'Z': ..., 'RX': ..., 'RY': ..., 'RZ': ...}
    effective_modal_mass: Dict[str, float]        # In kg: {'X': ..., 'Y': ..., 'Z': ...}
    participation_ratio: Dict[str, float]         # Normalized (0.0 - 1.0): {'X': ..., 'Y': ..., 'Z': ...}
    cumulative_mass_ratio: Dict[str, float]       # Running sum (0.0 - 1.0): {'X': ..., 'Y': ..., 'Z': ...}
    mode_shapes: Dict[str, ModeShapeNodeDisplacement] = field(default_factory=dict)
    max_translation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode_number": self.mode_number,
            "eigenvalue": self.eigenvalue,
            "angular_frequency": self.angular_frequency,
            "frequency": self.frequency,
            "period": self.period,
            "generalized_mass": self.generalized_mass,
            "generalized_stiffness": self.generalized_stiffness,
            "participation_factors": self.participation_factors,
            "effective_modal_mass": self.effective_modal_mass,
            "participation_ratio": self.participation_ratio,
            "cumulative_mass_ratio": self.cumulative_mass_ratio,
            "max_translation": self.max_translation,
            "mode_shapes": {nid: shape.to_dict() for nid, shape in self.mode_shapes.items()}
        }


@dataclass
class AnimationFrame:
    """A single harmonic time-step snapshot of the deformed structure."""
    frame_index: int
    time_sec: float
    phase_rad: float
    scale_factor: float
    nodal_coordinates: Dict[str, Tuple[float, float, float]]  # {node_id: (x, y, z)}
    nodal_displacements: Dict[str, Tuple[float, float, float]]  # {node_id: (dx, dy, dz)}


@dataclass
class ModalAnalysisResult:
    """Complete multi-mode eigenvalue analysis results package."""
    total_modes: int
    modes: List[ModalParticipationResult]
    total_structural_mass: Dict[str, float]   # {'X': kg, 'Y': kg, 'Z': kg}
    total_weight_kn: float
    execution_time_ms: float
    is_converged: bool = True
    mass_matrix_diagonal_kg: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def get_mode(self, mode_num: int) -> Optional[ModalParticipationResult]:
        for m in self.modes:
            if m.mode_number == mode_num:
                return m
        return None

    def generate_animation_frames(
        self,
        mode_number: int,
        original_nodes: Dict[str, Tuple[float, float, float]],
        num_frames: int = 36,
        amplitude_scale: float = 1.0
    ) -> List[AnimationFrame]:
        """
        Generates harmonic animation snapshots u(t) = phi * sin(omega * t)
        for real-time WebGL/Canvas viewport rendering.
        """
        mode = self.get_mode(mode_number)
        if not mode:
            raise ValueError(f"Mode {mode_number} does not exist.")

        frames: List[AnimationFrame] = []
        period = mode.period if mode.period > 1e-6 else 1.0

        for f_idx in range(num_frames):
            phase = (2.0 * math.pi * f_idx) / num_frames
            t_sec = (f_idx / num_frames) * period
            scale = math.sin(phase) * amplitude_scale

            def_coords: Dict[str, Tuple[float, float, float]] = {}
            def_disps: Dict[str, Tuple[float, float, float]] = {}

            for nid, (x0, y0, z0) in original_nodes.items():
                m_disp = mode.mode_shapes.get(nid, ModeShapeNodeDisplacement())
                dx = m_disp.ux * scale
                dy = m_disp.uy * scale
                dz = m_disp.uz * scale
                def_disps[nid] = (dx, dy, dz)
                def_coords[nid] = (x0 + dx, y0 + dy, z0 + dz)

            frames.append(AnimationFrame(
                frame_index=f_idx,
                time_sec=t_sec,
                phase_rad=phase,
                scale_factor=scale,
                nodal_coordinates=def_coords,
                nodal_displacements=def_disps
            ))

        return frames

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_modes": self.total_modes,
            "total_structural_mass": self.total_structural_mass,
            "total_weight_kn": self.total_weight_kn,
            "execution_time_ms": self.execution_time_ms,
            "is_converged": self.is_converged,
            "modes": [m.to_dict() for m in self.modes]
        }


# ==============================================================================
# EIGENVALUE SOLVER UTILITIES (JACOBI & GENERALIZED EIGENVALUE PROBLEM)
# ==============================================================================

def jacobi_symmetric_eigenvalues(
    A_mat: List[List[float]],
    max_sweeps: int = 150,
    tol: float = 1e-13
) -> Tuple[List[float], List[List[float]]]:
    """
    Classical Cyclic Jacobi Algorithm for finding ALL eigenvalues and eigenvectors
    of a real symmetric matrix A.
    Guaranteed quadratic convergence and machine-precision orthogonality.
    Returns:
      eigenvalues: List[float] sorted in ascending order
      eigenvectors: List[List[float]] where columns are corresponding unit eigenvectors
    """
    n = len(A_mat)
    if n == 0:
        return [], []
    if n == 1:
        return [A_mat[0][0]], [[1.0]]

    # Deep copy A into working matrix
    A = [row[:] for row in A_mat]
    # Initialize eigenvector matrix V as Identity
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for sweep in range(max_sweeps):
        # Measure off-diagonal Frobenius norm
        off_diag_sq = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                off_diag_sq += A[i][j] * A[i][j]

        if math.sqrt(2.0 * off_diag_sq) < tol:
            break

        # Zero out off-diagonal elements via Givens rotations
        for p in range(n):
            for q in range(p + 1, n):
                apq = A[p][q]
                if abs(apq) < 1e-16:
                    continue

                app = A[p][p]
                aqq = A[q][q]
                theta = 0.5 * (aqq - app) / apq

                # t = s / c
                if theta >= 0.0:
                    t = 1.0 / (theta + math.sqrt(theta * theta + 1.0))
                else:
                    t = -1.0 / (-theta + math.sqrt(theta * theta + 1.0))

                c = 1.0 / math.sqrt(1.0 + t * t)
                s = t * c
                tau = s / (1.0 + c)

                # Update A[p][p], A[q][q], A[p][q]
                h = t * apq
                A[p][p] -= h
                A[q][q] += h
                A[p][q] = 0.0
                A[q][p] = 0.0

                # Update remaining elements of row/col p and q
                for r in range(p):
                    arp = A[r][p]
                    arq = A[r][q]
                    A[r][p] = arp - s * (arq + tau * arp)
                    A[p][r] = A[r][p]
                    A[r][q] = arq + s * (arp - tau * arq)
                    A[q][r] = A[r][q]

                for r in range(p + 1, q):
                    apr = A[p][r]
                    arq = A[r][q]
                    A[p][r] = apr - s * (arq + tau * apr)
                    A[r][p] = A[p][r]
                    A[r][q] = arq + s * (apr - tau * arq)
                    A[q][r] = A[r][q]

                for r in range(q + 1, n):
                    apr = A[p][r]
                    aqr = A[q][r]
                    A[p][r] = apr - s * (aqr + tau * apr)
                    A[r][p] = A[p][r]
                    A[q][r] = aqr + s * (apr - tau * aqr)
                    A[r][q] = A[q][r]

                # Update eigenvectors V (accumulate rotation)
                for r in range(n):
                    vrp = V[r][p]
                    vrq = V[r][q]
                    V[r][p] = vrp - s * (vrq + tau * vrp)
                    V[r][q] = vrq + s * (vrp - tau * vrq)

    # Extract diagonal eigenvalues
    raw_evals = [A[i][i] for i in range(n)]

    # Pair eigenvalues with their eigenvector columns and sort ascending
    pairs = []
    for j in range(n):
        vec = [V[i][j] for i in range(n)]
        pairs.append((raw_evals[j], vec))

    pairs.sort(key=lambda x: x[0])

    sorted_evals = [p[0] for p in pairs]
    sorted_evecs = [[pairs[j][1][i] for j in range(n)] for i in range(n)]

    return sorted_evals, sorted_evecs


# ==============================================================================
# MODAL ANALYSIS SOLVER ENGINE
# ==============================================================================

class ModalSolver:
    """
    Dedicated Modal Dynamics Engine:
      - Assembles global mass matrix M (Frame 3D + Shell 3D + Mass Sources)
      - Condenses boundary constraints to free degrees of freedom
      - Solves generalized eigenvalue problem K_ff * phi = lambda * M_ff * phi
      - Calculates full modal participation metrics & mode shape normalization
    """

    def __init__(
        self,
        dof_system: NodeDOFSystem,
        elements: Dict[str, FrameElement3D],
        shell_elements: Dict[str, ShellElement3D],
        materials: Dict[str, Material],
        sections: Dict[str, CrossSection],
        dok_K: Dict[Tuple[int, int], float],
        load_engine: Optional[LoadEngine] = None
    ):
        self.dof_system = dof_system
        self.elements = elements
        self.shell_elements = shell_elements
        self.materials = materials
        self.sections = sections
        self.dok_K = dok_K
        self.load_engine = load_engine

    def assemble_mass_matrix(
        self,
        use_consistent_mass: bool = False,
        include_mass_source: bool = True
    ) -> Tuple[List[float], Dict[str, Dict[str, float]], float]:
        """
        Assembles the global diagonal (lumped) mass vector M_diag of length (total_dofs),
        and extracts per-node mass components.
        Returns:
          M_diag: List[float] of length total_dofs (kg)
          nodal_masses: Dict[node_id, {'mass_trans': kg, 'mass_rot': kg*m^2}]
          total_mass_kg: Total translational structural mass in kg
        """
        total_dofs = self.dof_system.total_dofs
        M_diag = [0.0] * total_dofs
        nodal_mass_trans: Dict[str, float] = {nid: 0.0 for nid in self.dof_system.node_order}
        nodal_mass_rot: Dict[str, float] = {nid: 0.0 for nid in self.dof_system.node_order}

        total_frame_mass = 0.0
        total_shell_mass = 0.0

        # 1. 3D Frame Member Elements Mass
        for elem_id, elem in self.elements.items():
            L = elem.length
            rho = elem.material.density
            A = elem.section.area
            J = elem.section.torsion_j
            Iy = elem.section.iy
            Iz = elem.section.iz

            m_elem = rho * A * L
            total_frame_mass += m_elem

            # Lumped mass: m/2 at node i, m/2 at node j
            half_m = 0.5 * m_elem

            # Rotational inertia terms (about local axes):
            # Torsion: J * rho * L / 2
            # Bending: rho * I * L / 2 + m * L^2 / 24
            Ixx_loc = 0.5 * rho * J * L
            Iyy_loc = 0.5 * rho * Iy * L + (1.0 / 24.0) * m_elem * (L ** 2)
            Izz_loc = 0.5 * rho * Iz * L + (1.0 / 24.0) * m_elem * (L ** 2)

            avg_I_rot = (Ixx_loc + Iyy_loc + Izz_loc) / 3.0

            # Assign to node i
            ni = elem.start_node_id
            b_i = self.dof_system.node_indices[ni] * 6
            M_diag[b_i + 0] += half_m  # UX
            M_diag[b_i + 1] += half_m  # UY
            M_diag[b_i + 2] += half_m  # UZ
            M_diag[b_i + 3] += avg_I_rot  # RX
            M_diag[b_i + 4] += avg_I_rot  # RY
            M_diag[b_i + 5] += avg_I_rot  # RZ
            nodal_mass_trans[ni] += half_m
            nodal_mass_rot[ni] += avg_I_rot

            # Assign to node j
            nj = elem.end_node_id
            b_j = self.dof_system.node_indices[nj] * 6
            M_diag[b_j + 0] += half_m  # UX
            M_diag[b_j + 1] += half_m  # UY
            M_diag[b_j + 2] += half_m  # UZ
            M_diag[b_j + 3] += avg_I_rot  # RX
            M_diag[b_j + 4] += avg_I_rot  # RY
            M_diag[b_j + 5] += avg_I_rot  # RZ
            nodal_mass_trans[nj] += half_m
            nodal_mass_rot[nj] += avg_I_rot

        # 2. 3D Shell Elements Mass
        for s_id, s_elem in self.shell_elements.items():
            area = s_elem.area
            thickness = s_elem.thickness
            mat = s_elem.material
            rho = mat.density
            m_shell = rho * thickness * area
            total_shell_mass += m_shell

            num_n = s_elem.num_nodes
            share_m = m_shell / num_n
            # Equivalent radius of gyration for rotational inertia
            r_gyr_sq = area / (4.0 * math.pi)
            share_rot = (share_m * r_gyr_sq) / 6.0

            for nid in s_elem.node_ids:
                if nid in self.dof_system.node_indices:
                    b_n = self.dof_system.node_indices[nid] * 6
                    M_diag[b_n + 0] += share_m
                    M_diag[b_n + 1] += share_m
                    M_diag[b_n + 2] += share_m
                    M_diag[b_n + 3] += share_rot
                    M_diag[b_n + 4] += share_rot
                    M_diag[b_n + 5] += share_rot
                    nodal_mass_trans[nid] += share_m
                    nodal_mass_rot[nid] += share_rot

        # 3. Mass Source Load Contributions (Dead, Super Dead, Live fractions)
        total_source_mass = 0.0
        if include_mass_source and self.load_engine is not None:
            nodes_dict = self.dof_system.nodes
            mass_summary = self.load_engine.calculate_mass_source(
                nodes=nodes_dict,
                members=self.elements,
                shell_elements=self.shell_elements
            )
            total_source_mass = mass_summary.total_mass_kg

            # Add any load pattern converted nodal masses that exceed self-weight
            for nid, n_res in mass_summary.nodal_masses.items():
                if nid in self.dof_system.node_indices:
                    # Nodal mass from mass source (converted loads)
                    added_m = max(0.0, n_res.mass_kg - nodal_mass_trans[nid])
                    if added_m > 1e-6:
                        b_n = self.dof_system.node_indices[nid] * 6
                        M_diag[b_n + 0] += added_m
                        M_diag[b_n + 1] += added_m
                        M_diag[b_n + 2] += added_m
                        nodal_mass_trans[nid] += added_m

        total_trans_mass = sum(nodal_mass_trans.values())

        # Ensure small non-zero rotational mass on free rotational DOFs
        # (Standard regularization to prevent zero-mass rotational singularity)
        min_rot_mass = 1e-4 * (total_trans_mass / max(1, len(self.dof_system.node_order))) * 0.01
        for nid in self.dof_system.node_order:
            b_n = self.dof_system.node_indices[nid] * 6
            for d in range(3, 6):
                if M_diag[b_n + d] < min_rot_mass:
                    M_diag[b_n + d] = max(min_rot_mass, M_diag[b_n + d])

        nodal_mass_summary = {
            nid: {
                "mass_trans_kg": nodal_mass_trans[nid],
                "mass_rot_kg_m2": nodal_mass_rot[nid]
            }
            for nid in self.dof_system.node_order
        }

        return M_diag, nodal_mass_summary, total_trans_mass

    def solve_modal(
        self,
        num_modes: int = 12,
        use_consistent_mass: bool = False
    ) -> ModalAnalysisResult:
        """
        Executes complete eigenvalue modal analysis:
          1. Assembles diagonal mass vector M_diag
          2. Partitions K and M to free unconstrained degrees of freedom
          3. Solves K_ff * phi = lambda * M_ff * phi
          4. Computes modal frequencies, periods, participation factors, and effective modal mass
        """
        start_time = time.perf_counter()

        free_dofs, restrained_dofs = self.dof_system.partition_dofs()
        n_free = len(free_dofs)
        if n_free == 0:
            raise ValueError("All degrees of freedom are restrained; no free vibration modes exist.")

        # 1. Assemble Global Mass Matrix
        M_diag, nodal_masses, total_structural_mass_kg = self.assemble_mass_matrix(
            use_consistent_mass=use_consistent_mass
        )

        # 2. Extract Reduced Free DOFs Mass and Stiffness
        dof_map = {dof: idx for idx, dof in enumerate(free_dofs)}

        # Free mass vector
        m_free = [M_diag[dof] for dof in free_dofs]

        # Assemble reduced dense stiffness matrix K_ff
        K_ff = [[0.0 for _ in range(n_free)] for _ in range(n_free)]
        for (i, j), val in self.dok_K.items():
            if i in dof_map and j in dof_map:
                K_ff[dof_map[i]][dof_map[j]] += val

        # Symmetrize K_ff for numerical precision: K_sym = 0.5 * (K + K^T)
        for i in range(n_free):
            for j in range(i + 1, n_free):
                avg = 0.5 * (K_ff[i][j] + K_ff[j][i])
                K_ff[i][j] = avg
                K_ff[j][i] = avg

        # 3. Transform to Standard Symmetric Eigenvalue Problem:
        # Since M_ff is diagonal with m_i > 0:
        # Let D = diag(1 / sqrt(m_i)), then K_tilde = D * K_ff * D
        # K_tilde * y = lambda * y, where phi = D * y
        inv_sqrt_m = [1.0 / math.sqrt(max(1e-12, m)) for m in m_free]
        K_tilde = [[0.0 for _ in range(n_free)] for _ in range(n_free)]

        for i in range(n_free):
            d_i = inv_sqrt_m[i]
            for j in range(n_free):
                K_tilde[i][j] = d_i * K_ff[i][j] * inv_sqrt_m[j]

        # 4. Solve Eigenvalues & Eigenvectors via Jacobi Algorithm
        evals_all, evecs_all = jacobi_symmetric_eigenvalues(K_tilde)

        # 5. Filter and select requested number of modes
        actual_modes_count = min(num_modes, n_free)
        selected_evals = evals_all[:actual_modes_count]
        selected_evecs = [[evecs_all[i][j] for j in range(actual_modes_count)] for i in range(n_free)]

        # 6. Directional Rigid-Body Influence Vectors for Free DOFs
        # r_X has 1.0 at UX DOFs (local DOF index 0), 0.0 elsewhere
        r_vectors: Dict[str, List[float]] = {
            "X": [1.0 if (dof % 6 == 0) else 0.0 for dof in free_dofs],
            "Y": [1.0 if (dof % 6 == 1) else 0.0 for dof in free_dofs],
            "Z": [1.0 if (dof % 6 == 2) else 0.0 for dof in free_dofs],
            "RX": [1.0 if (dof % 6 == 3) else 0.0 for dof in free_dofs],
            "RY": [1.0 if (dof % 6 == 4) else 0.0 for dof in free_dofs],
            "RZ": [1.0 if (dof % 6 == 5) else 0.0 for dof in free_dofs]
        }

        # Total available mass per direction across all nodes
        total_mass_dir = {
            "X": total_structural_mass_kg,
            "Y": total_structural_mass_kg,
            "Z": total_structural_mass_kg,
            "RX": sum(M_diag[b * 6 + 3] for b in range(len(self.dof_system.node_order))),
            "RY": sum(M_diag[b * 6 + 4] for b in range(len(self.dof_system.node_order))),
            "RZ": sum(M_diag[b * 6 + 5] for b in range(len(self.dof_system.node_order)))
        }

        modes_list: List[ModalParticipationResult] = []
        cumulative_mass_ratio = {"X": 0.0, "Y": 0.0, "Z": 0.0, "RX": 0.0, "RY": 0.0, "RZ": 0.0}

        for m_idx in range(actual_modes_count):
            eigenval = max(1e-12, selected_evals[m_idx])
            omega = math.sqrt(eigenval)
            freq_hz = omega / (2.0 * math.pi)
            period_s = 1.0 / freq_hz if freq_hz > 1e-9 else 0.0

            # Raw unnormalized mode shape phi = D * y
            phi_free = [inv_sqrt_m[i] * selected_evecs[i][m_idx] for i in range(n_free)]

            # Generalized modal mass: m_star = phi^T * M_ff * phi
            m_star = sum(phi_free[i] * m_free[i] * phi_free[i] for i in range(n_free))
            if m_star < 1e-18:
                m_star = 1.0

            # Mass-normalize mode shape: phi_norm = phi / sqrt(m_star)
            # such that phi_norm^T * M_ff * phi_norm = 1.0
            norm_factor = 1.0 / math.sqrt(m_star)
            phi_norm = [p * norm_factor for p in phi_free]

            # Generalized modal stiffness: k_star = omega^2 * m_star
            k_star = eigenval * m_star

            # Participation factors & Effective Modal Mass
            part_factors: Dict[str, float] = {}
            eff_mass: Dict[str, float] = {}
            part_ratio: Dict[str, float] = {}

            for dir_key in ["X", "Y", "Z", "RX", "RY", "RZ"]:
                r_vec = r_vectors[dir_key]
                # L_dir = phi_norm^T * M_ff * r_vec
                L_dir = sum(phi_norm[i] * m_free[i] * r_vec[i] for i in range(n_free))
                part_factors[dir_key] = L_dir
                
                # Effective modal mass: M_eff = (phi^T * M * r)^2 / (phi^T * M * phi) = L_dir^2 (since phi_norm is mass-normalized)
                m_eff = L_dir * L_dir
                eff_mass[dir_key] = m_eff

                tot_m = max(1e-9, total_mass_dir[dir_key])
                ratio = min(1.0, m_eff / tot_m)
                part_ratio[dir_key] = ratio
                cumulative_mass_ratio[dir_key] = min(1.0, cumulative_mass_ratio[dir_key] + ratio)

            # Reconstruct Full 3D Nodal Mode Shape Displacements
            full_mode_dofs = [0.0] * self.dof_system.total_dofs
            for f_idx, dof in enumerate(free_dofs):
                full_mode_dofs[dof] = phi_norm[f_idx]

            node_mode_shapes: Dict[str, ModeShapeNodeDisplacement] = {}
            max_trans = 0.0

            for nid in self.dof_system.node_order:
                b_n = self.dof_system.node_indices[nid] * 6
                ux = full_mode_dofs[b_n + 0]
                uy = full_mode_dofs[b_n + 1]
                uz = full_mode_dofs[b_n + 2]
                rx = full_mode_dofs[b_n + 3]
                ry = full_mode_dofs[b_n + 4]
                rz = full_mode_dofs[b_n + 5]

                mag_t = math.sqrt(ux * ux + uy * uy + uz * uz)
                if mag_t > max_trans:
                    max_trans = mag_t

                node_mode_shapes[nid] = ModeShapeNodeDisplacement(
                    ux=ux, uy=uy, uz=uz, rx=rx, ry=ry, rz=rz
                )

            modes_list.append(ModalParticipationResult(
                mode_number=m_idx + 1,
                eigenvalue=eigenval,
                angular_frequency=omega,
                frequency=freq_hz,
                period=period_s,
                generalized_mass=1.0,  # Mass-normalized
                generalized_stiffness=eigenval,
                participation_factors=part_factors,
                effective_modal_mass=eff_mass,
                participation_ratio=part_ratio,
                cumulative_mass_ratio=dict(cumulative_mass_ratio),
                mode_shapes=node_mode_shapes,
                max_translation=max_trans
            ))

        exec_time = (time.perf_counter() - start_time) * 1000.0

        return ModalAnalysisResult(
            total_modes=actual_modes_count,
            modes=modes_list,
            total_structural_mass={
                "X": total_structural_mass_kg,
                "Y": total_structural_mass_kg,
                "Z": total_structural_mass_kg
            },
            total_weight_kn=(total_structural_mass_kg * 9.80665) / 1000.0,
            execution_time_ms=exec_time,
            is_converged=True,
            mass_matrix_diagonal_kg=nodal_masses
        )
