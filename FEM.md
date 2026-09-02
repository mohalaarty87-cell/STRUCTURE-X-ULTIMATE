# FINITE ELEMENT METHOD (FEM) SPECIFICATION — STRUCTURE-X ULTIMATE

## 1. 3D Spatial Frame Element Formulation

Each 1D frame member is discretized as an elastic 3D beam element connecting 2 joints (Node $i$ and Node $j$) with 6 degrees of freedom (DOF) per node:
$$\{d\} = \begin{bmatrix} u_{xi} & u_{yi} & u_{zi} & \theta_{xi} & \theta_{yi} & \theta_{zi} & u_{xj} & u_{yj} & u_{zj} & \theta_{xj} & \theta_{yj} & \theta_{zj} \end{bmatrix}^T$$

### Local Element Stiffness Matrix $[k_e]$ ($12 \times 12$)
The element stiffness matrix incorporates:
- **Axial action**: $k_{axial} = \frac{E A}{L}$
- **Torsion action (St. Venant)**: $k_{torsion} = \frac{G J}{L}$
- **Bending about local $z$-axis (major axis, $I_z$)** with optional Timoshenko shear deformation ($\Phi_y$):
  $$\Phi_y = \frac{12 E I_z}{G A_{s,y} L^2}$$
- **Bending about local $y$-axis (minor axis, $I_y$)** with optional Timoshenko shear deformation ($\Phi_z$):
  $$\Phi_z = \frac{12 E I_y}{G A_{s,z} L^2}$$

#### Explicit Sub-Matrices (Euler-Bernoulli / Timoshenko):
- Bending about $z$ ($v_i, \theta_{zi}, v_j, \theta_{zj}$):
  $$k_{b,z} = \frac{E I_z}{(1+\Phi_y) L^3} \begin{bmatrix} 12 & 6L & -12 & 6L \\ 6L & (4+\Phi_y)L^2 & -6L & (2-\Phi_y)L^2 \\ -12 & -6L & 12 & -6L \\ 6L & (2-\Phi_y)L^2 & -6L & (4+\Phi_y)L^2 \end{bmatrix}$$
- Bending about $y$ ($w_i, \theta_{yi}, w_j, \theta_{yj}$):
  $$k_{b,y} = \frac{E I_y}{(1+\Phi_z) L^3} \begin{bmatrix} 12 & -6L & -12 & -6L \\ -6L & (4+\Phi_z)L^2 & 6L & (2-\Phi_z)L^2 \\ -12 & 6L & 12 & 6L \\ -6L & (2-\Phi_z)L^2 & 6L & (4+\Phi_z)L^2 \end{bmatrix}$$

---

## 2. Coordinate Transformation Matrix $[T]$ ($12 \times 12$)

Transformation from local member axes $(\hat{x}, \hat{y}, \hat{z})$ to global Cartesian axes $(X, Y, Z)$:
$$\{d_{local}\} = [T] \{d_{global}\}$$
$$[K_{e,global}] = [T]^T [k_e] [T]$$

Where $[T] = \operatorname{diag}([R], [R], [R], [R])$ is a block-diagonal matrix built from the $3 \times 3$ direction cosine matrix $[R]$:
$$[R] = \begin{bmatrix} r_{11} & r_{12} & r_{13} \\ r_{21} & r_{22} & r_{23} \\ r_{31} & r_{32} & r_{33} \end{bmatrix}$$
- Longitudinal axis: $\vec{r}_1 = \frac{\vec{x}_j - \vec{x}_i}{L}$
- Transverse and normal axes $\vec{r}_2, \vec{r}_3$ are established via orthogonal cross products with reference orientation vector $\vec{v}_{ref}$ and member roll angle $\beta$.

---

## 3. Global Assembly & Sparse Linear Solver

### 1. Global Degree-of-Freedom Mapping
- $N$ joints yield $6N$ total system DOFs: $[UX, UY, UZ, RX, RY, RZ]$.
- DOF partitioning: Partitioned into free degrees of freedom ($f$) and restrained degrees of freedom ($r$):
  $$\begin{bmatrix} K_{ff} & K_{fr} \\ K_{rf} & K_{rr} \end{bmatrix} \begin{bmatrix} u_f \\ u_r \end{bmatrix} = \begin{bmatrix} P_f \\ P_r + R_r \end{bmatrix}$$

### 2. Equivalent Nodal Load Vector $\{P_{global}\}$
Distributed loads $w(x)$ along member spans are converted into energetically conjugate equivalent nodal forces:
$$\{p_e^{equiv}\} = \int_0^L [N(x)]^T \{w(x)\} \, dx$$
$$\{P_{global}\} = \sum_e [T]^T \{p_e^{equiv}\} + \{P_{nodal}\}$$

### 3. Sparse Solution
- Assembled via Dictionary of Keys (DOK) sparse matrix format and solved via `scipy.sparse.linalg.spsolve` (SuperLU / sparse LU factorization).
- Equilibrium solution:
  $$u_f = [K_{ff}]^{-1} (P_f - [K_{fr}] u_r)$$
- Reactions at all restrained supports:
  $$\{R\} = [K_{global}] \{U_{full}\} - \{P_{global}\}$$

