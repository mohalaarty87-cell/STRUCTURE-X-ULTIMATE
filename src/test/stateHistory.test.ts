import { ProjectStore } from '../core/state/ProjectStore';
import { projectRepository } from '../server/repository/ProjectRepository';
import { StructuralModel } from '../types/domain';

export function runStateHistoryTests(): { name: string; passed: boolean; message?: string }[] {
  const results: { name: string; passed: boolean; message?: string }[] = [];
  const store = ProjectStore.getInstance();

  try {
    const baseModel: StructuralModel = JSON.parse(JSON.stringify(projectRepository.getProject('PRJ-BENCHMARK-01')));
    store.setModel(baseModel, false); // initial load without recording history

    // State 1
    const modified1 = JSON.parse(JSON.stringify(baseModel));
    modified1.projectName = 'Modified Step 1';
    store.setModel(modified1, true);

    // State 2
    const modified2 = JSON.parse(JSON.stringify(modified1));
    modified2.projectName = 'Modified Step 2';
    store.setModel(modified2, true);

    // Undo 1 step
    const canUndo1 = store.canUndo();
    store.undo();
    const modelAfterUndo1 = store.getModel();
    const passed1 = canUndo1 && modelAfterUndo1?.projectName === 'Modified Step 1';

    results.push({
      name: 'StateHistory: Undo Step Restores Previous State',
      passed: passed1,
      message: passed1 ? undefined : `Expected 'Modified Step 1', got '${modelAfterUndo1?.projectName}'`
    });

    // Redo 1 step
    const canRedo1 = store.canRedo();
    store.redo();
    const modelAfterRedo1 = store.getModel();
    const passed2 = canRedo1 && modelAfterRedo1?.projectName === 'Modified Step 2';

    results.push({
      name: 'StateHistory: Redo Step Restores Forward State',
      passed: passed2,
      message: passed2 ? undefined : `Expected 'Modified Step 2', got '${modelAfterRedo1?.projectName}'`
    });

  } catch (e: any) {
    results.push({ name: 'StateHistory: Undo/Redo Engine', passed: false, message: e.message });
  }

  return results;
}
