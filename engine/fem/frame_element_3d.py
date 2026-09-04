"""
3D Spatial Frame Finite Element Formulation
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
Supports 3D Euler-Bernoulli and Timoshenko beam theory (shear deformation),
arbitrary spatial orientation, roll angles, end releases, and member loads.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import math

from .materials import Material
from .sections import CrossSection
from .matrix_ops import (
    create_zero_matrix,
    matrix_transpose,
    matrix_multiply,
    transform_element_stiffness,
    matrix_vector_multiply
)

@dataclass
class MemberLoad:
    """Distributed or concentrated load on a frame element."""
    load_type: str            # 'uniform', 'point', 'trapezoidal', 'triangular', 'temperature'
    direction: str            # 'local_x', 'local_y', 'local_z', 'global_X', 'global_Y', 'global_Z'
    w1: float = 0.0           # Load intensity at start (N/m or N)
    w2: float = 0.0           # Load intensity at end (N/m)
    dist_a: float = 0.0       # Start distance from node i (m)
    dist_b: float = 0.0       # End distance or point load position from node i (m)
    delta_t_uniform: float = 0.0    # deg C
    delta_t_gradient_y: float = 0.0 # deg C
    delta_t_gradient_z: float = 0.0 # deg C
    thermal_alpha: float = 1.0e-5   # 1/deg C

@dataclass
class MemberInternalForces:
    """Internal forces and moments at stations along a frame member."""
    stations: List[float]     # x coordinates [0, ..., L]
    N: List[float]            # Axial force (N, tension > 0)
    V2: List[float]           # Shear force along local y (N)
    V3: List[float]           # Shear force along local z (N)
    T: List[float]            # Torsional moment (N*m)
    M2: List[float]           # Bending moment about local y (N*m)
    M3: List[float]           # Bending moment about local z (N*m)


class FrameElement3D:
    """
    Two-node 3D Spatial Frame Element with 6 DOFs per node (12 DOFs total):
      Node i: (u_xi, u_yi, u_zi, theta_xi, theta_yi, theta_zi) -> (0, 1, 2, 3, 4, 5)
      Node j: (u_xj, u_yj, u_zj, theta_xj, theta_yj, theta_zj) -> (6, 7, 8, 9, 10, 11)
    """

    def __init__(
        self,
        element_id: str,
        start_node_id: str,
        end_node_id: str,
        start_coords: Tuple[float, float, float],
        end_coords: Tuple[float, float, float],
        material: Material,
        section: CrossSection,
        rotation_angle_deg: float = 0.0,
        release_start: Optional[Dict[str, bool]] = None,
        release_end: Optional[Dict[str, bool]] = None,
        include_shear_deformation: bool = True
    ):
        self.id = element_id
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.start_coords = start_coords
        self.end_coords = end_coords
        self.material = material
        self.section = section
        self.rotation_angle_deg = rotation_angle_deg
        self.release_start = release_start or {}
        self.release_end = release_end or {}
        self.include_shear_deformation = include_shear_deformation
        
        self.loads: List[MemberLoad] = []

        # Compute geometry
        dx = end_coords[0] - start_coords[0]
        dy = end_coords[1] - start_coords[1]
        dz = end_coords[2] - start_coords[2]
        self.length = math.sqrt(dx * dx + dy * dy + dz * dz)
        
        if self.length < 1e-9:
            raise ValueError(f"Zero length element detected for element {element_id}.")

        self.dir_cosines = (dx / self.length, dy / self.length, dz / self.length)
        self._T_matrix: Optional[List[List[float]]] = None
        self._k_local: Optional[List[List[float]]] = None
        self._k_global: Optional[List[List[float]]] = None

    def add_load(self, load: MemberLoad):
        """Attach a member load to this frame element."""
        self.loads.append(load)

    def get_transformation_matrix(self) -> List[List[float]]:
        """
        Constructs the 12x12 coordinate transformation matrix [T].
        Local axes:
          - x_local: along member axis (from start to end node)
          - y_local: principal depth / vertical axis
          - z_local: principal width / lateral axis
        """
        if self._T_matrix is not None:
            return self._T_matrix

        cx, cy, cz = self.dir_cosines
        lxz = math.sqrt(cx * cx + cz * cz)
        beta = math.radians(self.rotation_angle_deg)
        cos_b = math.cos(beta)
        sin_b = math.sin(beta)

        # 3x3 base direction cosine matrix R0
        if lxz < 1e-6:
            # Vertical column (along global Y)
            if cy > 0:  # Pointing up (+Y)
                # x_local = (0, 1, 0)
                # y_local = (-1, 0, 0)
                # z_local = (0, 0, 1)
                r1 = [0.0, 1.0, 0.0]
                r2 = [-1.0, 0.0, 0.0]
                r3 = [0.0, 0.0, 1.0]
            else:       # Pointing down (-Y)
                r1 = [0.0, -1.0, 0.0]
                r2 = [1.0, 0.0, 0.0]
                r3 = [0.0, 0.0, 1.0]
        else:
            # General non-vertical orientation (standard structural engineering web-up convention)
            # x_local = (cx, cy, cz)
            # y_local = (-cx*cy/lxz, lxz, -cy*cz/lxz)
            # z_local = (-cz/lxz, 0, cx/lxz)
            r1 = [cx, cy, cz]
            r2 = [-cx * cy / lxz, lxz, -cy * cz / lxz]
            r3 = [-cz / lxz, 0.0, cx / lxz]

        # Apply roll rotation angle beta about local x
        # y' = cos(beta) * y + sin(beta) * z
        # z' = -sin(beta) * y + cos(beta) * z
        r2_rot = [
            cos_b * r2[0] + sin_b * r3[0],
            cos_b * r2[1] + sin_b * r3[1],
            cos_b * r2[2] + sin_b * r3[2]
        ]
        r3_rot = [
            -sin_b * r2[0] + cos_b * r3[0],
            -sin_b * r2[1] + cos_b * r3[1],
            -sin_b * r2[2] + cos_b * r3[2]
        ]

        R = [
            r1,
            r2_rot,
            r3_rot
        ]

        # Assemble 12x12 block diagonal transformation matrix T
        T = create_zero_matrix(12, 12)
        for b in range(4):
            offset = b * 3
            for i in range(3):
                for j in range(3):
                    T[offset + i][offset + j] = R[i][j]

        self._T_matrix = T
        return T

    def get_local_stiffness_matrix(self) -> List[List[float]]:
        """
        Calculates the 12x12 local element stiffness matrix [k_e]
        accounting for axial, torsion, bending about local y & z,
        and shear deformation (Timoshenko theory).
        """
        if self._k_local is not None:
            return self._k_local

        E = self.material.E
        G = self.material.G
        A = self.section.A
        Iz = self.section.Iz
        Iy = self.section.Iy
        J = self.section.J
        L = self.length

        # Axial & Torsional coefficients
        k_axial = (E * A) / L
        k_torsion = (G * J) / L

        # Shear deformation parameters
        if self.include_shear_deformation and self.section.Asy > 0 and self.section.Asz > 0:
            phi_y = (12.0 * E * Iz) / (G * self.section.Asy * L * L)
            phi_z = (12.0 * E * Iy) / (G * self.section.Asz * L * L)
        else:
            phi_y = 0.0
            phi_z = 0.0

        # Bending in local x-y plane (about local z-axis) -> DOFs (1, 5, 7, 11)
        # uz-rotations and uy-translations
        c_y = 1.0 + phi_y
        k_vy1 = (12.0 * E * Iz) / ((L ** 3) * c_y)
        k_vym = (6.0 * E * Iz) / ((L ** 2) * c_y)
        k_mz1 = ((4.0 + phi_y) * E * Iz) / (L * c_y)
        k_mz2 = ((2.0 - phi_y) * E * Iz) / (L * c_y)

        # Bending in local x-z plane (about local y-axis) -> DOFs (2, 4, 8, 10)
        # uy-rotations and uz-translations
        c_z = 1.0 + phi_z
        k_vz1 = (12.0 * E * Iy) / ((L ** 3) * c_z)
        k_vzm = (6.0 * E * Iy) / ((L ** 2) * c_z)
        k_my1 = ((4.0 + phi_z) * E * Iy) / (L * c_z)
        k_my2 = ((2.0 - phi_z) * E * Iy) / (L * c_z)

        k = create_zero_matrix(12, 12)

        # 1. Axial (DOFs 0, 6)
        k[0][0] = k_axial
        k[0][6] = -k_axial
        k[6][0] = -k_axial
        k[6][6] = k_axial

        # 2. Torsion (DOFs 3, 9)
        k[3][3] = k_torsion
        k[3][9] = -k_torsion
        k[9][3] = -k_torsion
        k[9][9] = k_torsion

        # 3. Bending about local z (DOFs 1, 5, 7, 11)
        k[1][1] = k_vy1
        k[1][5] = k_vym
        k[1][7] = -k_vy1
        k[1][11] = k_vym

        k[5][1] = k_vym
        k[5][5] = k_mz1
        k[5][7] = -k_vym
        k[5][11] = k_mz2

        k[7][1] = -k_vy1
        k[7][5] = -k_vym
        k[7][7] = k_vy1
        k[7][11] = -k_vym

        k[11][1] = k_vym
        k[11][5] = k_mz2
        k[11][7] = -k_vym
        k[11][11] = k_mz1

        # 4. Bending about local y (DOFs 2, 4, 8, 10)
        # Sign convention: theta_y = -duz/dx
        k[2][2] = k_vz1
        k[2][4] = -k_vzm
        k[2][8] = -k_vz1
        k[2][10] = -k_vzm

        k[4][2] = -k_vzm
        k[4][4] = k_my1
        k[4][8] = k_vzm
        k[4][10] = k_my2

        k[8][2] = -k_vz1
        k[8][4] = k_vzm
        k[8][8] = k_vz1
        k[8][10] = k_vzm

        k[10][2] = -k_vzm
        k[10][4] = k_my2
        k[10][8] = k_vzm
        k[10][10] = k_my1

        # Apply Member End Releases (Pin-Pin, Fixed-Pin, etc.)
        k = self._apply_releases(k)

        self._k_local = k
        return k

    def _apply_releases(self, k: List[List[float]]) -> List[List[float]]:
        """
        Modifies local stiffness matrix for released end hinges via static condensation.
        """
        # Releases map: 'mz', 'my', 't', 'fx', etc.
        rel_mz_i = self.release_start.get('mz', False) or self.release_start.get('rz', False)
        rel_mz_j = self.release_end.get('mz', False) or self.release_end.get('rz', False)
        rel_my_i = self.release_start.get('my', False) or self.release_start.get('ry', False)
        rel_my_j = self.release_end.get('my', False) or self.release_end.get('ry', False)
        rel_t_i = self.release_start.get('t', False) or self.release_start.get('rx', False)
        rel_t_j = self.release_end.get('t', False) or self.release_end.get('rx', False)

        E = self.material.E
        Iz = self.section.Iz
        Iy = self.section.Iy
        L = self.length

        # Pin-Pin about z (both ends pinned for Mz)
        if rel_mz_i and rel_mz_j:
            k[1][1] = 0.0; k[1][5] = 0.0; k[1][7] = 0.0; k[1][11] = 0.0
            k[5][1] = 0.0; k[5][5] = 0.0; k[5][7] = 0.0; k[5][11] = 0.0
            k[7][1] = 0.0; k[7][5] = 0.0; k[7][7] = 0.0; k[7][11] = 0.0
            k[11][1] = 0.0; k[11][5] = 0.0; k[11][7] = 0.0; k[11][11] = 0.0
        elif rel_mz_i: # Pinned at i, fixed at j (about z)
            k3 = (3.0 * E * Iz) / (L ** 3)
            k2 = (3.0 * E * Iz) / (L ** 2)
            k1 = (3.0 * E * Iz) / L
            k[1][1] = k3; k[1][5] = 0.0; k[1][7] = -k3; k[1][11] = k2
            k[5][1] = 0.0; k[5][5] = 0.0; k[5][7] = 0.0; k[5][11] = 0.0
            k[7][1] = -k3; k[7][5] = 0.0; k[7][7] = k3; k[7][11] = -k2
            k[11][1] = k2; k[11][5] = 0.0; k[11][7] = -k2; k[11][11] = k1
        elif rel_mz_j: # Fixed at i, pinned at j (about z)
            k3 = (3.0 * E * Iz) / (L ** 3)
            k2 = (3.0 * E * Iz) / (L ** 2)
            k1 = (3.0 * E * Iz) / L
            k[1][1] = k3; k[1][5] = k2; k[1][7] = -k3; k[1][11] = 0.0
            k[5][1] = k2; k[5][5] = k1; k[5][7] = -k2; k[5][11] = 0.0
            k[7][1] = -k3; k[7][5] = -k2; k[7][7] = k3; k[7][11] = 0.0
            k[11][1] = 0.0; k[11][5] = 0.0; k[11][7] = 0.0; k[11][11] = 0.0

        # Pin-Pin about y (both ends pinned for My)
        if rel_my_i and rel_my_j:
            k[2][2] = 0.0; k[2][4] = 0.0; k[2][8] = 0.0; k[2][10] = 0.0
            k[4][2] = 0.0; k[4][4] = 0.0; k[4][8] = 0.0; k[4][10] = 0.0
            k[8][2] = 0.0; k[8][4] = 0.0; k[8][8] = 0.0; k[8][10] = 0.0
            k[10][2] = 0.0; k[10][4] = 0.0; k[10][8] = 0.0; k[10][10] = 0.0
        elif rel_my_i: # Pinned at i, fixed at j (about y)
            k3 = (3.0 * E * Iy) / (L ** 3)
            k2 = (3.0 * E * Iy) / (L ** 2)
            k1 = (3.0 * E * Iy) / L
            k[2][2] = k3; k[2][4] = 0.0; k[2][8] = -k3; k[2][10] = -k2
            k[4][2] = 0.0; k[4][4] = 0.0; k[4][8] = 0.0; k[4][10] = 0.0
            k[8][2] = -k3; k[8][4] = 0.0; k[8][8] = k3; k[8][10] = k2
            k[10][2] = -k2; k[10][4] = 0.0; k[10][8] = k2; k[10][10] = k1
        elif rel_my_j: # Fixed at i, pinned at j (about y)
            k3 = (3.0 * E * Iy) / (L ** 3)
            k2 = (3.0 * E * Iy) / (L ** 2)
            k1 = (3.0 * E * Iy) / L
            k[2][2] = k3; k[2][4] = -k2; k[2][8] = -k3; k[2][10] = 0.0
            k[4][2] = -k2; k[4][4] = k1; k[4][8] = k2; k[4][10] = 0.0
            k[8][2] = -k3; k[8][4] = k2; k[8][8] = k3; k[8][10] = 0.0
            k[10][2] = 0.0; k[10][4] = 0.0; k[10][8] = 0.0; k[10][10] = 0.0

        # Torsion release
        if rel_t_i or rel_t_j:
            k[3][3] = 0.0; k[3][9] = 0.0
            k[9][3] = 0.0; k[9][9] = 0.0

        return k

    def get_local_geometric_stiffness_matrix(self, P: float) -> List[List[float]]:
        """
        Calculates 12x12 local geometric stiffness matrix [k_g] for axial force P.
        Sign convention: P > 0 is tension, P < 0 is compression.
        Under compression (P < 0), k_g reduces lateral stiffness (tangent K_T = K_E + K_G).
        """
        L = self.length
        if L <= 1e-9:
            return create_zero_matrix(12, 12)

        kg = create_zero_matrix(12, 12)
        if abs(P) < 1e-15:
            return kg

        # Bending in local x-y plane (about local z-axis) -> DOFs (1, 5, 7, 11)
        c1 = (6.0 * P) / (5.0 * L)
        c2 = P / 10.0
        c3 = (2.0 * P * L) / 15.0
        c4 = -(P * L) / 30.0

        kg[1][1] = c1;  kg[1][5] = c2;  kg[1][7] = -c1; kg[1][11] = c2
        kg[5][1] = c2;  kg[5][5] = c3;  kg[5][7] = -c2; kg[5][11] = c4
        kg[7][1] = -c1; kg[7][5] = -c2; kg[7][7] = c1;  kg[7][11] = -c2
        kg[11][1] = c2; kg[11][5] = c4; kg[11][7] = -c2; kg[11][11] = c3

        # Bending in local x-z plane (about local y-axis) -> DOFs (2, 4, 8, 10)
        # Note sign convention for theta_y = -duz/dx
        kg[2][2] = c1;   kg[2][4] = -c2;  kg[2][8] = -c1;  kg[2][10] = -c2
        kg[4][2] = -c2;  kg[4][4] = c3;   kg[4][8] = c2;   kg[4][10] = c4
        kg[8][2] = -c1;  kg[8][4] = c2;   kg[8][8] = c1;   kg[8][10] = c2
        kg[10][2] = -c2; kg[10][4] = c4;  kg[10][8] = c2;  kg[10][10] = c3

        # Torsion -> DOFs (3, 9)
        A = self.section.A
        if A > 1e-12:
            rp2 = (self.section.Iy + self.section.Iz) / A
            c_tor = (P * rp2) / L
            kg[3][3] = c_tor;  kg[3][9] = -c_tor
            kg[9][3] = -c_tor; kg[9][9] = c_tor

        # End releases modification if hinges are present
        rel_mz_i = self.release_start.get('mz', False) or self.release_start.get('rz', False)
        rel_mz_j = self.release_end.get('mz', False) or self.release_end.get('rz', False)
        if rel_mz_i or rel_mz_j:
            if rel_mz_i and rel_mz_j:
                kg[1][1] = P / L; kg[1][5] = 0.0; kg[1][7] = -P / L; kg[1][11] = 0.0
                kg[5][1] = 0.0;   kg[5][5] = 0.0; kg[5][7] = 0.0;    kg[5][11] = 0.0
                kg[7][1] = -P / L; kg[7][5] = 0.0; kg[7][7] = P / L; kg[7][11] = 0.0
                kg[11][1] = 0.0;  kg[11][5] = 0.0; kg[11][7] = 0.0;   kg[11][11] = 0.0

        rel_my_i = self.release_start.get('my', False) or self.release_start.get('ry', False)
        rel_my_j = self.release_end.get('my', False) or self.release_end.get('ry', False)
        if rel_my_i or rel_my_j:
            if rel_my_i and rel_my_j:
                kg[2][2] = P / L; kg[2][4] = 0.0; kg[2][8] = -P / L; kg[2][10] = 0.0
                kg[4][2] = 0.0;   kg[4][4] = 0.0; kg[4][8] = 0.0;    kg[4][10] = 0.0
                kg[8][2] = -P / L; kg[8][4] = 0.0; kg[8][8] = P / L; kg[8][10] = 0.0
                kg[10][2] = 0.0;  kg[10][4] = 0.0; kg[10][8] = 0.0;   kg[10][10] = 0.0

        return kg

    def get_global_geometric_stiffness_matrix(self, P: float) -> List[List[float]]:
        """Calculates [K_g,global] = [T]^T * [k_g,local] * [T] (12x12)."""
        kg_loc = self.get_local_geometric_stiffness_matrix(P)
        T = self.get_transformation_matrix()
        return transform_element_stiffness(kg_loc, T)

    def get_global_stiffness_matrix(self) -> List[List[float]]:
        """Calculates [K_e,global] = [T]^T * [k_e,local] * [T] (12x12)."""
        if self._k_global is not None:
            return self._k_global

        k_loc = self.get_local_stiffness_matrix()
        T = self.get_transformation_matrix()
        self._k_global = transform_element_stiffness(k_loc, T)
        return self._k_global

    def compute_equivalent_nodal_loads(self) -> Tuple[List[float], List[float]]:
        """
        Computes the Equivalent Nodal Load (ENL) vectors:
          - p_local: in local coordinates (12x1)
          - p_global: transferred to global coordinate system (12x1)
        Consistent with integral(N^T * w dx).
        """
        p_local = [0.0] * 12
        L = self.length
        T = self.get_transformation_matrix()

        for load in self.loads:
            # Transform global loads to local if needed
            w_loc_x = 0.0
            w_loc_y = 0.0
            w_loc_z = 0.0

            if load.direction == 'local_y':
                w_loc_y = load.w1
            elif load.direction == 'local_z':
                w_loc_z = load.w1
            elif load.direction == 'local_x':
                w_loc_x = load.w1
            elif load.direction.startswith('global_'):
                g_vec = [0.0, 0.0, 0.0]
                if load.direction == 'global_X':
                    g_vec[0] = load.w1
                elif load.direction == 'global_Y':
                    g_vec[1] = load.w1
                elif load.direction == 'global_Z':
                    g_vec[2] = load.w1
                
                # R * g_vec
                R = [T[0][:3], T[1][:3], T[2][:3]]
                w_loc_x = R[0][0] * g_vec[0] + R[0][1] * g_vec[1] + R[0][2] * g_vec[2]
                w_loc_y = R[1][0] * g_vec[0] + R[1][1] * g_vec[1] + R[1][2] * g_vec[2]
                w_loc_z = R[2][0] * g_vec[0] + R[2][1] * g_vec[1] + R[2][2] * g_vec[2]

            if load.load_type == 'uniform':
                # Uniform load along local y (bending about z)
                if abs(w_loc_y) > 1e-15:
                    p_local[1] += w_loc_y * L / 2.0
                    p_local[5] += w_loc_y * (L ** 2) / 12.0
                    p_local[7] += w_loc_y * L / 2.0
                    p_local[11] += -w_loc_y * (L ** 2) / 12.0

                # Uniform load along local z (bending about y)
                if abs(w_loc_z) > 1e-15:
                    p_local[2] += w_loc_z * L / 2.0
                    p_local[4] += -w_loc_z * (L ** 2) / 12.0
                    p_local[8] += w_loc_z * L / 2.0
                    p_local[10] += w_loc_z * (L ** 2) / 12.0

                # Uniform load along local x (axial)
                if abs(w_loc_x) > 1e-15:
                    p_local[0] += w_loc_x * L / 2.0
                    p_local[6] += w_loc_x * L / 2.0

            elif load.load_type == 'point':
                a = max(0.0, min(L, load.dist_a))
                b = L - a
                P = load.w1
                
                if load.direction in ('local_y', 'global_Y'):
                    Py = w_loc_y if load.direction.startswith('global') else P
                    if abs(Py) > 1e-15:
                        p_local[1] += Py * (b ** 2) * (3 * a + b) / (L ** 3)
                        p_local[5] += Py * a * (b ** 2) / (L ** 2)
                        p_local[7] += Py * (a ** 2) * (a + 3 * b) / (L ** 3)
                        p_local[11] += -Py * (a ** 2) * b / (L ** 2)

                elif load.direction in ('local_z', 'global_Z'):
                    Pz = w_loc_z if load.direction.startswith('global') else P
                    if abs(Pz) > 1e-15:
                        p_local[2] += Pz * (b ** 2) * (3 * a + b) / (L ** 3)
                        p_local[4] += -Pz * a * (b ** 2) / (L ** 2)
                        p_local[8] += Pz * (a ** 2) * (a + 3 * b) / (L ** 3)
                        p_local[10] += Pz * (a ** 2) * b / (L ** 2)

                elif load.direction in ('local_x', 'global_X'):
                    Px = w_loc_x if load.direction.startswith('global') else P
                    if abs(Px) > 1e-15:
                        p_local[0] += Px * b / L
                        p_local[6] += Px * a / L

            elif load.load_type in ('trapezoidal', 'triangular'):
                # Trapezoidal load with w1 at start (dist_a) and w2 at end (dist_b)
                a = max(0.0, min(L, load.dist_a))
                b = L if load.dist_b is None or load.dist_b <= 0 else max(a, min(L, load.dist_b))
                lab = max(1e-9, b - a)
                w1_val = load.w1
                w2_val = load.w2

                # 4-point Gauss numerical quadrature over [a, b] for exact shape function integrals
                # integral( N_i(x) * w(x) dx )
                gauss_pts = [
                    (-0.8611363115940526, 0.34785484513745386),
                    (-0.3399810435848563, 0.6521451548625461),
                    (0.3399810435848563, 0.6521451548625461),
                    (0.8611363115940526, 0.34785484513745386)
                ]
                for xi_g, wt_g in gauss_pts:
                    x = 0.5 * (b + a) + 0.5 * lab * xi_g
                    s = x / L
                    w_x = w1_val + (w2_val - w1_val) * ((x - a) / lab)
                    dx = 0.5 * lab * wt_g

                    # Beam bending shape functions along local y
                    N1 = 1.0 - 3.0 * s**2 + 2.0 * s**3
                    N2 = L * (s - 2.0 * s**2 + s**3)
                    N3 = 3.0 * s**2 - 2.0 * s**3
                    N4 = L * (-s**2 + s**3)

                    if abs(w_loc_y) > 1e-15 or (load.direction in ('local_y', 'global_Y') and abs(w_x) > 1e-15):
                        wy = w_x if load.direction in ('local_y', 'global_Y') else (w_loc_y * (w_x / max(1e-9, w1_val)))
                        p_local[1] += wy * N1 * dx
                        p_local[5] += wy * N2 * dx
                        p_local[7] += wy * N3 * dx
                        p_local[11] += wy * N4 * dx

                    if abs(w_loc_z) > 1e-15 or (load.direction in ('local_z', 'global_Z') and abs(w_x) > 1e-15):
                        wz = w_x if load.direction in ('local_z', 'global_Z') else (w_loc_z * (w_x / max(1e-9, w1_val)))
                        p_local[2] += wz * N1 * dx
                        p_local[4] += -wz * N2 * dx
                        p_local[8] += wz * N3 * dx
                        p_local[10] += -wz * N4 * dx

                    if abs(w_loc_x) > 1e-15 or (load.direction in ('local_x', 'global_X') and abs(w_x) > 1e-15):
                        wx = w_x if load.direction in ('local_x', 'global_X') else (w_loc_x * (w_x / max(1e-9, w1_val)))
                        p_local[0] += wx * (1.0 - s) * dx
                        p_local[6] += wx * s * dx

            elif load.load_type == 'temperature':
                E = self.material.elastic_modulus
                A = self.section.area
                Iz = self.section.moment_of_inertia_z
                Iy = self.section.moment_of_inertia_y
                h = max(0.01, self.section.depth)
                b = max(0.01, self.section.width)
                alpha = load.thermal_alpha

                # 1. Uniform delta T -> axial fixed-end reaction equivalent
                if abs(load.delta_t_uniform) > 1e-9:
                    N_th = E * A * alpha * load.delta_t_uniform
                    # Fixed end forces: -N_th at start (node i), +N_th at end (node j)
                    # Equivalent nodal forces: +N_th at start, -N_th at end
                    p_local[0] += -N_th
                    p_local[6] += N_th

                # 2. Thermal gradient along Y (top hotter than bottom)
                if abs(load.delta_t_gradient_y) > 1e-9:
                    # M_z,th = E * Iz * alpha * (delta_t_gradient_y / h)
                    M_z_th = E * Iz * alpha * (load.delta_t_gradient_y / h)
                    p_local[5] += M_z_th
                    p_local[11] += -M_z_th

                # 3. Thermal gradient along Z (left hotter than right)
                if abs(load.delta_t_gradient_z) > 1e-9:
                    M_y_th = E * Iy * alpha * (load.delta_t_gradient_z / b)
                    p_local[4] += -M_y_th
                    p_local[10] += M_y_th

        # p_global = T^T * p_local
        T_T = matrix_transpose(T)
        p_global = matrix_vector_multiply(T_T, p_local)
        return p_local, p_global

    def compute_fixed_end_forces(self) -> Tuple[List[float], List[float]]:
        """Deprecated alias for compute_equivalent_nodal_loads."""
        return self.compute_equivalent_nodal_loads()

    def recover_internal_forces(
        self,
        u_global_elem: List[float],
        num_stations: int = 11
    ) -> MemberInternalForces:
        """
        Recovers local end actions and computes internal forces (N, V2, V3, T, M2, M3)
        at discrete stations along the beam member length.
        """
        T = self.get_transformation_matrix()
        k_loc = self.get_local_stiffness_matrix()
        p_enl_loc, _ = self.compute_equivalent_nodal_loads()

        # u_local = [T] * u_global
        u_loc = matrix_vector_multiply(T, u_global_elem)

        # f_local_actions = [k_loc] * u_loc - p_enl_loc
        f_loc_actions = matrix_vector_multiply(k_loc, u_loc)
        for i in range(12):
            f_loc_actions[i] -= p_enl_loc[i]

        L = self.length
        stations = [i * L / (num_stations - 1) for i in range(num_stations)]

        N_list = []
        V2_list = []
        V3_list = []
        T_list = []
        M2_list = []
        M3_list = []

        # Internal forces at start of member (station x = 0)
        # N: tension positive -> -f[0]
        # V2: shear along local y -> f[1]
        # V3: shear along local z -> f[2]
        # T: torsion -> -f[3]
        # M2: moment about local y -> -f[4]
        # M3: moment about local z -> -f[5]
        N0 = -f_loc_actions[0]
        V2_0 = f_loc_actions[1]
        V3_0 = f_loc_actions[2]
        T0 = -f_loc_actions[3]
        M2_0 = -f_loc_actions[4]
        M3_0 = -f_loc_actions[5]

        for x in stations:
            n_x = N0
            v2_x = V2_0
            v3_x = V3_0
            t_x = T0
            m2_x = M2_0 - V3_0 * x
            m3_x = M3_0 + V2_0 * x

            for load in self.loads:
                w_loc_y = 0.0
                w_loc_z = 0.0
                w_loc_x = 0.0

                if load.direction == 'local_y':
                    w_loc_y = load.w1
                elif load.direction == 'local_z':
                    w_loc_z = load.w1
                elif load.direction == 'local_x':
                    w_loc_x = load.w1
                elif load.direction.startswith('global_'):
                    g_vec = [0.0, 0.0, 0.0]
                    if load.direction == 'global_X':
                        g_vec[0] = load.w1
                    elif load.direction == 'global_Y':
                        g_vec[1] = load.w1
                    elif load.direction == 'global_Z':
                        g_vec[2] = load.w1
                    R = [T[0][:3], T[1][:3], T[2][:3]]
                    w_loc_x = R[0][0] * g_vec[0] + R[0][1] * g_vec[1] + R[0][2] * g_vec[2]
                    w_loc_y = R[1][0] * g_vec[0] + R[1][1] * g_vec[1] + R[1][2] * g_vec[2]
                    w_loc_z = R[2][0] * g_vec[0] + R[2][1] * g_vec[1] + R[2][2] * g_vec[2]

                if load.load_type == 'uniform':
                    if abs(w_loc_y) > 1e-15:
                        v2_x += w_loc_y * x
                        m3_x += 0.5 * w_loc_y * (x ** 2)

                    if abs(w_loc_z) > 1e-15:
                        v3_x += w_loc_z * x
                        m2_x -= 0.5 * w_loc_z * (x ** 2)

                    if abs(w_loc_x) > 1e-15:
                        n_x += w_loc_x * x

                elif load.load_type == 'point':
                    a = load.dist_a
                    if x >= a:
                        dx = x - a
                        P = load.w1
                        if load.direction in ('local_y', 'global_Y'):
                            Py = w_loc_y if load.direction.startswith('global') else P
                            v2_x += Py
                            m3_x += Py * dx
                        elif load.direction in ('local_z', 'global_Z'):
                            Pz = w_loc_z if load.direction.startswith('global') else P
                            v3_x += Pz
                            m2_x -= Pz * dx
                        elif load.direction in ('local_x', 'global_X'):
                            Px = w_loc_x if load.direction.startswith('global') else P
                            n_x += Px

            N_list.append(n_x)
            V2_list.append(v2_x)
            V3_list.append(v3_x)
            T_list.append(t_x)
            M2_list.append(m2_x)
            M3_list.append(m3_x)

        return MemberInternalForces(
            stations=stations,
            N=N_list,
            V2=V2_list,
            V3=V3_list,
            T=T_list,
            M2=M2_list,
            M3=M3_list
        )
