import { UnitConverter } from '../core/units/unitConverter';

export function runUnitConversionTests(): { name: string; passed: boolean; message?: string }[] {
  const results: { name: string; passed: boolean; message?: string }[] = [];

  // Test 1: Length conversion 1 m = 1000 mm
  try {
    const val = UnitConverter.convertLength(1.0, 'm', 'mm');
    const passed = Math.abs(val - 1000.0) < 1e-6;
    results.push({
      name: 'Length: 1 m -> 1000 mm',
      passed,
      message: passed ? undefined : `Expected 1000, got ${val}`
    });
  } catch (e: any) {
    results.push({ name: 'Length: 1 m -> 1000 mm', passed: false, message: e.message });
  }

  // Test 2: Length conversion 1 ft = 0.3048 m
  try {
    const val = UnitConverter.convertLength(1.0, 'ft', 'm');
    const passed = Math.abs(val - 0.3048) < 1e-6;
    results.push({
      name: 'Length: 1 ft -> 0.3048 m',
      passed,
      message: passed ? undefined : `Expected 0.3048, got ${val}`
    });
  } catch (e: any) {
    results.push({ name: 'Length: 1 ft -> 0.3048 m', passed: false, message: e.message });
  }

  // Test 3: Force conversion 1 kip = 4.44822 kN
  try {
    const val = UnitConverter.convertForce(1.0, 'kip', 'kN');
    const passed = Math.abs(val - 4.4482216) < 1e-4;
    results.push({
      name: 'Force: 1 kip -> ~4.44822 kN',
      passed,
      message: passed ? undefined : `Expected ~4.44822, got ${val}`
    });
  } catch (e: any) {
    results.push({ name: 'Force: 1 kip -> ~4.44822 kN', passed: false, message: e.message });
  }

  // Test 4: Stress conversion 1 ksi = 6.89476 MPa
  try {
    const val = UnitConverter.convertStress(1.0, 'ksi', 'MPa');
    const passed = Math.abs(val - 6.894757) < 1e-3;
    results.push({
      name: 'Stress: 1 ksi -> ~6.89476 MPa',
      passed,
      message: passed ? undefined : `Expected ~6.89476, got ${val}`
    });
  } catch (e: any) {
    results.push({ name: 'Stress: 1 ksi -> ~6.89476 MPa', passed: false, message: e.message });
  }

  // Test 5: Temperature conversion 100 C -> 212 F
  try {
    const val = UnitConverter.convertTemperature(100.0, 'C', 'F');
    const passed = Math.abs(val - 212.0) < 1e-6;
    results.push({
      name: 'Temperature: 100 C -> 212 F',
      passed,
      message: passed ? undefined : `Expected 212, got ${val}`
    });
  } catch (e: any) {
    results.push({ name: 'Temperature: 100 C -> 212 F', passed: false, message: e.message });
  }

  return results;
}
