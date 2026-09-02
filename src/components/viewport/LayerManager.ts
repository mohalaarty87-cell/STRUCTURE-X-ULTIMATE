import * as THREE from 'three';
import {
  StructuralModel,
  LayerVisibilityState,
  DEFAULT_LAYER_VISIBILITY,
  DisplayMode,
  AnnotationSettings,
  DEFAULT_ANNOTATION_SETTINGS
} from '../../types/structure';
import { GridLayer } from './layers/GridLayer';
import { StoryLayer } from './layers/StoryLayer';
import { FrameLayer } from './layers/FrameLayer';
import { ShellLayer } from './layers/ShellLayer';
import { WallLayer } from './layers/WallLayer';
import { LoadLayer } from './layers/LoadLayer';
import { SupportLayer } from './layers/SupportLayer';
import { ResultLayer } from './layers/ResultLayer';
import { SelectionLayer } from './layers/SelectionLayer';
import { AnnotationLayer } from './layers/AnnotationLayer';

export class LayerManager {
  public rootGroup: THREE.Group;

  public gridLayer: GridLayer;
  public storyLayer: StoryLayer;
  public frameLayer: FrameLayer;
  public shellLayer: ShellLayer;
  public wallLayer: WallLayer;
  public loadLayer: LoadLayer;
  public supportLayer: SupportLayer;
  public resultLayer: ResultLayer;
  public selectionLayer: SelectionLayer;
  public annotationLayer: AnnotationLayer;

  private visibilityState: LayerVisibilityState;
  private annotationSettings: AnnotationSettings;

  constructor() {
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = 'StructureX_LayersRoot';

    this.gridLayer = new GridLayer();
    this.storyLayer = new StoryLayer();
    this.frameLayer = new FrameLayer();
    this.shellLayer = new ShellLayer();
    this.wallLayer = new WallLayer();
    this.loadLayer = new LoadLayer();
    this.supportLayer = new SupportLayer();
    this.resultLayer = new ResultLayer();
    this.selectionLayer = new SelectionLayer();
    this.annotationLayer = new AnnotationLayer();

    this.rootGroup.add(this.gridLayer.group);
    this.rootGroup.add(this.storyLayer.group);
    this.rootGroup.add(this.frameLayer.group);
    this.rootGroup.add(this.shellLayer.group);
    this.rootGroup.add(this.wallLayer.group);
    this.rootGroup.add(this.loadLayer.group);
    this.rootGroup.add(this.supportLayer.group);
    this.rootGroup.add(this.resultLayer.group);
    this.rootGroup.add(this.selectionLayer.group);
    this.rootGroup.add(this.annotationLayer.group);

    this.visibilityState = { ...DEFAULT_LAYER_VISIBILITY };
    this.annotationSettings = { ...DEFAULT_ANNOTATION_SETTINGS };
  }

  public updateAll(
    model: StructuralModel,
    visibility: LayerVisibilityState = this.visibilityState,
    displayMode: DisplayMode = 'extruded',
    selectedElementId: string | null = null,
    hoveredElementId: string | null = null,
    activeStoryFilter: string = 'all',
    annotationSettings: AnnotationSettings = this.annotationSettings
  ): void {
    this.visibilityState = { ...visibility };
    this.annotationSettings = { ...annotationSettings };

    // Update each specific layer
    this.gridLayer.update(model, visibility.grid);
    this.storyLayer.update(model, visibility.story, activeStoryFilter);
    this.frameLayer.update(model, visibility.frame, displayMode, selectedElementId, hoveredElementId, activeStoryFilter);
    this.shellLayer.update(model, visibility.shell, displayMode, selectedElementId, hoveredElementId, activeStoryFilter);
    this.wallLayer.update(model, visibility.wall, displayMode, selectedElementId, hoveredElementId, activeStoryFilter);
    this.loadLayer.update(model, visibility.load, activeStoryFilter);
    this.supportLayer.update(model, visibility.support);
    this.resultLayer.update(model, visibility.result, displayMode, activeStoryFilter);
    this.selectionLayer.update(model, selectedElementId, hoveredElementId, visibility.selection);
    this.annotationLayer.update(model, visibility.annotation, annotationSettings, activeStoryFilter);
  }

  public setLayerVisibility(layerName: keyof LayerVisibilityState, visible: boolean): void {
    this.visibilityState[layerName] = visible;
    switch (layerName) {
      case 'grid': this.gridLayer.setVisible(visible); break;
      case 'story': this.storyLayer.setVisible(visible); break;
      case 'frame': this.frameLayer.setVisible(visible); break;
      case 'shell': this.shellLayer.setVisible(visible); break;
      case 'wall': this.wallLayer.setVisible(visible); break;
      case 'load': this.loadLayer.setVisible(visible); break;
      case 'support': this.supportLayer.setVisible(visible); break;
      case 'result': this.resultLayer.setVisible(visible); break;
      case 'selection': this.selectionLayer.setVisible(visible); break;
      case 'annotation': this.annotationLayer.setVisible(visible); break;
    }
  }

  public getPickableObjects(): THREE.Object3D[] {
    return [
      ...this.frameLayer.pickableObjects,
      ...this.shellLayer.pickableObjects,
      ...this.wallLayer.pickableObjects
    ];
  }

  public dispose(): void {
    this.gridLayer.clear();
    this.storyLayer.clear();
    this.frameLayer.clear();
    this.shellLayer.clear();
    this.wallLayer.clear();
    this.loadLayer.clear();
    this.supportLayer.clear();
    this.resultLayer.clear();
    this.selectionLayer.clear();
    this.annotationLayer.clear();
  }
}
