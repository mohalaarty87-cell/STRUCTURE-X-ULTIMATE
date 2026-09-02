import { 
  LengthUnit, 
  ForceUnit, 
  MomentUnit, 
  StressUnit, 
  DistributedForceUnit, 
  AreaForceUnit, 
  UnitWeightUnit,
  TemperatureUnit,
  UnitDimension 
} from './unitSystem';

// Length: Base unit is Meters (m)
const LENGTH_TO_METERS: Record<LengthUnit, number> = {
  m: 1.0,
  cm: 0.01,
  mm: 0.001,
  ft: 0.3048,
  in: 0.0254
};

// Force: Base unit is Newtons (N)
const FORCE_TO_NEWTONS: Record<ForceUnit, number> = {
  N: 1.0,
  kN: 1000.0,
  kip: 4448.2216152605,
  lbf: 4.4482216152605,
  kgf: 9.80665,
  tonf: 9806.65
};

// Moment: Base unit is Newton-Meters (N.m)
const MOMENT_TO_NM: Record<MomentUnit, number> = {
  'kN-m': 1000.0,
  'N-mm': 0.001,
  'kip-ft': 1355.8179483314, // 4448.2216152605 * 0.3048
  'kip-in': 112.9848290276,  // 4448.2216152605 * 0.0254
  'kgf-m': 9.80665,
  'tonf-m': 9806.65
};

// Stress / Pressure: Base unit is Pascals (Pa)
const STRESS_TO_PASCALS: Record<StressUnit, number> = {
  MPa: 1e6,
  GPa: 1e9,
  kPa: 1e3,
  'N/mm2': 1e6,
  psi: 6894.757293168,
  ksi: 6894757.293168,
  'kgf/cm2': 98066.5,
  'tonf/m2': 9806.65
};

// Distributed Force: Base unit is N/m
const DIST_FORCE_TO_NM: Record<DistributedForceUnit, number> = {
  'kN/m': 1000.0,
  'N/mm': 1000.0,
  'kip/ft': 14593.9029372064, // (4448.2216152605 / 0.3048)
  plf: 14.5939029372064,
  klf: 14593.9029372064,
  'kgf/m': 9.80665
};

// Area Force: Base unit is Pa (N/m2)
const AREA_FORCE_TO_PA: Record<AreaForceUnit, number> = {
  'kN/m2': 1000.0,
  kPa: 1000.0,
  MPa: 1e6,
  psf: 47.88025898,
  ksf: 47880.25898,
  psi: 6894.757293168,
  'kgf/m2': 9.80665
};

// Unit Weight: Base unit is N/m3
const UNIT_WEIGHT_TO_NM3: Record<UnitWeightUnit, number> = {
  'kN/m3': 1000.0,
  'kg/m3': 9.80665,
  pcf: 157.0874638,
  'lb/ft3': 157.0874638
};

export class UnitConverter {
  public static convertLength(value: number, from: LengthUnit, to: LengthUnit): number {
    if (from === to) return value;
    const inMeters = value * LENGTH_TO_METERS[from];
    return inMeters / LENGTH_TO_METERS[to];
  }

  public static convertForce(value: number, from: ForceUnit, to: ForceUnit): number {
    if (from === to) return value;
    const inNewtons = value * FORCE_TO_NEWTONS[from];
    return inNewtons / FORCE_TO_NEWTONS[to];
  }

  public static convertMoment(value: number, from: MomentUnit, to: MomentUnit): number {
    if (from === to) return value;
    const inNm = value * MOMENT_TO_NM[from];
    return inNm / MOMENT_TO_NM[to];
  }

  public static convertStress(value: number, from: StressUnit, to: StressUnit): number {
    if (from === to) return value;
    const inPa = value * STRESS_TO_PASCALS[from];
    return inPa / STRESS_TO_PASCALS[to];
  }

  public static convertDistributedForce(value: number, from: DistributedForceUnit, to: DistributedForceUnit): number {
    if (from === to) return value;
    const inNm = value * DIST_FORCE_TO_NM[from];
    return inNm / DIST_FORCE_TO_NM[to];
  }

  public static convertAreaForce(value: number, from: AreaForceUnit, to: AreaForceUnit): number {
    if (from === to) return value;
    const inPa = value * AREA_FORCE_TO_PA[from];
    return inPa / AREA_FORCE_TO_PA[to];
  }

  public static convertUnitWeight(value: number, from: UnitWeightUnit, to: UnitWeightUnit): number {
    if (from === to) return value;
    const inNm3 = value * UNIT_WEIGHT_TO_NM3[from];
    return inNm3 / UNIT_WEIGHT_TO_NM3[to];
  }

  public static convertTemperature(value: number, from: TemperatureUnit, to: TemperatureUnit): number {
    if (from === to) return value;
    // Normalize to Celsius
    let celsius = value;
    if (from === 'F') celsius = (value - 32) * (5 / 9);
    if (from === 'K') celsius = value - 273.15;

    // Convert to target
    if (to === 'C') return celsius;
    if (to === 'F') return (celsius * 9) / 5 + 32;
    if (to === 'K') return celsius + 273.15;
    return value;
  }
}
