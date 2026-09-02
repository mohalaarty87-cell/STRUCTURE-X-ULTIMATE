# CHANGELOG — STRUCTURE-X ULTIMATE

All notable changes to the STRUCTURE-X ULTIMATE structural analysis and design platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to strict engineering numerical traceability.

---

## [Phase 05] - Shell Finite Element Engine (Slabs, Shear Walls, Area Elements)

### Added
- **3D Shell & Plate Finite Element (`engine.fem.shell_element_3d.ShellElement3D`)**:
  - Full $24 \times 24$ (Quad4) and $18 \times 18$ (Tri3) 6-DOF per node element formulation.
  - In-plane membrane action via plane stress elasticity with drilling rotation degree-of-freedom formulation ($K_{\theta z} = 0.05 G t A$).
  - Reissner-Mindlin thick/thin plate bending formulation with transverse shear deformation.
  - Selective Reduced Integration (SRI) with centroidal shear evaluation and zero-energy checkerboard hourglass stabilization $\mathbf{h} = [1, -1, 1, -1]^T$ to eliminate shear locking and spurious kinematics.
  - Transformation $[T]$ between 3D global Cartesian space and local element coordinate systems.
  - Equivalent surface load integration for uniform pressures, surface tractions, and vertical gravity dead loads.
  - High-precision stress and internal action recovery: $N_{xx}, N_{yy}, N_{xy}$, $M_{xx}, M_{yy}, M_{xy}$, $V_x, V_y$, top/bottom principal stresses, and Von Mises equivalent stress $\sigma_{vm}$.
- **Conforming Finite Element Meshing Engine (`engine.fem.meshing.ShellMeshGenerator`)**:
  - Automatic quadrilateral and triangular grid generation for arbitrary 3D planar polygons.
  - Openings cutout filtering and conforming boundary discretization for doors, windows, and floor penetrations.
  - Mesh quality verification suite assessing element aspect ratio ($AR$), minimum interior angle ($\theta_{min}$), maximum interior angle ($\theta_{max}$), and Jacobian determinant positivity.
  - Automatic co-located boundary node merging ($\epsilon = 10^{-4}\text{ m}$) ensuring 6-DOF displacement compatibility between shell boundaries and structural frame columns/beams.
- **5 Canonical Shell Benchmark Suites (`engine.fem.shell_benchmarks`)**:
  - `SBM-01`: Simply supported square plate with uniform surface pressure (Navier 2D Fourier series deflection, reactions, bending moments).
  - `SBM-02`: Clamped square plate under central point load (Roark/Timoshenko plate solution).
  - `SBM-03`: Deep cantilever shear wall under lateral shear (Timoshenko flexure and shear deformation with base overturning moment).
  - `SBM-04`: Perforated shear wall with central window opening (mesh filtering, mesh quality, and 2D static equilibrium).
  - `SBM-05`: 3D multi-element coupled building combining 4 RC columns, 4 RC edge beams, and an integrated 16-element RC floor slab shell under lateral shear and gravity loads.
  - **Verification Result**: 16/16 Verification checks PASSED (100.0% verified). Combined verification: 40/40 tests passing across Frame and Shell engines.

---

## [Phase 04] - Finite Element Analysis (FEM) 3D Frame Engine

### Added
- **Core 3D Spatial Frame Element (`engine.fem.frame_element_3d.FrameElement3D`)**:
  - Full $12 \times 12$ elastic stiffness matrix accounting for Axial, St. Venant Torsion, Bending about local $y$ (minor) and local $z$ (major).
  - Shear deformation coupling ($\Phi_y, \Phi_z$) for Timoshenko beam formulation.
  - Arbitrary spatial 3D coordinate transformation $[T]$ with direction cosines and orientation roll angle $\beta$.
  - Exact Equivalent Nodal Load (ENL) integration for uniform and point member loads along member spans.
  - High-resolution internal force recovery ($N, V_2, V_3, T, M_2, M_3$) evaluated at discrete member stations.
- **Global FEM Solver & Degree-of-Freedom Mapping (`engine.fem.solver_core.FEMSolver3D`)**:
  - 6-DOF per joint node numbering and degree-of-freedom partitioning ($K_{ff}, K_{fr}, K_{rf}, K_{rr}$).
  - Sparse Dictionary of Keys (DOK) global matrix assembly and SuperLU sparse solver integration (`scipy.sparse.linalg.spsolve`).
  - Prescribed displacement handling and full support reaction force & moment computation ($R_x, R_y, R_z, M_x, M_y, M_z$).
