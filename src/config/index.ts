export interface AppConfig {
  env: 'development' | 'production' | 'test';
  port: number;
  host: string;
  appUrl: string;
  version: string;
  buildTime: string;
  features: {
    enableAutoSave: boolean;
    autoSaveIntervalMs: number;
    maxUndoHistorySteps: number;
    enableDiagnosticsLogs: boolean;
    enableStrictModelValidation: boolean;
  };
  numericalPrecision: {
    geometricToleranceMeters: number; // 0.0001 m (0.1 mm)
    forceToleranceKiloNewtons: number; // 0.001 kN (1 N)
    momentToleranceKiloNewtonMeters: number; // 0.001 kN.m
    stressToleranceMegaPascals: number; // 0.01 MPa
    displayPrecisionDecimals: number; // 3 decimals for display
  };
}

export const config: AppConfig = {
  env: (process.env.NODE_ENV as 'development' | 'production' | 'test') || 'development',
  port: 3000,
  host: '0.0.0.0',
  appUrl: process.env.APP_URL || 'http://localhost:3000',
  version: '4.2.0-PRO',
  buildTime: new Date().toISOString(),
  features: {
    enableAutoSave: true,
    autoSaveIntervalMs: 30000, // 30s
    maxUndoHistorySteps: 50,
    enableDiagnosticsLogs: true,
    enableStrictModelValidation: true,
  },
  numericalPrecision: {
    geometricToleranceMeters: 1e-4, // 0.1 mm
    forceToleranceKiloNewtons: 1e-3, // 1 N
    momentToleranceKiloNewtonMeters: 1e-3,
    stressToleranceMegaPascals: 1e-2,
    displayPrecisionDecimals: 3,
  },
};
