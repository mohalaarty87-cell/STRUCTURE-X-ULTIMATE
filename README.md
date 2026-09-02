# STRUCTURE-X ULTIMATE

## Professional Web-Based Structural Analysis, Modeling & Design Platform
**Version**: 4.2.0-PRO  
**Release Target**: Phase 01 Foundation Architecture  

STRUCTURE-X ULTIMATE is an original, scalable, browser-based 3D structural analysis and BIM modeling environment built for structural engineers and researchers.

---

## 1. Phase 01 System Foundation

Phase 01 establishes the enterprise-grade foundation for the entire STRUCTURE-X platform:

### 1.1 Frontend Architecture
- High-contrast, dense structural CAD interface with command ribbon, collapsible Model Explorer, 3D WebGL viewport (Three.js), docked Property Inspector, and real-time Status Bar.
- Multi-lingual support (English / Arabic RTL) and theme toggles.
- Zero UI-thread blocking with decoupled state management.

### 1.2 Backend Architecture
- Full-stack Express server running on port 3000 (`0.0.0.0`) with Vite middleware in development mode and static production bundling via esbuild (`dist/server.cjs`).
- Structured REST API endpoints for projects, model validation, unit conversions, diagnostic logging, and test execution.

### 1.3 Database & Project Repository
- Repository pattern (`ProjectRepository`) with versioning, revision bumping, snapshot serialization, and integrity validation.
- Seeded default benchmarks including multi-story reinforced concrete building frames.

### 1.4 TypeScript Domain Types & Zod Schemas
- Exhaustive structural domain models (`NodePoint`, `FrameMember`, `PlanarSlab`, `SectionProperty`, `MaterialDefinition`, `GridSystem`, `StoryLevel`, `LoadPattern`, `LoadCombination`, `ProjectMetadata`).
- Strict schema validation using Zod (`StructuralModelSchema`).

### 1.5 Precision Units System Foundation
- Dimensional analysis engine supporting SI Standard (`kN-m, °C`), SI Millimeter (`N-mm, °C`), US Customary (`kip-ft, °F`), US Customary Inch (`kip-in, °F`), and MKS Metric (`kgf-cm, °C`).
- Bidirectional converter with exact conversion factors for Force, Length, Moment, Stress, Distributed Loads, Area Loads, and Temperatures.

### 1.6 Error Handling & Diagnostic Logging
- Standardized engineering error codes catalog (`E1000`–`E6999`) with categorized severity levels (`INFO`, `WARNING`, `ERROR`, `CRITICAL`) and actionable remediation suggestions.
- Structured Logger with in-memory ring buffer, module tagging, and UI console stream integration.

### 1.7 Testing Framework & Verification Suite
- Self-contained automated testing framework with test suites for Units Conversion, Model Topology Validation, Project Repository CRUD, and Undo/Redo State History.

---

## 2. Getting Started

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
```
Launches the full-stack Express + Vite application on `http://0.0.0.0:3000`.

### Running Verification Tests
```bash
npm test
```
Executes the CLI test runner across all foundation verification test suites.

### Production Build
```bash
npm run build
npm start
```
Builds the client application and bundles the server into a single standalone `dist/server.cjs`.

---

## 3. Project Structure

```
├── server.ts                       # Express + Vite Full-Stack Entry Point
├── src/
│   ├── config/                     # Centralized App Configuration & Tolerances
│   │   └── index.ts
│   ├── core/
│   │   ├── errors/                 # Standardized Engineering Error Codes & Classes
│   │   │   ├── EngineeringError.ts
│   │   │   └── errorCodes.ts
│   │   ├── logging/                # Structured Engineering Logger & Buffer
│   │   │   └── Logger.ts
│   │   ├── schema/                 # Zod Structural Model Schemas
│   │   │   └── structuralModelSchema.ts
│   │   ├── state/                  # Project Store, Undo/Redo & AutoSave
│   │   │   └── ProjectStore.ts
│   │   ├── units/                  # Dimensional Analysis & Unit Converter
│   │   │   ├── unitConverter.ts
│   │   │   └── unitSystem.ts
│   │   └── validation/             # Model Integrity & Health Diagnostics
│   │       └── ModelIntegrityValidator.ts
│   ├── server/
│   │   ├── repository/             # Project Repository (CRUD & Persistence)
│   │   │   └── ProjectRepository.ts
│   │   └── routes/                 # Express REST API Routes
│   │       └── api.ts
│   ├── test/                       # Foundation Automated Test Harness
│   │   ├── modelValidation.test.ts
│   │   ├── projectRepository.test.ts
│   │   ├── runTests.ts
│   │   ├── stateHistory.test.ts
│   │   ├── testRunner.ts
│   │   └── unitConversion.test.ts
│   ├── types/                      # Domain & Structural TypeScript Types
│   │   ├── domain.ts
│   │   └── structure.ts
│   └── components/                 # CAD Viewports, Modals & Inspector
├── README.md
├── ARCHITECTURE.md
├── PROJECT_STATUS.md
└── CHANGELOG.md
```
