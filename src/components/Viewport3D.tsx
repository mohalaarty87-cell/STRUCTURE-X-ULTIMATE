import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import {
  StructuralModel,
  ActiveCadTool,
  DisplayMode,
  ViewportMode,
  CameraProjection,
  CameraPreset,
  LayerVisibilityState,
  DEFAULT_LAYER_VISIBILITY,
  AnnotationSettings,
  DEFAULT_ANNOTATION_SETTINGS
} from '../types/structure';
import { LayerManager } from './viewport/LayerManager';
import { CameraController } from './viewport/CameraController';
import { ViewCube } from './viewport/ViewCube';
import {
  Layers,
  Eye,
  EyeOff,
  Maximize,
  Compass,
  Grid,
  Box,
  Layers3,
  Sliders,
  Sparkles,
  RefreshCw,
  Camera,
  Activity,
  CheckSquare,
  Square
} from 'lucide-react';

interface Viewport3DProps {
  model: StructuralModel;
  selectedElementId: string | null;
  onSelectElement: (id: string | null) => void;
  activeTool: ActiveCadTool;
  displayMode: DisplayMode;
  setDisplayMode: (mode: DisplayMode) => void;
  viewportMode: ViewportMode;
  setViewportMode: (mode: ViewportMode) => void;
  isAnalyzing: boolean;
  activeStoryFilter: string;
  setActiveStoryFilter: (story: string) => void;
  layerVisibility?: LayerVisibilityState;
  onToggleLayer?: (layer: keyof LayerVisibilityState) => void;
  onUpdateCoordinates?: (coords: { x: number; y: number; z: number }) => void;
  lang: 'en' | 'ar';
}

