# ARCHITECTURE SPECIFICATION — STRUCTURE-X ULTIMATE

## 1. Architectural Principles

STRUCTURE-X ULTIMATE is designed around five core engineering architectural pillars:
1. **Separation of Concerns**: Mathematical foundations, geometric modeling, validation diagnostics, and visualization rendering remain decoupled.
2. **Domain-Driven Strict Typing**: Every structural entity (Joints, Elements, Sections, Materials, Load Cases) is strongly typed in TypeScript and validated at runtime using Zod schemas.
3. **Traceability & Diagnostics**: Every calculation, error, and assumption is surfaced with structured error codes (`E1000`–`E6999`) and actionable remediation suggestions.
4. **Precision Dimensional Handling**: Dimensional quantities are normalized to canonical SI units internally while supporting arbitrary user unit conversions with zero numerical drift.
5. **Full-Stack Extensibility**: Seamless client-server integration with Express API routing and modular persistence repository.

---

## 2. System Architecture Layers

```
+-------------------------------------------------------------------------+
|                           CLIENT TIER (React 19)                       |
|  +-------------------+  +-------------------+  +---------------------+  |
|  | CAD Command Ribbon|  | 3D WebGL Viewport |  | Property Inspector  |  |
|  +-------------------+  +-------------------+  +---------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                ProjectStore (State, Undo/Redo, AutoSave)          |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                                    |
                                    v (REST API / JSON)
+-------------------------------------------------------------------------+
|                        BACKEND TIER (Express 4)                         |
|  +-------------------+  +-------------------+  +---------------------+  |
|  |  /api/projects    |  |  /api/validate    |  |  /api/units         |  |
|  +-------------------+  +-------------------+  +---------------------+  |
|  +-------------------+  +-------------------+  +---------------------+  |
|  |  /api/health      |  |  /api/logs        |  |  /api/tests/run     |  |
|  +-------------------+  +-------------------+  +---------------------+  |
|  +-------------------------------------------------------------------+  |
|  |                   ProjectRepository (Persistence)                 |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         CORE FOUNDATION SERVICES                        |
|  +-------------------------------------------------------------------+  |
|  | Units System (Dimensional Analysis, Multi-standard Converter)     |  |
|  | Model Integrity Validator (Topology, Constraints, Section Checks) |  |
|  | Structured Engineering Logger (Log Levels, Stream Buffer)        |  |
|  | Error Codes Catalog (E1000-E6999, Actionable Remediation)         |  |
|  | Testing Framework & Automated Verification Suites                 |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 3. Core Modules & Responsibilities

### 3.1 Domain Schema (`src/core/schema/` & `src/types/domain.ts`)
- Defines canonical structural entities with strict field types.
- Provides runtime Zod schema parsing (`StructuralModelSchema.safeParse()`).

### 3.2 Units System (`src/core/units/`)
- Encapsulates physical dimensions: Length, Force, Moment, Stress, Distributed Force, Area Force, Unit Weight, and Temperature.
- Standard systems: `kN-m, °C`, `N-mm, °C`, `kip-ft, °F`, `kip-in, °F`, `kgf-cm, °C`.

### 3.3 Diagnostic Validation Engine (`src/core/validation/`)
- Analyzes models before solving:
  - Detects orphan nodes (`E1001`).
  - Detects zero-length frame members (`E1002`).
  - Flags missing or non-existent section assignments (`E2001`).
  - Checks for non-positive section area/inertias (`E2003`).
  - Validates ground support boundary conditions (`E3001`).

### 3.4 State & Project History Management (`src/core/state/`)
- Manages active working model in memory.
- Implements linear history stack (`undo()` / `redo()`) up to configured limits.
- Manages auto-save intervals to localStorage and repository backend.

### 3.5 Project Repository & REST API (`src/server/`)
- Repository interface for project creation, listing, retrieval, mutation, and validation.
- Standardized RESTful endpoints under `/api/*`.

### 3.6 Automated Testing Harness (`src/test/`)
- Integrated test runners for units, schemas, models, persistence, and state.
- Capable of execution via CLI (`npm test`) or API (`/api/tests/run`).