- **5 Canonical Benchmark Verification Suites (`engine.fem.verification_benchmarks`)**:
  - `BM-01`: Linear elastic axial bar tension verification (Hooke's law).
  - `BM-02`: Euler-Bernoulli cantilever beam under tip point load (deflection, slope, shear, moment).
  - `BM-03`: Simply supported beam under uniformly distributed gravity load (deflection, reactions, bending moment).
  - `BM-04`: 2D rigid portal frame lateral drift and shear distribution.
  - `BM-05`: Small 3D spatial multi-member frame under bi-axial lateral shear and gravity loads with 6-DOF spatial coupling.
  - **Verification Result**: 24/24 Verification checks PASSED with relative error $< 0.0002\%$ against exact analytical targets.

---

## [Phase 02] - Professional Engineering UI & 3D Viewport

### Added
- **10 Modular 3D WebGL Rendering Layers**:
  - `GridLayer`: Coordinate grids, axes, grid bubbles, and plane markers.
  - `StoryLayer`: Story levels, elevation planes, floor boundary markers.
  - `FrameLayer`: 3D extruded solid geometry for columns, beams, and structural members.
  - `ShellLayer`: 2D finite planar shells and slabs with thickness offsets.
  - `WallLayer`: Shear wall panels with thickness representation.
  - `LoadLayer`: Point loads, distributed line loads, surface pressure loads with magnitude tags.
  - `SupportLayer`: Boundary restraints (Fixed footings, Pinned, Roller).
  - `ResultLayer`: Moment diagrams (M3), Shear force diagrams (V2), Axial force diagrams (P), Deflected shapes.
  - `SelectionLayer`: High-contrast bounding selection wireframes and highlighted cages.
  - `AnnotationLayer`: Section callouts, story labels, node IDs, dimension strings.
- **LayerManager Engine**:
  - Centralized coordinator managing layer lifecycle, visibility toggles, and resource disposal.
- **Camera System & Controls**:
  - `CameraController` supporting Perspective & Orthographic parallel projections.
  - Preset camera transitions: Plan (Top XY), Elevation (XZ), Elevation (YZ), 3D Isometric (NE/NW/SE/SW), Fit Model Extents.
  - Interactive mouse Orbit (Left drag), Pan (Middle/Right drag), Zoom (Scroll wheel).
- **3D ViewCube Navigation Gizmo**:
  - Interactive 3D cube in the top right of the viewport with clickable planar and corner facets.
- **Floating Viewport HUD**:
  - Story level filtering, Projection switch (PERS/ORTHO), Display mode dropdown, and 10 Layer visibility switches.
- **CAD Toolbar & Model Explorer**:
  - Extended CAD toolbar with Select, Joint, Beam, Column, Slab, Wall, Support, Load, Measure, and Snaps.
  - Enhanced Model Explorer tree with search filter for Stories, Grids, Materials, Sections, Elements, Supports, and Loads.
- **Engineering CLI Console & Diagnostics**:
  - Command line prompt with autocomplete and command execution (`select`, `fit`, `view`, `layer`, `display`, `stats`, `units`, `help`).
  - Live diagnostics and engine log streaming.

---

## [Phase 01] - Project Foundation Architecture

### Added
- **Backend Architecture & REST API**:
  - Express server (`server.ts`) configured on port 3000 (`0.0.0.0`) with Vite middleware in development and static production bundling via esbuild (`dist/server.cjs`).
  - RESTful endpoints: `/api/health`, `/api/projects`, `/api/projects/:id`, `/api/projects/:id/validate`, `/api/units/systems`, `/api/units/convert`, `/api/logs`, `/api/tests/run`.
- **Database Architecture & Project Repository**:
  - `ProjectRepository` implementing repository pattern with model versioning, revision management, and JSON serialization.
  - Pre-seeded benchmark models (2-Story RC Building Frame).
- **TypeScript Domain Types & Schemas**:
  - Exhaustive domain entity types (`NodePoint`, `FrameMember`, `PlanarSlab`, `SectionProperty`, `MaterialDefinition`, `GridSystem`, `StoryLevel`, `LoadPattern`, `LoadCombination`, `ProjectMetadata`).
  - Strict Zod validation schemas (`StructuralModelSchema`).
- **Units System Foundation**:
  - Dimensional analysis engine for Length, Force, Moment, Stress, Distributed Force, Area Force, Unit Weight, and Temperature.
  - Pre-configured unit systems: SI Metric Standard (`kN-m, °C`), SI Metric Millimeter (`N-mm, °C`), US Customary (`kip-ft, °F`), US Customary Inch (`kip-in, °F`), and MKS Metric (`kgf-cm, °C`).
  - High-precision bidirectional converter (`UnitConverter`).
- **Error Handling & Diagnostic Logging**:
  - Standardized engineering error codes catalog (`E1000`–`E6999`) with categorized severity levels (`INFO`, `WARNING`, `ERROR`, `CRITICAL`) and actionable remediation suggestions.
  - Structured `EngineeringError` class and structured `Logger` with in-memory ring buffer for UI console streaming.
- **Model Integrity Validation Subsystem**:
  - `ModelIntegrityValidator` performing topology checks, zero-length detection, section/material mapping integrity, and kinematic boundary constraint verification.
- **State Management & History**:
  - `ProjectStore` with linear undo/redo historical stack, dirty flag tracking, and automatic background saving.
- **Testing Framework**:
  - Automated test runner (`testRunner.ts`) with test suites for Units Conversion, Model Schema Validation, Repository Persistence, and State History.
  - CLI test execution command `npm test` (`src/test/runTests.ts`).
- **Configuration & Environment**:
  - Centralized configuration (`src/config/index.ts`) with numerical tolerances, feature flags, and environment variables.
  - Full-stack build scripts in `package.json` (`dev`, `build`, `start`, `test`, `lint`).
- **Documentation**:
  - `README.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`.