export const Viewport3D: React.FC<Viewport3DProps> = ({
  model,
  selectedElementId,
  onSelectElement,
  activeTool,
  displayMode,
  setDisplayMode,
  viewportMode,
  setViewportMode,
  isAnalyzing,
  activeStoryFilter,
  setActiveStoryFilter,
  layerVisibility: externalLayerVisibility,
  onToggleLayer,
  onUpdateCoordinates,
  lang
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Engine References
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraControllerRef = useRef<CameraController | null>(null);
  const layerManagerRef = useRef<LayerManager | null>(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());

  // Local state
  const [layers, setLayers] = useState<LayerVisibilityState>(externalLayerVisibility || DEFAULT_LAYER_VISIBILITY);
  const [annotationSettings, setAnnotationSettings] = useState<AnnotationSettings>(DEFAULT_ANNOTATION_SETTINGS);
  const [showLayerMenu, setShowLayerMenu] = useState(false);
  const [showDisplayMenu, setShowDisplayMenu] = useState(false);
  const [projection, setProjection] = useState<CameraProjection>('perspective');
  const [hoveredElementId, setHoveredElementId] = useState<string | null>(null);
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0, z: 0 });

  // Mouse interaction state
  const isDraggingRef = useRef(false);
  const isPanningRef = useRef(false);
  const prevMousePosRef = useRef({ x: 0, y: 0 });

  // Sync external layers state if provided
  useEffect(() => {
    if (externalLayerVisibility) {
      setLayers(externalLayerVisibility);
    }
  }, [externalLayerVisibility]);

  // 1. Initialize Scene & Three.js Engine
  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth || 800;
    const height = containerRef.current.clientHeight || 600;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1012);
    sceneRef.current = scene;

    // Lighting (CAD Studio HDR-like setup)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight1.position.set(25, 40, 20);
    dirLight1.castShadow = true;
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x96ccff, 0.45);
    dirLight2.position.set(-25, 20, -20);
    scene.add(dirLight2);

    // Camera Controller
    const cameraController = new CameraController(width, height);
    cameraControllerRef.current = cameraController;

    // Layer Manager
    const layerManager = new LayerManager();
    layerManagerRef.current = layerManager;
    scene.add(layerManager.rootGroup);

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    rendererRef.current = renderer;

    containerRef.current.replaceChildren(renderer.domElement);

    // Fit Initial Model
    cameraController.fitModel(model);

    // Animation Render Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (rendererRef.current && sceneRef.current && cameraControllerRef.current) {
        rendererRef.current.render(sceneRef.current, cameraControllerRef.current.activeCamera);
      }
    };
    animate();

    // Resize Observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newW, height: newH } = entry.contentRect;
        if (newW > 0 && newH > 0 && rendererRef.current && cameraControllerRef.current) {
          rendererRef.current.setSize(newW, newH);
          cameraControllerRef.current.setSize(newW, newH);
        }
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      if (layerManagerRef.current) layerManagerRef.current.dispose();
      if (rendererRef.current) rendererRef.current.dispose();
    };
  }, []);

  // 2. Update Layers whenever Model, Visibility, DisplayMode, or Selection changes
  useEffect(() => {
    if (!layerManagerRef.current) return;
    layerManagerRef.current.updateAll(
      model,
      layers,
      displayMode,
      selectedElementId,
      hoveredElementId,
      activeStoryFilter,
      annotationSettings
    );
  }, [model, layers, displayMode, selectedElementId, hoveredElementId, activeStoryFilter, annotationSettings]);

  // 3. Camera Projection Toggle
  const handleToggleProjection = (proj: CameraProjection) => {
    setProjection(proj);
    if (cameraControllerRef.current) {
      cameraControllerRef.current.setProjection(proj);
    }
  };

  // 4. Camera Presets (Plan, Elevation, 3D Iso, Fit)
  const handleSelectPreset = (preset: CameraPreset) => {
    if (cameraControllerRef.current) {
      cameraControllerRef.current.applyPreset(preset, model);
    }
    if (preset === 'plan') setViewportMode('plan');
    else if (preset.startsWith('elevation')) setViewportMode('elevation');
    else setViewportMode('3d');
  };

  const handleFitModel = () => {
    if (cameraControllerRef.current) {
      cameraControllerRef.current.fitModel(model);
    }
  };

  // 5. Layer Toggle Handler
  const toggleLayer = (layerName: keyof LayerVisibilityState) => {
    setLayers((prev) => {
      const updated = { ...prev, [layerName]: !prev[layerName] };
      if (layerManagerRef.current) {
        layerManagerRef.current.setLayerVisibility(layerName, updated[layerName]);
      }
      return updated;
    });
    if (onToggleLayer) onToggleLayer(layerName);
  };

  // 6. Mouse & Raycasting Handlers
  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button === 0) {
      // Left Click: Orbit or Selection
      isDraggingRef.current = true;
    } else if (e.button === 1 || e.button === 2) {
      // Middle or Right Click: Pan
      isPanningRef.current = true;
    }
    prevMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!containerRef.current || !cameraControllerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    mouseRef.current.set(mouseX, mouseY);

    const deltaX = e.clientX - prevMousePosRef.current.x;
    const deltaY = e.clientY - prevMousePosRef.current.y;
    prevMousePosRef.current = { x: e.clientX, y: e.clientY };

    if (isDraggingRef.current) {
      cameraControllerRef.current.orbit(deltaX, deltaY);
    } else if (isPanningRef.current) {
      cameraControllerRef.current.pan(deltaX, deltaY);
    } else {
      // Raycasting for Hover Highlight & Cursor coordinate calculation
      raycasterRef.current.setFromCamera(mouseRef.current, cameraControllerRef.current.activeCamera);
      
      // Compute ground plane intersection for real-time cursor coordinates
      const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
      const intersectionPoint = new THREE.Vector3();
      if (raycasterRef.current.ray.intersectPlane(groundPlane, intersectionPoint)) {
        const coords = {
          x: Math.round(intersectionPoint.x * 100) / 100,
          y: Math.round(intersectionPoint.y * 100) / 100,
          z: Math.round(intersectionPoint.z * 100) / 100
        };
        setCursorPos(coords);
        if (onUpdateCoordinates) onUpdateCoordinates(coords);
      }

      // Check hover on pickable elements
      if (layerManagerRef.current) {
        const pickables = layerManagerRef.current.getPickableObjects();
        const intersects = raycasterRef.current.intersectObjects(pickables, true);
        if (intersects.length > 0) {
          let topObj: THREE.Object3D | null = intersects[0].object;
          while (topObj && !topObj.userData?.id && topObj.parent) {
            topObj = topObj.parent;
          }
          if (topObj?.userData?.id) {
            setHoveredElementId(topObj.userData.id);
          }
        } else {
          setHoveredElementId(null);
        }
      }
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    // If not dragged significantly, treat as Click Selection
    const distMoved = Math.hypot(e.clientX - prevMousePosRef.current.x, e.clientY - prevMousePosRef.current.y);
    if (distMoved < 5 && isDraggingRef.current && layerManagerRef.current && cameraControllerRef.current) {
      raycasterRef.current.setFromCamera(mouseRef.current, cameraControllerRef.current.activeCamera);
      const pickables = layerManagerRef.current.getPickableObjects();
      const intersects = raycasterRef.current.intersectObjects(pickables, true);

      if (intersects.length > 0) {
        let topObj: THREE.Object3D | null = intersects[0].object;
        while (topObj && !topObj.userData?.id && topObj.parent) {
          topObj = topObj.parent;
        }
        if (topObj?.userData?.id) {
          onSelectElement(topObj.userData.id);
        }
      } else {
        // Deselect if clicked in empty space
        onSelectElement(null);
      }
    }

    isDraggingRef.current = false;
    isPanningRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (cameraControllerRef.current) {
      cameraControllerRef.current.zoom(e.deltaY);
    }
  };

  return (
    <div className="relative w-full h-full select-none overflow-hidden bg-[#0c0e10]">
      {/* 3D WebGL Canvas Container */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
        onContextMenu={(e) => e.preventDefault()}
        className="w-full h-full cursor-crosshair"
      />

      {/* 3D ViewCube Navigation Gizmo */}
      <ViewCube
        onSelectPreset={handleSelectPreset}
        onResetView={handleFitModel}
        lang={lang}
      />

      {/* Top Floating Viewport HUD Toolbar */}
      <div className="absolute top-3 left-16 z-30 flex items-center space-x-1.5 rtl:space-x-reverse bg-[#1a1c1e]/90 backdrop-blur-md border border-[#41474f] rounded-lg px-2 py-1 shadow-2xl font-mono text-[11px]">
        {/* Story Level Filter */}
        <select
          value={activeStoryFilter}
          onChange={(e) => setActiveStoryFilter(e.target.value)}
          className="bg-[#282a2c] text-[#96ccff] font-bold px-2 py-1 rounded border border-[#41474f] outline-none text-[11px] cursor-pointer hover:border-[#96ccff]"
        >
          <option value="all">All Stories</option>
          {model.stories.map((s) => (
            <option key={s.id} value={s.name}>
              {s.name} (+{s.elevation.toFixed(1)}m)
            </option>
          ))}
        </select>

        <div className="w-px h-4 bg-[#41474f]" />

        {/* Projection Switcher (PERS vs ORTHO) */}
        <div className="flex bg-[#282a2c] p-0.5 rounded border border-[#41474f]">
          <button
            onClick={() => handleToggleProjection('perspective')}
            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors cursor-pointer ${
              projection === 'perspective' ? 'bg-[#96ccff] text-[#003353]' : 'text-[#c1c7d0] hover:text-white'
            }`}
            title="Perspective Camera"
          >
            PERS
          </button>
          <button
            onClick={() => handleToggleProjection('orthographic')}
            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors cursor-pointer ${
              projection === 'orthographic' ? 'bg-[#96ccff] text-[#003353]' : 'text-[#c1c7d0] hover:text-white'
            }`}
            title="Orthographic Parallel Projection"
          >
            ORTHO
          </button>
        </div>

        <div className="w-px h-4 bg-[#41474f]" />

        {/* Display Mode Selector Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowDisplayMenu(!showDisplayMenu)}
            className="flex items-center space-x-1 px-2 py-1 bg-[#282a2c] hover:bg-[#343a40] text-[#e2e2e5] rounded border border-[#41474f] cursor-pointer transition-colors"
          >
            <Sliders className="w-3.5 h-3.5 text-[#7ed99e]" />
            <span className="capitalize">{displayMode}</span>
          </button>

          {showDisplayMenu && (
            <div className="absolute top-full mt-1 left-0 w-44 bg-[#1e2022] border border-[#41474f] rounded shadow-2xl py-1 z-50">
              {(['extruded', 'wireframe', 'deformed', 'bmd', 'sfd', 'axial', 'stress'] as DisplayMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => {
                    setDisplayMode(mode);
                    setShowDisplayMenu(false);
                  }}
                  className={`w-full px-3 py-1 text-left rtl:text-right text-[11px] capitalize hover:bg-[#96ccff]/20 hover:text-[#96ccff] transition-colors ${
                    displayMode === mode ? 'text-[#7ed99e] font-bold bg-[#7ed99e]/10' : 'text-[#e2e2e5]'
                  }`}
                >
                  {mode === 'bmd' ? 'Bending Moment (M3)' : mode === 'sfd' ? 'Shear Force (V2)' : mode}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="w-px h-4 bg-[#41474f]" />

        {/* Layers Visibility Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowLayerMenu(!showLayerMenu)}
            className="flex items-center space-x-1 px-2 py-1 bg-[#282a2c] hover:bg-[#343a40] text-[#e2e2e5] rounded border border-[#41474f] cursor-pointer transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-[#96ccff]" />
            <span>Layers (10)</span>
          </button>

          {showLayerMenu && (
            <div className="absolute top-full mt-1 left-0 w-52 bg-[#1e2022] border border-[#41474f] rounded shadow-2xl p-2 z-50 space-y-1">
              <div className="text-[10px] font-bold text-[#8b919a] uppercase border-b border-[#41474f] pb-1 mb-1">
                Rendering Layers
              </div>
              {(Object.keys(layers) as (keyof LayerVisibilityState)[]).map((layerKey) => (
                <button
                  key={layerKey}
                  onClick={() => toggleLayer(layerKey)}
                  className="w-full flex items-center justify-between px-2 py-1 text-left rtl:text-right text-[11px] rounded hover:bg-[#282a2c] text-[#e2e2e5] cursor-pointer"
                >
                  <span className="capitalize">{layerKey} Layer</span>
                  {layers[layerKey] ? (
                    <Eye className="w-3.5 h-3.5 text-[#7ed99e]" />
                  ) : (
                    <EyeOff className="w-3.5 h-3.5 text-[#8b919a]" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="w-px h-4 bg-[#41474f]" />

        {/* Fit Model (Zoom Extents) Button */}
        <button
          onClick={handleFitModel}
          className="p-1 bg-[#282a2c] hover:bg-[#96ccff] hover:text-[#003353] text-[#c1c7d0] rounded border border-[#41474f] cursor-pointer transition-colors"
          title="Fit Model / Zoom Extents"
        >
          <Maximize className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Floating Bottom-Left Coordinate & Tool Status Indicator */}
      <div className="absolute bottom-3 left-16 z-30 flex items-center space-x-3 rtl:space-x-reverse bg-[#1a1c1e]/90 backdrop-blur-md border border-[#41474f] rounded px-2.5 py-1 text-[11px] font-mono text-[#c1c7d0] shadow-xl">
        <div className="flex items-center space-x-1.5">
          <span className="text-[#8b919a]">XYZ:</span>
          <span className="text-[#96ccff]">
            X: {cursorPos.x.toFixed(2)}m, Y: {cursorPos.y.toFixed(2)}m, Z: {cursorPos.z.toFixed(2)}m
          </span>
        </div>

        {selectedElementId && (
          <>
            <div className="w-px h-3.5 bg-[#41474f]" />
            <div className="flex items-center space-x-1 text-[#7ed99e]">
              <span className="text-[#8b919a]">Selected:</span>
              <span className="font-bold">{selectedElementId}</span>
            </div>
          </>
        )}

        {hoveredElementId && hoveredElementId !== selectedElementId && (
          <>
            <div className="w-px h-3.5 bg-[#41474f]" />
            <div className="flex items-center space-x-1 text-[#e2e2e5]">
              <span className="text-[#8b919a]">Hover:</span>
              <span>{hoveredElementId}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