---

## 4. Internal Force Recovery & Span Diagrams

For each member, local end displacements are recovered:
$$\{u_{local}\} = [T] \{U_{elem,global}\}$$
$$\{f_{local}\} = [k_e] \{u_{local}\} - \{p_e^{equiv}\}$$

At any station $x \in [0, L]$ along the member:
- **Axial Force**: $N(x) = N_0 + \int_0^x w_x(\xi) \, d\xi$
- **Shear Force (local y)**: $V_2(x) = V_{2,0} + \int_0^x w_y(\xi) \, d\xi$
- **Shear Force (local z)**: $V_3(x) = V_{3,0} + \int_0^x w_z(\xi) \, d\xi$
- **Torsion Moment**: $T(x) = T_0$
- **Bending Moment (about local y)**: $M_2(x) = M_{2,0} - V_{3,0} x - \int_0^x w_z(\xi)(x-\xi) \, d\xi$
- **Bending Moment (about local z)**: $M_3(x) = M_{3,0} + V_{2,0} x + \int_0^x w_y(\xi)(x-\xi) \, d\xi$

---

## 5. 3D Shell & Plate Element Formulation (Phase 05)

Planar slabs, shear walls, and area structural entities are discretized into 4-node quadrilateral (Quad4) and 3-node triangular (Tri3) shell elements with 6 DOFs per node ($u, v, w, \theta_x, \theta_y, \theta_z$).

### 1. Membrane Action (In-Plane Plane Stress)
- Bilinear isoparametric formulation:
  $$\begin{Bmatrix} \epsilon_{xx} \\ \epsilon_{yy} \\ \gamma_{xy} \end{Bmatrix} = [B_m] \{d_m\}$$
- Plane stress constitutive matrix:
  $$[D_m] = \frac{E t}{1 - \nu^2} \begin{bmatrix} 1 & \nu & 0 \\ \nu & 1 & 0 \\ 0 & 0 & \frac{1-\nu}{2} \end{bmatrix}$$
- Drilling DOF formulation: Integrated with relative shear modulus stiffness $K_{\theta z} = 0.05 \cdot G t A$ to ensure complete rigid-body mode invariance.

### 2. Plate Bending & Transverse Shear (Reissner-Mindlin)
- Transverse deflection $w$ and normal rotations $\theta_x, \theta_y$:
  $$\begin{Bmatrix} \kappa_{xx} \\ \kappa_{yy} \\ \kappa_{xy} \end{Bmatrix} = \begin{Bmatrix} -\frac{\partial \theta_y}{\partial x} \\ \frac{\partial \theta_x}{\partial y} \\ -\frac{\partial \theta_y}{\partial y} + \frac{\partial \theta_x}{\partial x} \end{Bmatrix} = [B_b] \{d_b\}$$
  $$\begin{Bmatrix} \gamma_{xz} \\ \gamma_{yz} \end{Bmatrix} = \begin{Bmatrix} \frac{\partial w}{\partial x} + \theta_y \\ \frac{\partial w}{\partial y} - \theta_x \end{Bmatrix} = [B_s] \{d_b\}$$
- Plate bending constitutive matrix:
  $$[D_b] = \frac{E t^3}{12(1-\nu^2)} \begin{bmatrix} 1 & \nu & 0 \\ \nu & 1 & 0 \\ 0 & 0 & \frac{1-\nu}{2} \end{bmatrix}, \quad [D_s] = \kappa G t \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$$
- Selective Reduced Integration (SRI) with centroidal shear evaluation and zero-energy checkerboard hourglass stabilization $\mathbf{h} = [1, -1, 1, -1]^T$ to eliminate shear locking across all thickness ratios $t/L$.

### 3. Shell Stress & Internal Force Recovery
At element centroids and integration points:
- **In-plane membrane forces**: $N_{xx} = \int \sigma_{xx} dz$, $N_{yy} = \int \sigma_{yy} dz$, $N_{xy} = \int \tau_{xy} dz$ ($\text{kN/m}$)
- **Out-of-plane bending & twisting moments**: $M_{xx} = \int \sigma_{xx} z dz$, $M_{yy} = \int \sigma_{yy} z dz$, $M_{xy} = \int \tau_{xy} z dz$ ($\text{kN}\cdot\text{m/m}$)
- **Transverse shear forces**: $V_x = \int \tau_{xz} dz$, $V_y = \int \tau_{yz} dz$ ($\text{kN/m}$)
- **Top & bottom surface stresses**: $\sigma_{xx}^{\pm} = \frac{N_{xx}}{t} \pm \frac{6 M_{xx}}{t^2}$, $\sigma_{yy}^{\pm} = \frac{N_{yy}}{t} \pm \frac{6 M_{yy}}{t^2}$, $\tau_{xy}^{\pm} = \frac{N_{xy}}{t} \pm \frac{6 M_{xy}}{t^2}$
- **Equivalent Von Mises stresses**:
  $$\sigma_{vm} = \sqrt{\sigma_{xx}^2 - \sigma_{xx}\sigma_{yy} + \sigma_{yy}^2 + 3\tau_{xy}^2}$$


