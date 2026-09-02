import { projectRepository } from '../server/repository/ProjectRepository';

export function runProjectRepositoryTests(): { name: string; passed: boolean; message?: string }[] {
  const results: { name: string; passed: boolean; message?: string }[] = [];

  // Test 1: List seeded projects
  try {
    const list = projectRepository.listProjects();
    const passed = list.length >= 1 && list.some(p => p.id === 'PRJ-BENCHMARK-01');
    results.push({
      name: 'Repository: List Seeded Benchmark Projects',
      passed,
      message: passed ? undefined : `Found ${list.length} projects`
    });
  } catch (e: any) {
    results.push({ name: 'Repository: List Seeded Benchmark Projects', passed: false, message: e.message });
  }

  // Test 2: Create new project
  let createdId = '';
  try {
    const newPrj = projectRepository.createProject({
      name: 'Test Cantilever Tower',
      code: 'TWR-TEST',
      engineer: 'QA Engineer'
    });
    createdId = newPrj.metadata.id;
    const passed = newPrj.projectName === 'Test Cantilever Tower' && newPrj.metadata.code === 'TWR-TEST';
    results.push({
      name: 'Repository: Create Project with Metadata',
      passed,
      message: passed ? undefined : 'Failed to initialize project metadata'
    });
  } catch (e: any) {
    results.push({ name: 'Repository: Create Project with Metadata', passed: false, message: e.message });
  }

  // Test 3: Save and fetch project
  try {
    const fetched = projectRepository.getProject(createdId);
    fetched.projectName = 'Renamed Cantilever Tower';
    projectRepository.saveProject(fetched);

    const reFetched = projectRepository.getProject(createdId);
    const passed = reFetched.projectName === 'Renamed Cantilever Tower' && reFetched.metadata.revision === 2;
    results.push({
      name: 'Repository: Update Project & Revision Bump',
      passed,
      message: passed ? undefined : `Expected Rev 2, got ${reFetched.metadata.revision}`
    });
  } catch (e: any) {
    results.push({ name: 'Repository: Update Project & Revision Bump', passed: false, message: e.message });
  }

  // Test 4: Delete project
  try {
    projectRepository.deleteProject(createdId);
    let threw = false;
    try {
      projectRepository.getProject(createdId);
    } catch {
      threw = true;
    }
    results.push({
      name: 'Repository: Delete Project',
      passed: threw,
      message: threw ? undefined : 'Project still accessible after deletion'
    });
  } catch (e: any) {
    results.push({ name: 'Repository: Delete Project', passed: false, message: e.message });
  }

  return results;
}
