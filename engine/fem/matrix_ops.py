"""
Linear Algebra and Sparse Matrix Operations
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
Seamlessly utilizes NumPy / SciPy when available, with a fast, high-precision pure Python fallback.
"""

from typing import List, Tuple, Dict, Optional
import math

try:
    import numpy as np
    import scipy.sparse as sps
    import scipy.sparse.linalg as spla
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None
    sps = None
    spla = None


def create_zero_matrix(rows: int, cols: int) -> List[List[float]]:
    """Create a rows x cols matrix initialized to 0.0."""
    return [[0.0 for _ in range(cols)] for _ in range(rows)]


def matrix_multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Matrix multiplication C = A * B."""
    if HAS_NUMPY:
        return (np.array(A, dtype=np.float64) @ np.array(B, dtype=np.float64)).tolist()
    
    rows_A = len(A)
    cols_A = len(A[0])
    cols_B = len(B[0])
    C = [[0.0 for _ in range(cols_B)] for _ in range(rows_A)]
    
    for i in range(rows_A):
        for k in range(cols_A):
            aik = A[i][k]
            if abs(aik) > 1e-18:
                for j in range(cols_B):
                    C[i][j] += aik * B[k][j]
    return C


def matrix_transpose(A: List[List[float]]) -> List[List[float]]:
    """Matrix transpose A^T."""
    if HAS_NUMPY:
        return np.array(A, dtype=np.float64).T.tolist()
    return [[A[j][i] for j in range(len(A))] for i in range(len(A[0]))]


def matrix_vector_multiply(A: List[List[float]], x: List[float]) -> List[float]:
    """Matrix-vector multiplication y = A * x."""
    if HAS_NUMPY:
        return (np.array(A, dtype=np.float64) @ np.array(x, dtype=np.float64)).tolist()
    
    rows = len(A)
    cols = len(x)
    y = [0.0 for _ in range(rows)]
    for i in range(rows):
        s = 0.0
        row = A[i]
        for j in range(cols):
            s += row[j] * x[j]
        y[i] = s
    return y


def vector_dot_product(u: List[float], v: List[float]) -> float:
    """Computes dot product of two vectors."""
    return sum(a * b for a, b in zip(u, v))


def vector_cross_product(u: List[float], v: List[float]) -> Tuple[float, float, float]:
    """Computes 3D cross product u x v."""
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0]
    )


def vector_length(v: List[float]) -> float:
    """Computes Euclidean norm of vector."""
    return math.sqrt(sum(x * x for x in v))


def vector_magnitude(v: List[float]) -> float:
    """Computes Euclidean norm of vector (alias for vector_length)."""
    return math.sqrt(sum(x * x for x in v))


def vector_normalize(v: List[float]) -> List[float]:
    """Normalizes vector to unit length."""
    mag = vector_length(v)
    if mag < 1e-15:
        return [0.0] * len(v)
    return [x / mag for x in v]


def transform_element_stiffness(k_local: List[List[float]], T: List[List[float]]) -> List[List[float]]:
    """
    Computes K_global = T^T * k_local * T for a 12x12 element.
    Optimized for block-diagonal transformation matrices.
    """
    if HAS_NUMPY:
        T_arr = np.array(T, dtype=np.float64)
        k_arr = np.array(k_local, dtype=np.float64)
        return (T_arr.T @ k_arr @ T_arr).tolist()
    
    # Block-wise or standard matrix multiplication
    T_T = matrix_transpose(T)
    temp = matrix_multiply(T_T, k_local)
    return matrix_multiply(temp, T)


def solve_linear_system(A: List[List[float]], b: List[float]) -> List[float]:
    """
    Solves A * x = b for x using NumPy/SciPy or LU Decomposition with partial pivoting.
    """
    n = len(A)
    if n == 0:
        return []
    
    if HAS_NUMPY:
        try:
            return np.linalg.solve(np.array(A, dtype=np.float64), np.array(b, dtype=np.float64)).tolist()
        except Exception:
            pass

    # High-precision LU decomposition with partial pivoting
    # Make deep copies
    M = [row[:] for row in A]
    x = b[:]
    
    # Pivoting order
    perm = list(range(n))

    for k in range(n):
        # Find pivot
        max_val = abs(M[k][k])
        max_row = k
        for i in range(k + 1, n):
            if abs(M[i][k]) > max_val:
                max_val = abs(M[i][k])
                max_row = i

        if max_val < 1e-15:
            raise ValueError(f"Singular stiffness matrix encountered at equation {k}. Structure may be kinematically unstable.")

        # Swap rows
        if max_row != k:
            M[k], M[max_row] = M[max_row], M[k]
            x[k], x[max_row] = x[max_row], x[k]
            perm[k], perm[max_row] = perm[max_row], perm[k]

        # Elimination
        pivot = M[k][k]
        for i in range(k + 1, n):
            factor = M[i][k] / pivot
            M[i][k] = factor
            for j in range(k + 1, n):
                M[i][j] -= factor * M[k][j]
            x[i] -= factor * x[k]

    # Back substitution
    for i in range(n - 1, -1, -1):
        s = x[i]
        for j in range(i + 1, n):
            s -= M[i][j] * x[j]
        x[i] = s / M[i][i]

    return x


def solve_sparse_system(dok_K: Dict[Tuple[int, int], float], 
                        free_dofs: List[int], 
                        p_free: List[float]) -> List[float]:
    """
    Solves K_ff * u_f = P_f using SciPy sparse direct solver (SuperLU) if available,
    or converts reduced dense block for direct solution.
    """
    n_free = len(free_dofs)
    if n_free == 0:
        return []

    # Map free DOF index to reduced index 0..n_free-1
    dof_map = {dof: idx for idx, dof in enumerate(free_dofs)}

    if HAS_NUMPY:
        rows = []
        cols = []
        data = []
        for (i, j), val in dok_K.items():
            if i in dof_map and j in dof_map:
                rows.append(dof_map[i])
                cols.append(dof_map[j])
                data.append(val)
        
        K_csr = sps.csr_matrix((data, (rows, cols)), shape=(n_free, n_free), dtype=np.float64)
        b_vec = np.array(p_free, dtype=np.float64)
        
        try:
            u_f = spla.spsolve(K_csr, b_vec)
            return u_f.tolist()
        except Exception:
            pass

    # Dense fallback for free DOFs
    K_dense = [[0.0 for _ in range(n_free)] for _ in range(n_free)]
    for (i, j), val in dok_K.items():
        if i in dof_map and j in dof_map:
            K_dense[dof_map[i]][dof_map[j]] += val

    return solve_linear_system(K_dense, p_free)
