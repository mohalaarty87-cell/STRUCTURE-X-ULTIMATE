import { StructuralModel } from '../types/structure';
import { ModelIntegrityValidator } from '../core/validation/ModelIntegrityValidator';

const STORAGE_KEY_ACTIVE_PROJECT = 'structurex_active_model';
const STORAGE_KEY_SAVED_PROJECTS = 'structurex_saved_projects';
const STORAGE_KEY_AUTOSAVE_TIMESTAMP = 'structurex_last_autosave';

export class ProjectStorage {
  /**
   * Saves the current active model to localStorage for autosave & persistence
   */
  public static saveActiveProject(model: StructuralModel): void {
    try {
      const serialized = JSON.stringify(model);
      localStorage.setItem(STORAGE_KEY_ACTIVE_PROJECT, serialized);
      localStorage.setItem(STORAGE_KEY_AUTOSAVE_TIMESTAMP, new Date().toISOString());

      // Also index into saved projects list
      const savedProjects = this.listSavedProjects();
      const modelMetaId = (model as any).metadata?.id || (model as any).id;
      const existingIdx = savedProjects.findIndex(p => p.id === modelMetaId || p.name === model.projectName);
      
      const summary = {
        id: modelMetaId || `prj-${Date.now()}`,
        name: model.projectName,
        lastModified: new Date().toISOString(),
        nodeCount: model.nodes.length,
        memberCount: model.members.length,
        slabCount: model.slabs.length,
        wallCount: model.walls?.length || 0,
        storyCount: model.stories.length,
        units: model.units
      };

      if (existingIdx >= 0) {
        savedProjects[existingIdx] = summary;
      } else {
        savedProjects.push(summary);
      }

      localStorage.setItem(STORAGE_KEY_SAVED_PROJECTS, JSON.stringify(savedProjects));
    } catch (e) {
      console.error('Failed to autosave project to localStorage:', e);
    }
  }

  /**
   * Loads the active model from localStorage if available
   */
  public static loadActiveProject(): StructuralModel | null {
    try {
      const data = localStorage.getItem(STORAGE_KEY_ACTIVE_PROJECT);
      if (!data) return null;
      const model = JSON.parse(data) as StructuralModel;
      return model;
    } catch (e) {
      console.error('Failed to load active project from localStorage:', e);
      return null;
    }
  }

  /**
   * Gets the last autosave time
   */
  public static getLastAutosaveTime(): string | null {
    return localStorage.getItem(STORAGE_KEY_AUTOSAVE_TIMESTAMP);
  }

  /**
   * Lists all saved projects summaries
   */
  public static listSavedProjects(): Array<{
    id: string;
    name: string;
    lastModified: string;
    nodeCount: number;
    memberCount: number;
    slabCount: number;
    wallCount: number;
    storyCount: number;
    units: string;
  }> {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_SAVED_PROJECTS);
      if (!raw) return [];
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }

  /**
   * Clears saved state (for new project creation)
   */
  public static clearActiveProject(): void {
    localStorage.removeItem(STORAGE_KEY_ACTIVE_PROJECT);
    localStorage.removeItem(STORAGE_KEY_AUTOSAVE_TIMESTAMP);
  }
}
