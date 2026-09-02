import { runUnitConversionTests } from './unitConversion.test';
import { runModelValidationTests } from './modelValidation.test';
import { runProjectRepositoryTests } from './projectRepository.test';
import { runStateHistoryTests } from './stateHistory.test';
import { runModelingEngineTests } from './modelingEngine.test';

export interface TestSuiteReport {
  timestamp: string;
  totalTests: number;
  passedCount: number;
  failedCount: number;
  allPassed: boolean;
  suites: {
    name: string;
    tests: { name: string; passed: boolean; message?: string }[];
  }[];
}

export function runAllVerificationSuites(): TestSuiteReport {
  const suites = [
    { name: 'Units System & Conversions', tests: runUnitConversionTests() },
    { name: 'Model Schema & Topology Validation', tests: runModelValidationTests() },
    { name: 'Project Repository & CRUD Persistence', tests: runProjectRepositoryTests() },
    { name: 'State Manager & Undo/Redo Engine', tests: runStateHistoryTests() },
    { name: 'Phase 03 Structural Modeling Engine & CAD Operations', tests: runModelingEngineTests() }
  ];

  let totalTests = 0;
  let passedCount = 0;
  let failedCount = 0;

  suites.forEach(s => {
    s.tests.forEach(t => {
      totalTests++;
      if (t.passed) {
        passedCount++;
      } else {
        failedCount++;
      }
    });
  });

  return {
    timestamp: new Date().toISOString(),
    totalTests,
    passedCount,
    failedCount,
    allPassed: failedCount === 0,
    suites
  };
}
