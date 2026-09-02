import { StructuralModel } from '../../types/domain';
import { ModelIntegrityValidator, ValidationReport } from '../validation/ModelIntegrityValidator';
import { logger } from '../logging/Logger';
import { config } from '../../config';

export type StateChangeListener = (model: StructuralModel) => void;

export class ProjectStore {
  private static instance: ProjectStore;
  private currentModel: StructuralModel | null = null;
  private undoStack: StructuralModel[] = [];
  private redoStack: StructuralModel[] = [];
  private maxHistory: number = config.features.maxUndoHistorySteps;
  private listeners: StateChangeListener[] = [];
  private isDirty: boolean = false;
  private autoSaveTimer: NodeJS.Timeout | null = null;

  private constructor() {
    if (config.features.enableAutoSave && typeof window !== 'undefined') {
      this.initAutoSave();
    }
  }

  public static getInstance(): ProjectStore {
    if (!ProjectStore.instance) {
      ProjectStore.instance = new ProjectStore();
    }
    return ProjectStore.instance;
  }

  public getModel(): StructuralModel | null {
    return this.currentModel;
  }

  public setModel(model: StructuralModel, recordHistory: boolean = true): void {
    if (recordHistory && this.currentModel) {
      this.undoStack.push(JSON.parse(JSON.stringify(this.currentModel)));
      if (this.undoStack.length > this.maxHistory) {
        this.undoStack.shift();
      }
      this.redoStack = []; // Reset redo stack on new modification
    }

    this.currentModel = JSON.parse(JSON.stringify(model));
    this.isDirty = true;
    logger.info('ProjectStore', `Updated model "${model.projectName}" (Nodes: ${model.nodes.length}, Members: ${model.members.length})`);

    this.notify();
  }

  public undo(): boolean {
    if (this.undoStack.length === 0 || !this.currentModel) return false;

    const previous = this.undoStack.pop()!;
    this.redoStack.push(JSON.parse(JSON.stringify(this.currentModel)));
    this.currentModel = previous;
    this.isDirty = true;
    logger.info('ProjectStore', 'Action undone. History steps remaining: ' + this.undoStack.length);
    this.notify();
    return true;
  }

  public redo(): boolean {
    if (this.redoStack.length === 0 || !this.currentModel) return false;

    const next = this.redoStack.pop()!;
    this.undoStack.push(JSON.parse(JSON.stringify(this.currentModel)));
    this.currentModel = next;
    this.isDirty = true;
    logger.info('ProjectStore', 'Action redone. Redo steps remaining: ' + this.redoStack.length);
    this.notify();
    return true;
  }

  public canUndo(): boolean {
    return this.undoStack.length > 0;
  }

  public canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  public validateCurrentModel(): ValidationReport | null {
    if (!this.currentModel) return null;
    return ModelIntegrityValidator.validate(this.currentModel);
  }

  public subscribe(listener: StateChangeListener): () => void {
    this.listeners.push(listener);
    if (this.currentModel) {
      listener(this.currentModel);
    }
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify(): void {
    if (!this.currentModel) return;
    this.listeners.forEach(fn => {
      try {
        fn(this.currentModel!);
      } catch (e) {
        logger.error('ProjectStore', 'Listener execution error', e);
      }
    });
  }

  public markClean(): void {
    this.isDirty = false;
  }

  public getIsDirty(): boolean {
    return this.isDirty;
  }

  private initAutoSave(): void {
    if (this.autoSaveTimer) clearInterval(this.autoSaveTimer);
    this.autoSaveTimer = setInterval(() => {
      if (this.isDirty && this.currentModel) {
        try {
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem(`structurex_autosave_${this.currentModel.metadata.id}`, JSON.stringify(this.currentModel));
            logger.debug('ProjectStore', `AutoSaved model "${this.currentModel.projectName}" to local storage`);
            this.isDirty = false;
          }
        } catch (e) {
          logger.warn('ProjectStore', 'Failed to autosave model', e);
        }
      }
    }, config.features.autoSaveIntervalMs);
  }
}

export const projectStore = ProjectStore.getInstance();
