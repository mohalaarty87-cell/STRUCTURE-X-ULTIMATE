import { ModelIntegrityValidator } from '../core/validation/ModelIntegrityValidator';
import { projectRepository } from '../server/repository/ProjectRepository';
import { StructuralModel } from '../types/domain';

export function runModelValidationTests(): { name: string; passed: boolean; message?: string }[] {
  const results: { name: string; passed: boolean; message?: string }[] = [];

  // Test 1: Benchmark model should pass validation
  try {
    const benchmark = projectRepository.getProject('PRJ-BENCHMARK-01');
    const report = ModelIntegrityValidator.validate(benchmark);
    const passed = report.isValid && report.canAnalyze && report.totalErrors === 0;
    results.push({
      name: 'Validation: 2-Story RC Benchmark Model isValid',
      passed,
      message: passed ? undefined : `Errors: ${report.issues.map(i => i.message).join(', ')}`
    });
  } catch (e: any) {
    results.push({ name: 'Validation: 2-Story RC Benchmark Model isValid', passed: false, message: e.message });
  }

  // Test 2: Detect E1002 (Zero length member)
  try {
    const invalidModel: StructuralModel = JSON.parse(JSON.stringify(projectRepository.getProject('PRJ-BENCHMARK-01')));
    // Corrupt member to have same start and end
    invalidModel.members[0].endNodeId = invalidModel.members[0].startNodeId;
    const report = ModelIntegrityValidator.validate(invalidModel);
    const hasZeroLen = report.issues.some(i => i.code === 'E1002');
    results.push({
      name: 'Validation: Detect E1002 Zero Length Member',
      passed: hasZeroLen && !report.isValid,
      message: hasZeroLen ? undefined : 'Failed to catch zero length member'
    });
  } catch (e: any) {
    results.push({ name: 'Validation: Detect E1002 Zero Length Member', passed: false, message: e.message });
  }

  // Test 3: Detect E2001 (Unassigned section)
  try {
    const invalidModel: StructuralModel = JSON.parse(JSON.stringify(projectRepository.getProject('PRJ-BENCHMARK-01')));
    invalidModel.members[0].sectionId = 'NON_EXISTENT_SECTION';
    const report = ModelIntegrityValidator.validate(invalidModel);
    const hasUnassigned = report.issues.some(i => i.code === 'E2001');
    results.push({
      name: 'Validation: Detect E2001 Missing Section Assignment',
      passed: hasUnassigned && !report.isValid,
      message: hasUnassigned ? undefined : 'Failed to catch missing section'
    });
  } catch (e: any) {
    results.push({ name: 'Validation: Detect E2001 Missing Section Assignment', passed: false, message: e.message });
  }

  // Test 4: Detect E3001 (No base restraints)
  try {
    const invalidModel: StructuralModel = JSON.parse(JSON.stringify(projectRepository.getProject('PRJ-BENCHMARK-01')));
    invalidModel.nodes.forEach(n => {
      n.isRestrained = false;
      n.restraints = { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false };
    });
    const report = ModelIntegrityValidator.validate(invalidModel);
    const hasNoRestraint = report.issues.some(i => i.code === 'E3001');
    results.push({
      name: 'Validation: Detect E3001 Missing Base Restraints',
      passed: hasNoRestraint && !report.canAnalyze,
      message: hasNoRestraint ? undefined : 'Failed to catch missing base restraints'
    });
  } catch (e: any) {
    results.push({ name: 'Validation: Detect E3001 Missing Base Restraints', passed: false, message: e.message });
  }

  return results;
}
