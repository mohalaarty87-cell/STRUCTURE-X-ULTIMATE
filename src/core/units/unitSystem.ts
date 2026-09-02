export type UnitDimension = 
  | 'LENGTH' 
  | 'FORCE' 
  | 'MOMENT' 
  | 'STRESS' 
  | 'DISTRIBUTED_FORCE' 
  | 'AREA_FORCE' 
  | 'UNIT_WEIGHT' 
  | 'MASS' 
  | 'TEMPERATURE';

export type LengthUnit = 'm' | 'cm' | 'mm' | 'ft' | 'in';
export type ForceUnit = 'kN' | 'N' | 'kip' | 'lbf' | 'kgf' | 'tonf';
export type MomentUnit = 'kN-m' | 'N-mm' | 'kip-ft' | 'kip-in' | 'kgf-m' | 'tonf-m';
export type StressUnit = 'MPa' | 'GPa' | 'kPa' | 'N/mm2' | 'psi' | 'ksi' | 'kgf/cm2' | 'tonf/m2';
export type DistributedForceUnit = 'kN/m' | 'N/mm' | 'kip/ft' | 'plf' | 'klf' | 'kgf/m';
export type AreaForceUnit = 'kN/m2' | 'kPa' | 'MPa' | 'psf' | 'ksf' | 'psi' | 'kgf/m2';
export type UnitWeightUnit = 'kN/m3' | 'kg/m3' | 'pcf' | 'lb/ft3';
export type TemperatureUnit = 'C' | 'F' | 'K';

export type StandardUnitSystemCode = 
  | 'kN-m, C'
  | 'N-mm, C'
  | 'kip-ft, F'
  | 'kip-in, F'
  | 'kgf-cm, C';

export interface UnitSystemDefinition {
  code: StandardUnitSystemCode;
  name: string;
  isMetric: boolean;
  length: LengthUnit;
  force: ForceUnit;
  moment: MomentUnit;
  stress: StressUnit;
  distributedForce: DistributedForceUnit;
  areaForce: AreaForceUnit;
  unitWeight: UnitWeightUnit;
  temperature: TemperatureUnit;
}

export const UNIT_SYSTEMS: Record<StandardUnitSystemCode, UnitSystemDefinition> = {
  'kN-m, C': {
    code: 'kN-m, C',
    name: 'SI Metric (Standard)',
    isMetric: true,
    length: 'm',
    force: 'kN',
    moment: 'kN-m',
    stress: 'MPa',
    distributedForce: 'kN/m',
    areaForce: 'kN/m2',
    unitWeight: 'kN/m3',
    temperature: 'C'
  },
  'N-mm, C': {
    code: 'N-mm, C',
    name: 'SI Metric (Engineering mm)',
    isMetric: true,
    length: 'mm',
    force: 'N',
    moment: 'N-mm',
    stress: 'MPa',
    distributedForce: 'N/mm',
    areaForce: 'MPa',
    unitWeight: 'kg/m3',
    temperature: 'C'
  },
  'kip-ft, F': {
    code: 'kip-ft, F',
    name: 'US Customary (Kip - Foot)',
    isMetric: false,
    length: 'ft',
    force: 'kip',
    moment: 'kip-ft',
    stress: 'ksi',
    distributedForce: 'kip/ft',
    areaForce: 'ksf',
    unitWeight: 'pcf',
    temperature: 'F'
  },
  'kip-in, F': {
    code: 'kip-in, F',
    name: 'US Customary (Kip - Inch)',
    isMetric: false,
    length: 'in',
    force: 'kip',
    moment: 'kip-in',
    stress: 'ksi',
    distributedForce: 'kip/ft',
    areaForce: 'psi',
    unitWeight: 'pcf',
    temperature: 'F'
  },
  'kgf-cm, C': {
    code: 'kgf-cm, C',
    name: 'MKS Metric (kgf - cm)',
    isMetric: true,
    length: 'cm',
    force: 'kgf',
    moment: 'kgf-m',
    stress: 'kgf/cm2',
    distributedForce: 'kgf/m',
    areaForce: 'kgf/m2',
    unitWeight: 'kg/m3',
    temperature: 'C'
  }
};
