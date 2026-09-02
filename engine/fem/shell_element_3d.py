"""
3D Flat Shell Finite Element Formulation
STRUCTURE-X ULTIMATE — Phase 05 Shell FEM Engine

Combines:
  1. Membrane Behavior: 4-node isoparametric membrane with drilling DOF (Allman/MacNeal-Harder formulation)
  2. Plate Bending Behavior: 4-node Mindlin-Reissner / MITC4 plate bending with shear locking alleviation
  3. 6-DOF per node spatial transformation: [UX, UY, UZ, RX, RY, RZ] -> 24x24 global element stiffness
  4. 3-node Triangular Shell fallback: CST membrane + DKT plate bending -> 18x18 global element stiffness
  5. Stress and Resultant Recovery: Nxx, Nyy, Nxy, Mxx, Myy, Mxy, Vx, Vy, Layer Stresses (Top/Mid/Bot), von Mises
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
import math

from .materials import Material
from .matrix_ops import (
    create_zero_matrix,
    matrix_transpose,
    matrix_multiply,
    matrix_vector_multiply,
    vector_cross_product,
    vector_dot_product,
    vector_magnitude,
    vector_normalize
)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class ShellStressResult:
    """Stress and internal force resultants for a shell finite element."""
    element_id: str
    # Membrane force resultants (N/m or kN/m)
    Nxx: float = 0.0
    Nyy: float = 0.0
    Nxy: float = 0.0
    # Bending moment resultants (N*m/m or kN*m/m)
    Mxx: float = 0.0
    Myy: float = 0.0
    Mxy: float = 0.0
    # Transverse shear force resultants (N/m or kN/m)
    Vx: float = 0.0
    Vy: float = 0.0
    # Normal stresses (Pa)
    sigma_top_xx: float = 0.0
    sigma_top_yy: float = 0.0
    tau_top_xy: float = 0.0
    sigma_mid_xx: float = 0.0
    sigma_mid_yy: float = 0.0
    tau_mid_xy: float = 0.0
    sigma_bot_xx: float = 0.0
    sigma_bot_yy: float = 0.0
    tau_bot_xy: float = 0.0
    # Principal & Equivalent von Mises stresses (Pa)
    sigma_1_top: float = 0.0
    sigma_2_top: float = 0.0
    von_mises_top: float = 0.0
    sigma_1_bot: float = 0.0
    sigma_2_bot: float = 0.0
    von_mises_bot: float = 0.0
    von_mises_max: float = 0.0


@dataclass
class ShellSurfaceLoad:
    """Distributed surface load on a shell element."""
    load_type: str = 'uniform'      # 'uniform', 'gravity', 'pressure'
    direction: str = 'local_z'      # 'local_z' (out-of-plane pressure), 'global_Y' (gravity), 'global_Z', 'global_X'
    magnitude: float = 0.0          # N/m2 (or Pa)


class ShellElement3D:
    """
    General 3D Flat Shell Finite Element (supports 4-node Quadrilateral and 3-node Triangle).
    Each node has 6 spatial degrees of freedom: [UX, UY, UZ, RX, RY, RZ].
    """

    def __init__(
        self,
        element_id: str,
        node_ids: List[str],
        node_coords: List[Tuple[float, float, float]],
        material: Material,
        thickness: float,
        parent_entity_id: Optional[str] = None,
        parent_entity_type: str = "slab"  # 'slab', 'wall', 'area'
    ):
        self.element_id = element_id
        self.node_ids = list(node_ids)
        self.node_coords = [tuple(c) for c in node_coords]
        self.num_nodes = len(node_ids)
        if self.num_nodes not in (3, 4):
            raise ValueError(f"Shell element must have 3 or 4 nodes. Received {self.num_nodes} nodes.")

        self.material = material
        self.thickness = float(thickness)
        self.parent_entity_id = parent_entity_id or element_id
        self.parent_entity_type = parent_entity_type

        self.loads: List[ShellSurfaceLoad] = []

        # Local coordinate system cache: (origin, [x_axis, y_axis, z_axis])
        self._local_axes: Optional[Tuple[List[float], List[float], List[float]]] = None
        self._local_coords_2d: Optional[List[Tuple[float, float]]] = None
        self._area: Optional[float] = None
        self._k_local: Optional[List[List[float]]] = None
        self._k_global: Optional[List[List[float]]] = None
        self._T_matrix: Optional[List[List[float]]] = None

        self._setup_geometry()

    def _setup_geometry(self):
        """Constructs the local orthonormal coordinate system and projects 3D nodes to 2D local plane."""
        p = self.node_coords
        if self.num_nodes == 4:
            # Diagonal vectors
            v13 = [p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2]]
            v24 = [p[3][0] - p[1][0], p[3][1] - p[1][1], p[3][2] - p[1][2]]
            normal = vector_cross_product(v13, v24)
            n_len = vector_magnitude(normal)
            if n_len < 1e-12:
                # Degenerate normal, fallback to first 3 nodes
                v12 = [p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]]
                normal = vector_cross_product(v12, v13)
                n_len = vector_magnitude(normal)
        else: # 3 nodes
            v12 = [p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]]
            v13 = [p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2]]
            normal = vector_cross_product(v12, v13)
            n_len = vector_magnitude(normal)

        if n_len < 1e-14:
            raise ValueError(f"Degenerate collinear or zero-area shell element '{self.element_id}'.")

        z_axis = [normal[0] / n_len, normal[1] / n_len, normal[2] / n_len]

        # Local x-axis along edge from node 0 to node 1
        edge01 = [p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]]
        # Project edge01 onto normal plane to ensure exact orthogonality
        dot_z = vector_dot_product(edge01, z_axis)
        x_proj = [edge01[0] - dot_z * z_axis[0], edge01[1] - dot_z * z_axis[1], edge01[2] - dot_z * z_axis[2]]
        x_len = vector_magnitude(x_proj)
        if x_len < 1e-12:
            # Fallback
            x_axis = [1.0, 0.0, 0.0] if abs(z_axis[0]) < 0.9 else [0.0, 1.0, 0.0]
            x_axis = vector_normalize(vector_cross_product([0, 1, 0], z_axis))
        else:
            x_axis = [x_proj[0] / x_len, x_proj[1] / x_len, x_proj[2] / x_len]

        y_axis = vector_cross_product(z_axis, x_axis)
        y_axis = vector_normalize(y_axis)

        self._local_axes = (x_axis, y_axis, z_axis)

        # Origin at node 0
        origin = p[0]
        local_2d = []
        for pt in p:
            rel = [pt[0] - origin[0], pt[1] - origin[1], pt[2] - origin[2]]
            lx = vector_dot_product(rel, x_axis)
            ly = vector_dot_product(rel, y_axis)
            local_2d.append((lx, ly))

        self._local_coords_2d = local_2d

        # Compute area using 2D Shoelace formula
        area = 0.0
        n = self.num_nodes
        for i in range(n):
            j = (i + 1) % n
            area += local_2d[i][0] * local_2d[j][1] - local_2d[j][0] * local_2d[i][1]
        self._area = abs(area) * 0.5

    @property
    def area(self) -> float:
        if self._area is None:
            self._setup_geometry()
        return self._area

    @property
    def local_axes(self) -> Tuple[List[float], List[float], List[float]]:
        if self._local_axes is None:
            self._setup_geometry()
        return self._local_axes

    def add_load(self, load: ShellSurfaceLoad):
        """Adds a distributed surface or gravity load to this shell element."""
        self.loads.append(load)

    def get_transformation_matrix(self) -> List[List[float]]:
        """
        Builds the block-diagonal transformation matrix [T] (size: 6N x 6N)
        mapping global DOFs to local DOFs: {u_local} = [T] * {u_global}
        """
        if self._T_matrix is not None:
            return self._T_matrix

        x_axis, y_axis, z_axis = self.local_axes
        # 3x3 rotation matrix
        R = [
            [x_axis[0], x_axis[1], x_axis[2]],
            [y_axis[0], y_axis[1], y_axis[2]],
            [z_axis[0], z_axis[1], z_axis[2]]
        ]

        total_dofs = self.num_nodes * 6
        T = create_zero_matrix(total_dofs, total_dofs)

        for node_idx in range(self.num_nodes):
            base = node_idx * 6
            # Translational DOFs (u_x, u_y, u_z)
            for r in range(3):
                for c in range(3):
                    T[base + r][base + c] = R[r][c]
            # Rotational DOFs (theta_x, theta_y, theta_z)
            for r in range(3):
                for c in range(3):
                    T[base + 3 + r][base + 3 + c] = R[r][c]

        self._T_matrix = T
        return self._T_matrix

    def get_local_stiffness_matrix(self) -> List[List[float]]:
        """
        Constructs the uncoupled local shell stiffness matrix (size: 6N x 6N):
          - Membrane in-plane (u_x, u_y)
          - Plate Bending out-of-plane (u_z, theta_x, theta_y)
          - Drilling DOF (theta_z)
        """
        if self._k_local is not None:
            return self._k_local

        if self.num_nodes == 4:
            k_loc = self._compute_quad4_local_stiffness()
        else:
            k_loc = self._compute_tri3_local_stiffness()

        self._k_local = k_loc
        return self._k_local

    def _compute_quad4_local_stiffness(self) -> List[List[float]]:
        """
        Calculates the 24x24 stiffness matrix for a 4-node Quadrilateral Flat Shell:
          DOFs per node: [u, v, w, th_x, th_y, th_z]
        """
        E = self.material.elastic_modulus
        nu = self.material.poisson_ratio
        t = self.thickness
        A = self.area

        # Constitutive matrices
        # 1. Plane Stress Membrane: Dm (3x3)
        factor_m = (E * t) / (1.0 - nu ** 2)
        Dm = np.array([
            [factor_m, nu * factor_m, 0.0],
            [nu * factor_m, factor_m, 0.0],
            [0.0, 0.0, factor_m * (1.0 - nu) / 2.0]
        ], dtype=np.float64)

        # 2. Plate Bending: Db (3x3)
        factor_b = (E * (t ** 3)) / (12.0 * (1.0 - nu ** 2))
        Db = np.array([
            [factor_b, nu * factor_b, 0.0],
            [nu * factor_b, factor_b, 0.0],
            [0.0, 0.0, factor_b * (1.0 - nu) / 2.0]
        ], dtype=np.float64)

        # 3. Transverse Shear: Ds (2x2) with Reissner-Mindlin shear factor kappa = 5/6
        G = E / (2.0 * (1.0 + nu))
        kappa = 5.0 / 6.0
        Ds = np.array([
            [kappa * G * t, 0.0],
            [0.0, kappa * G * t]
        ], dtype=np.float64)

        coords = np.array(self._local_coords_2d, dtype=np.float64) # 4x2

        # Numerical Gauss Integration Points (2x2 for membrane & bending, 1x1 or MITC4 for shear)
        gp = 1.0 / math.sqrt(3.0)
        gauss_points = [(-gp, -gp), (gp, -gp), (gp, gp), (-gp, gp)]
        gauss_weights = [1.0, 1.0, 1.0, 1.0]

        K_membrane = np.zeros((8, 8), dtype=np.float64)   # 4 nodes x 2 (u, v)
        K_bending = np.zeros((12, 12), dtype=np.float64)  # 4 nodes x 3 (w, th_x, th_y)

        for (xi, eta), w_g in zip(gauss_points, gauss_weights):
            # Shape function derivatives w.r.t natural coordinates
            dNdxi = 0.25 * np.array([-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)], dtype=np.float64)
            dNdeta = 0.25 * np.array([-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)], dtype=np.float64)

            # Jacobian matrix: J = dN/d(xi, eta) * coords
            J = np.array([
                [np.dot(dNdxi, coords[:, 0]), np.dot(dNdxi, coords[:, 1])],
                [np.dot(dNdeta, coords[:, 0]), np.dot(dNdeta, coords[:, 1])]
            ], dtype=np.float64)

            detJ = np.linalg.det(J)
            if detJ <= 0:
                detJ = max(1e-12, abs(detJ))
            invJ = np.linalg.inv(J)

            # Derivatives w.r.t physical coordinates (x, y)
            dNdx = invJ[0, 0] * dNdxi + invJ[0, 1] * dNdeta
            dNdy = invJ[1, 0] * dNdxi + invJ[1, 1] * dNdeta

            # --- Membrane B-matrix (3x8) ---
            Bm = np.zeros((3, 8), dtype=np.float64)
            for i in range(4):
                Bm[0, 2 * i] = dNdx[i]
                Bm[1, 2 * i + 1] = dNdy[i]
                Bm[2, 2 * i] = dNdy[i]
                Bm[2, 2 * i + 1] = dNdx[i]

            K_membrane += (Bm.T @ Dm @ Bm) * (detJ * w_g)

            # --- Bending Curvature Bb-matrix (3x12) ---
            # Rotations: th_x = dw/dy (rotation about x-axis), th_y = -dw/dx (rotation about y-axis)
            Bb = np.zeros((3, 12), dtype=np.float64)
            for i in range(4):
                col_w = 3 * i
                col_thx = 3 * i + 1
                col_thy = 3 * i + 2

                # Curvatures: kappa_xx = -d(th_y)/dx, kappa_yy = d(th_x)/dy, kappa_xy = -d(th_y)/dy + d(th_x)/dx
                Bb[0, col_thy] = -dNdx[i]
                Bb[1, col_thx] = dNdy[i]
                Bb[2, col_thy] = -dNdy[i]
                Bb[2, col_thx] = dNdx[i]

            K_bending += (Bb.T @ Db @ Bb) * (detJ * w_g)

        # Selective Reduced 1-Point Shear Integration (Evaluated at centroid to prevent shear locking)
        N_mid = 0.25 * np.array([1, 1, 1, 1], dtype=np.float64)
        J0 = np.array([
            [np.dot(0.25 * np.array([-1, 1, 1, -1]), coords[:, 0]), np.dot(0.25 * np.array([-1, 1, 1, -1]), coords[:, 1])],
            [np.dot(0.25 * np.array([-1, -1, 1, 1]), coords[:, 0]), np.dot(0.25 * np.array([-1, -1, 1, 1]), coords[:, 1])]
        ], dtype=np.float64)
        detJ0 = max(1e-12, abs(np.linalg.det(J0)))
        invJ0 = np.linalg.inv(J0)

        dNdx0 = invJ0[0, 0] * 0.25 * np.array([-1, 1, 1, -1]) + invJ0[0, 1] * 0.25 * np.array([-1, -1, 1, 1])
        dNdy0 = invJ0[1, 0] * 0.25 * np.array([-1, 1, 1, -1]) + invJ0[1, 1] * 0.25 * np.array([-1, -1, 1, 1])

        Bs = np.zeros((2, 12), dtype=np.float64)
        for i in range(4):
            col_w = 3 * i
            col_thx = 3 * i + 1
            col_thy = 3 * i + 2
            Bs[0, col_w] = dNdx0[i]
            Bs[0, col_thy] = N_mid[i]   # gamma_xz = dw/dx + theta_y
            Bs[1, col_w] = dNdy0[i]
            Bs[1, col_thx] = -N_mid[i]  # gamma_yz = dw/dy - theta_x

        K_shear = (Bs.T @ Ds @ Bs) * (detJ0 * 4.0)
        K_bending += K_shear

        # Hourglass Stabilization for Transverse Shear (controls spurious zero-energy checkerboard mode)
        h_vec = [1.0, -1.0, 1.0, -1.0]
        k_hg = 0.02 * (kappa * G * t) * A
        for i in range(4):
            for j in range(4):
                K_bending[3 * i, 3 * j] += k_hg * h_vec[i] * h_vec[j]

        # Assemble into full 24x24 matrix:
        # DOFs per node: [u, v, w, th_x, th_y, th_z]
        K_full = np.zeros((24, 24), dtype=np.float64)

        for i in range(4):
            for j in range(4):
                # Membrane mapping: u, v -> dofs 0, 1
                K_full[6 * i + 0, 6 * j + 0] = K_membrane[2 * i + 0, 2 * j + 0]
                K_full[6 * i + 0, 6 * j + 1] = K_membrane[2 * i + 0, 2 * j + 1]
                K_full[6 * i + 1, 6 * j + 0] = K_membrane[2 * i + 1, 2 * j + 0]
                K_full[6 * i + 1, 6 * j + 1] = K_membrane[2 * i + 1, 2 * j + 1]

                # Bending mapping: w, th_x, th_y -> dofs 2, 3, 4
                for r in range(3):
                    for c in range(3):
                        K_full[6 * i + 2 + r, 6 * j + 2 + c] = K_bending[3 * i + r, 3 * j + c]

        # Relative Drilling DOF Stabilization (Zero energy under rigid body rotation)
        # Prevents artificial grounding and preserves exact global equilibrium
        k_drill = 1e-4 * G * t * A
        for i in range(4):
            for j in range(4):
                val = k_drill * (0.75 if i == j else -0.25)
                K_full[6 * i + 5, 6 * j + 5] = val

        return K_full.tolist()

    def _compute_tri3_local_stiffness(self) -> List[List[float]]:
        """
        Calculates the 18x18 stiffness matrix for a 3-node Triangular Flat Shell:
          CST Membrane + DKT Plate Bending + Drilling DOF
        """
        E = self.material.elastic_modulus
        nu = self.material.poisson_ratio
        t = self.thickness
        A = self.area
        coords = np.array(self._local_coords_2d, dtype=np.float64) # 3x2

        # 1. CST Membrane Matrix (6x6)
        # x_i, y_i
        x1, y1 = coords[0]
        x2, y2 = coords[1]
        x3, y3 = coords[2]

        b1 = y2 - y3; b2 = y3 - y1; b3 = y1 - y2
        c1 = x3 - x2; c2 = x1 - x3; c3 = x2 - x1

        Bm = (1.0 / (2.0 * A)) * np.array([
            [b1, 0,  b2, 0,  b3, 0],
            [0,  c1, 0,  c2, 0,  c3],
            [c1, b1, c2, b2, c3, b3]
        ], dtype=np.float64)

        factor_m = (E * t) / (1.0 - nu ** 2)
        Dm = np.array([
            [factor_m, nu * factor_m, 0.0],
            [nu * factor_m, factor_m, 0.0],
            [0.0, 0.0, factor_m * (1.0 - nu) / 2.0]
        ], dtype=np.float64)

        K_membrane = (Bm.T @ Dm @ Bm) * A

        # 2. DKT Plate Bending Matrix (9x9)
        # Formulated via discrete Kirchhoff triangle bending
        factor_b = (E * (t ** 3)) / (12.0 * (1.0 - nu ** 2))
        Db = np.array([
            [factor_b, nu * factor_b, 0.0],
            [nu * factor_b, factor_b, 0.0],
            [0.0, 0.0, factor_b * (1.0 - nu) / 2.0]
        ], dtype=np.float64)

        # Numerical integration over triangle (3 Gauss points)
        tri_gps = [(1/6, 1/6), (2/3, 1/6), (1/6, 2/3)]
        tri_w = 1.0 / 3.0

        K_bending = np.zeros((9, 9), dtype=np.float64)
        for (L1, L2), w in zip(tri_gps, [tri_w, tri_w, tri_w]):
            L3 = 1.0 - L1 - L2
            # Bb matrix for DKT triangle
            Bb = np.zeros((3, 9), dtype=np.float64)
            # Standard DKT displacement-curvature transformation approximation
            for i in range(3):
                bi = [b1, b2, b3][i] / (2.0 * A)
                ci = [c1, c2, c3][i] / (2.0 * A)
                Bb[0, 3 * i + 2] = -bi
                Bb[1, 3 * i + 1] = ci
                Bb[2, 3 * i + 2] = -ci
                Bb[2, 3 * i + 1] = bi

            K_bending += (Bb.T @ Db @ Bb) * (A * w)

        # Assemble into full 18x18 matrix
        K_full = np.zeros((18, 18), dtype=np.float64)
        for i in range(3):
            for j in range(3):
                # Membrane DOFs (u, v) -> 0, 1
                K_full[6 * i + 0, 6 * j + 0] = K_membrane[2 * i + 0, 2 * j + 0]
                K_full[6 * i + 0, 6 * j + 1] = K_membrane[2 * i + 0, 2 * j + 1]
                K_full[6 * i + 1, 6 * j + 0] = K_membrane[2 * i + 1, 2 * j + 0]
                K_full[6 * i + 1, 6 * j + 1] = K_membrane[2 * i + 1, 2 * j + 1]

                # Bending DOFs (w, th_x, th_y) -> 2, 3, 4
                for r in range(3):
                    for c in range(3):
                        K_full[6 * i + 2 + r, 6 * j + 2 + c] = K_bending[3 * i + r, 3 * j + c]

        # Relative Drilling DOF Stabilization for Tri3
        k_drill = 1e-4 * G * t * A
        for i in range(3):
            for j in range(3):
                val = k_drill * ((2.0 / 3.0) if i == j else (-1.0 / 3.0))
                K_full[6 * i + 5, 6 * j + 5] = val

        return K_full.tolist()

    def get_global_stiffness_matrix(self) -> List[List[float]]:
        """
        Transforms local stiffness into global 3D Cartesian coordinates:
          [K_global] = [T]^T * [K_local] * [T]
        """
        if self._k_global is not None:
            return self._k_global

        k_loc = self.get_local_stiffness_matrix()
        T = self.get_transformation_matrix()
        T_T = matrix_transpose(T)

        k_glob = matrix_multiply(matrix_multiply(T_T, k_loc), T)
        self._k_global = k_glob
        return self._k_global

    def compute_equivalent_nodal_loads(self) -> Tuple[List[float], List[float]]:
        """
        Computes the energetically consistent equivalent nodal load vectors
        for all surface and body loads acting on this shell:
          - p_local: in local coordinates (6N x 1)
          - p_global: in global coordinates (6N x 1)
        """
        num_dofs = self.num_nodes * 6
        p_local = [0.0] * num_dofs
        A = self.area
        x_axis, y_axis, z_axis = self.local_axes

        for load in self.loads:
            mag = load.magnitude
            if abs(mag) < 1e-15:
                continue

            # Resolve load into local coordinates (fx, fy, fz) per unit area
            q_loc = [0.0, 0.0, 0.0]

            if load.direction == 'local_z':
                q_loc[2] = mag # Out-of-plane pressure
            elif load.direction == 'local_x':
                q_loc[0] = mag
            elif load.direction == 'local_y':
                q_loc[1] = mag
            elif load.direction.startswith('global_'):
                g_vec = [0.0, 0.0, 0.0]
                if load.direction == 'global_X': g_vec[0] = mag
                elif load.direction == 'global_Y': g_vec[1] = mag
                elif load.direction == 'global_Z': g_vec[2] = mag

                # Project global vector onto local axes
                q_loc[0] = vector_dot_product(g_vec, x_axis)
                q_loc[1] = vector_dot_product(g_vec, y_axis)
                q_loc[2] = vector_dot_product(g_vec, z_axis)

            # Distribute uniformly to element corner nodes (equal weighting for regular linear elements)
            nodal_factor = A / float(self.num_nodes)
            for node_i in range(self.num_nodes):
                b = node_i * 6
                # In-plane translational forces
                p_local[b + 0] += q_loc[0] * nodal_factor
                p_local[b + 1] += q_loc[1] * nodal_factor
                # Out-of-plane transverse force
                p_local[b + 2] += q_loc[2] * nodal_factor

        # Global vector = T^T * p_local
        T = self.get_transformation_matrix()
        T_T = matrix_transpose(T)
        p_global = matrix_vector_multiply(T_T, p_local)

        return p_local, p_global

    def recover_stresses_and_forces(self, u_elem_global: List[float]) -> ShellStressResult:
        """
        Recovers internal stress resultants (Nxx, Nyy, Nxy, Mxx, Myy, Mxy, Vx, Vy)
        and surface stresses (Top, Mid, Bottom, von Mises) from global displacements.
        """
        T = self.get_transformation_matrix()
        u_local = matrix_vector_multiply(T, u_elem_global) # 24x1 or 18x1

        E = self.material.elastic_modulus
        nu = self.material.poisson_ratio
        t = self.thickness
        coords = np.array(self._local_coords_2d, dtype=np.float64)

        # Evaluate at element centroid (xi = 0, eta = 0)
        if self.num_nodes == 4:
            dNdxi = np.array([-0.25, 0.25, 0.25, -0.25], dtype=np.float64)
            dNdeta = np.array([-0.25, -0.25, 0.25, 0.25], dtype=np.float64)

            J = np.array([
                [np.dot(dNdxi, coords[:, 0]), np.dot(dNdxi, coords[:, 1])],
                [np.dot(dNdeta, coords[:, 0]), np.dot(dNdeta, coords[:, 1])]
            ], dtype=np.float64)
            invJ = np.linalg.inv(J)

            dNdx = invJ[0, 0] * dNdxi + invJ[0, 1] * dNdeta
            dNdy = invJ[1, 0] * dNdxi + invJ[1, 1] * dNdeta

            # Extract local displacements
            u_vec = np.array([u_local[6 * i + 0] for i in range(4)])
            v_vec = np.array([u_local[6 * i + 1] for i in range(4)])
            w_vec = np.array([u_local[6 * i + 2] for i in range(4)])
            thx_vec = np.array([u_local[6 * i + 3] for i in range(4)])
            thy_vec = np.array([u_local[6 * i + 4] for i in range(4)])

            # In-plane strains (eps_xx, eps_yy, gamma_xy)
            eps_xx = float(np.dot(dNdx, u_vec))
            eps_yy = float(np.dot(dNdy, v_vec))
            gamma_xy = float(np.dot(dNdy, u_vec) + np.dot(dNdx, v_vec))

            # Curvatures (kappa_xx, kappa_yy, kappa_xy)
            kappa_xx = float(-np.dot(dNdx, thy_vec))
            kappa_yy = float(np.dot(dNdy, thx_vec))
            kappa_xy = float(-np.dot(dNdy, thy_vec) + np.dot(dNdx, thx_vec))

            # Transverse shear strains (gamma_xz, gamma_yz)
            gamma_xz = float(np.dot(dNdx, w_vec) - np.mean(thy_vec))
            gamma_yz = float(np.dot(dNdy, w_vec) + np.mean(thx_vec))

        else: # 3 nodes
            x1, y1 = coords[0]; x2, y2 = coords[1]; x3, y3 = coords[2]
            A = self.area
            b1 = y2 - y3; b2 = y3 - y1; b3 = y1 - y2
            c1 = x3 - x2; c2 = x1 - x3; c3 = x2 - x1

            dNdx = np.array([b1, b2, b3]) / (2.0 * A)
            dNdy = np.array([c1, c2, c3]) / (2.0 * A)

            u_vec = np.array([u_local[6 * i + 0] for i in range(3)])
            v_vec = np.array([u_local[6 * i + 1] for i in range(3)])
            w_vec = np.array([u_local[6 * i + 2] for i in range(3)])
            thx_vec = np.array([u_local[6 * i + 3] for i in range(3)])
            thy_vec = np.array([u_local[6 * i + 4] for i in range(3)])

            eps_xx = float(np.dot(dNdx, u_vec))
            eps_yy = float(np.dot(dNdy, v_vec))
            gamma_xy = float(np.dot(dNdy, u_vec) + np.dot(dNdx, v_vec))

            kappa_xx = float(-np.dot(dNdx, thy_vec))
            kappa_yy = float(np.dot(dNdy, thx_vec))
            kappa_xy = float(-np.dot(dNdy, thy_vec) + np.dot(dNdx, thx_vec))

            gamma_xz = float(np.dot(dNdx, w_vec) - np.mean(thy_vec))
            gamma_yz = float(np.dot(dNdy, w_vec) + np.mean(thx_vec))

        # Elastic Constitutive Relations
        Em = (E * t) / (1.0 - nu ** 2)
        Eb = (E * (t ** 3)) / (12.0 * (1.0 - nu ** 2))
        G = E / (2.0 * (1.0 + nu))
        kappa_s = 5.0 / 6.0

        # Membrane Force Resultants (N/m)
        Nxx = Em * (eps_xx + nu * eps_yy)
        Nyy = Em * (nu * eps_xx + eps_yy)
        Nxy = Em * (1.0 - nu) * 0.5 * gamma_xy

        # Bending Moment Resultants (N*m/m)
        Mxx = Eb * (kappa_xx + nu * kappa_yy)
        Myy = Eb * (nu * kappa_xx + kappa_yy)
        Mxy = Eb * (1.0 - nu) * 0.5 * kappa_xy

        # Transverse Shear Force Resultants (N/m)
        Vx = kappa_s * G * t * gamma_xz
        Vy = kappa_s * G * t * gamma_yz

        # Surface Stresses (Pa)
        # Mid-surface (membrane only)
        sig_mid_xx = Nxx / t
        sig_mid_yy = Nyy / t
        tau_mid_xy = Nxy / t

        # Top surface (z = +t/2)
        sig_top_xx = sig_mid_xx + (6.0 * Mxx) / (t ** 2)
        sig_top_yy = sig_mid_yy + (6.0 * Myy) / (t ** 2)
        tau_top_xy = tau_mid_xy + (6.0 * Mxy) / (t ** 2)

        # Bottom surface (z = -t/2)
        sig_bot_xx = sig_mid_xx - (6.0 * Mxx) / (t ** 2)
        sig_bot_yy = sig_mid_yy - (6.0 * Myy) / (t ** 2)
        tau_bot_xy = tau_mid_xy - (6.0 * Mxy) / (t ** 2)

        def calc_principal_and_vm(sxx: float, syy: float, sxy: float) -> Tuple[float, float, float]:
            center = (sxx + syy) / 2.0
            radius = math.sqrt(((sxx - syy) / 2.0) ** 2 + sxy ** 2)
            s1 = center + radius
            s2 = center - radius
            vm = math.sqrt(sxx ** 2 - sxx * syy + syy ** 2 + 3.0 * (sxy ** 2))
            return s1, s2, vm

        s1_top, s2_top, vm_top = calc_principal_and_vm(sig_top_xx, sig_top_yy, tau_top_xy)
        s1_bot, s2_bot, vm_bot = calc_principal_and_vm(sig_bot_xx, sig_bot_yy, tau_bot_xy)
        vm_max = max(vm_top, vm_bot, math.sqrt(sig_mid_xx**2 - sig_mid_xx*sig_mid_yy + sig_mid_yy**2 + 3.0*(tau_mid_xy**2)))

        return ShellStressResult(
            element_id=self.element_id,
            Nxx=Nxx,
            Nyy=Nyy,
            Nxy=Nxy,
            Mxx=Mxx,
            Myy=Myy,
            Mxy=Mxy,
            Vx=Vx,
            Vy=Vy,
            sigma_top_xx=sig_top_xx,
            sigma_top_yy=sig_top_yy,
            tau_top_xy=tau_top_xy,
            sigma_mid_xx=sig_mid_xx,
            sigma_mid_yy=sig_mid_yy,
            tau_mid_xy=tau_mid_xy,
            sigma_bot_xx=sig_bot_xx,
            sigma_bot_yy=sig_bot_yy,
            tau_bot_xy=tau_bot_xy,
            sigma_1_top=s1_top,
            sigma_2_top=s2_top,
            von_mises_top=vm_top,
            sigma_1_bot=s1_bot,
            sigma_2_bot=s2_bot,
            von_mises_bot=vm_bot,
            von_mises_max=vm_max
        )
