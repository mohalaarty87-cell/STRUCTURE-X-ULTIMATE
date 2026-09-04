import React, { useState, useCallback, useEffect } from 'react';
import {
  StructuralModel,
  StructuralMember,
  SectionProperty,
  Material,
  ActiveCadTool,
  DisplayMode,
  ViewportMode,
  ElementType,
  AnalysisSummary,
  LayerVisibilityState,
  DEFAULT_LAYER_VISIBILITY,
  ConsoleMessage,
  CameraPreset
} from './types/structure';
import { createDefaultRCBuilding } from './data/defaultModels';
import { runStructuralAnalysis } from './utils/structuralSolver';
import { StructuralModelingEngine } from './core/modeling/StructuralModelingEngine';
import { ModelIntegrityValidator } from './core/validation/ModelIntegrityValidator';
import { ProjectStorage } from './utils/projectStorage';
import { TopNavbar } from './components/TopNavbar';
import { ModelExplorer } from './components/ModelExplorer';
import { CadToolbar } from './components/CadToolbar';
import { Viewport3D } from './components/Viewport3D';
import { PropertyInspector } from './components/PropertyInspector';
import { StatusBar } from './components/StatusBar';
import { Console } from './components/Console';
import { ElementForcesModal } from './components/ElementForcesModal';
import { SectionEditorModal } from './components/SectionEditorModal';
import { RunAnalysisModal } from './components/RunAnalysisModal';
import { ReportsModal } from './components/ReportsModal';
import { TemplatesModal } from './components/TemplatesModal';
import { MaterialsModal } from './components/MaterialsModal';
import { ValidationLogsModal, HelpGuideModal } from './components/ValidationLogsModal';
import { ModelingToolsModal } from './components/ModelingToolsModal';
import { CadBimModal } from './components/CadBimModal';

export default function App() {
  // Main Structural Model State with Persistence
  const [model, setModel] = useState<StructuralModel>(() => {
    const saved = ProjectStorage.loadActiveProject();
    return saved || createDefaultRCBuilding();
  });

  // Undo / Redo History Stack (Max 30 states)
  const [history, setHistory] = useState<StructuralModel[]>([model]);
  const [historyIndex, setHistoryIndex] = useState<number>(0);

  const [analysisSummary, setAnalysisSummary] = useState<AnalysisSummary | null>(() => {
    const res = runStructuralAnalysis(model);
    return res.summary;
  });

  // UI & Viewport States
  const [activeMenu, setActiveMenu] = useState<string>('Draw');
  const [activeSidebarTab, setActiveSidebarTab] = useState<'explorer' | 'properties' | 'drawing' | 'view' | 'reports'>('explorer');
  const [selectedElementId, setSelectedElementId] = useState<string | null>('C1');
  const [selectedFilterType, setSelectedFilterType] = useState<ElementType | 'all'>('column');
  const [activeCadTool, setActiveCadTool] = useState<ActiveCadTool>('column');
  const [isSnapping, setIsSnapping] = useState<boolean>(true);
  const [displayMode, setDisplayMode] = useState<DisplayMode>('extruded');
  const [viewportMode, setViewportMode] = useState<ViewportMode>('3d');
  const [activeStoryFilter, setActiveStoryFilter] = useState<string>('all');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [lang, setLang] = useState<'en' | 'ar'>('en');

  // Phase 02: Layers & Viewport Coordinates
  const [layers, setLayers] = useState<LayerVisibilityState>(DEFAULT_LAYER_VISIBILITY);
  const [cursorCoords, setCursorCoords] = useState<{ x: number; y: number; z: number }>({ x: 0, y: 0, z: 0 });

  // Phase 02 & 03: CLI Console & Diagnostics
  const [isConsoleOpen, setIsConsoleOpen] = useState<boolean>(false);
  const [consoleMessages, setConsoleMessages] = useState<ConsoleMessage[]>([
    {
      id: 'msg-init-1',
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      text: 'STRUCTURE-X ULTIMATE v4.2 Structural Modeling & CAD Engine initialized.',
      source: 'CAD_ENGINE'
    },
    {
      id: 'msg-init-2',
      timestamp: new Date().toLocaleTimeString(),
      type: 'success',
      text: 'Phase 03 Active: Full structural entities, CAD transformations, Undo/Redo & Model Validation active.',
      source: 'ENGINE'
    },
    {
      id: 'msg-init-3',
      timestamp: new Date().toLocaleTimeString(),
      type: 'info',
      text: 'Type "help" in the console below to see CAD modeling commands (move, copy, divide, merge, align, mirror, validate).',
      source: 'CLI'
    }
  ]);

  // Modals
  const [showForcesModal, setShowForcesModal] = useState<boolean>(false);
  const [showSectionEditorModal, setShowSectionEditorModal] = useState<boolean>(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState<boolean>(false);
  const [showReportsModal, setShowReportsModal] = useState<boolean>(false);
  const [showTemplatesModal, setShowTemplatesModal] = useState<boolean>(false);
  const [showMaterialsModal, setShowMaterialsModal] = useState<boolean>(false);
  const [showValidationModal, setShowValidationModal] = useState<boolean>(false);
  const [showHelpModal, setShowHelpModal] = useState<boolean>(false);
  const [showModelingModal, setShowModelingModal] = useState<boolean>(false);
  const [showCadBimModal, setShowCadBimModal] = useState<boolean>(false);

  // Model update with history snapshot and autosave
  const handleUpdateModelWithHistory = useCallback((newModel: StructuralModel, actionDescription: string) => {
    setModel(newModel);
    ProjectStorage.saveActiveProject(newModel);

    // Truncate forward history and push new state
    setHistory(prev => {
      const truncated = prev.slice(0, historyIndex + 1);
      const next = [...truncated, JSON.parse(JSON.stringify(newModel))];
      if (next.length > 30) next.shift(); // Keep last 30
      return next;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 29));

    setConsoleMessages(prev => [
      ...prev,
      {
        id: `msg-hist-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type: 'info',
        text: `[HISTORY] ${actionDescription}`,
        source: 'HISTORY'
      }
    ]);
  }, [historyIndex]);

  // Undo Handler
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const targetIdx = historyIndex - 1;
      const targetModel = history[targetIdx];
      if (targetModel) {
        setModel(targetModel);
        setHistoryIndex(targetIdx);
        ProjectStorage.saveActiveProject(targetModel);
        setConsoleMessages(prev => [
          ...prev,
          {
            id: `msg-undo-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            type: 'warn',
            text: `Undone last action (History State ${targetIdx + 1}/${history.length})`,
            source: 'HISTORY'
          }
        ]);
      }
    }
  }, [history, historyIndex]);

  // Redo Handler
  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const targetIdx = historyIndex + 1;
      const targetModel = history[targetIdx];
      if (targetModel) {
        setModel(targetModel);
        setHistoryIndex(targetIdx);
        ProjectStorage.saveActiveProject(targetModel);
        setConsoleMessages(prev => [
          ...prev,
          {
            id: `msg-redo-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            type: 'info',
            text: `Redone action (History State ${targetIdx + 1}/${history.length})`,
            source: 'HISTORY'
          }
        ]);
      }
    }
  }, [history, historyIndex]);

  // Save Project explicitly
  const handleSaveProject = useCallback(() => {
    ProjectStorage.saveActiveProject(model);
    setConsoleMessages(prev => [
      ...prev,
      {
        id: `msg-save-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type: 'success',
        text: `Project "${model.projectName}" saved to local storage with ${model.nodes.length} joints, ${model.members.length} frames, and ${model.slabs.length} slabs.`,
        source: 'STORAGE'
      }
    ]);
  }, [model]);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if typing in an input
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        handleRedo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleSaveProject();
      } else if (e.key.toLowerCase() === 'p') {
        setShowModelingModal(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo, handleSaveProject]);

  // Execute structural analysis
  const handleExecuteSolve = () => {
    const { updatedModel, summary } = runStructuralAnalysis(model);
    setModel(updatedModel);
    setAnalysisSummary(summary);
    setIsAnalyzing(false);

    // Add success message to console
    setConsoleMessages(prev => [
      ...prev,
      {
        id: `msg-solve-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        type: 'success',
        text: `Structural analysis solved in ${summary.executionTimeMs}ms. Max member utilization: ${(summary.maxUtilization * 100).toFixed(1)}%.`,
        source: 'SOLVER'
      }
    ]);
  };

  const handleStartAnalysis = () => {
    setShowAnalysisModal(true);
  };

  // Update Section
  const handleSaveSection = (updatedSection: SectionProperty) => {
    const updated = {
      ...model,
      sections: model.sections.map(s => s.id === updatedSection.id ? updatedSection : s)
    };
    handleUpdateModelWithHistory(updated, `Updated Section Property ${updatedSection.name}`);
  };

  // Update Material
  const handleSaveMaterial = (updatedMat: Material) => {
    const updated = {
      ...model,
      materials: model.materials.map(m => m.id === updatedMat.id ? updatedMat : m)
    };
    handleUpdateModelWithHistory(updated, `Updated Material ${updatedMat.name}`);
  };

  // Select Element
  const handleSelectElement = (id: string | null) => {
    setSelectedElementId(id);
    if (id) {
      setConsoleMessages(prev => [
        ...prev,
        {
          id: `msg-sel-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: 'info',
          text: `Selected object: ${id}`,
          source: 'SELECTION'
        }
      ]);
    }
  };

  // Toggle Layer visibility
  const handleToggleLayer = (layer: keyof LayerVisibilityState) => {
    setLayers(prev => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

  // Command Line Interpreter for Console
  const handleExecuteCommand = useCallback((cmd: string) => {
    const parts = cmd.trim().split(/\s+/);
    const primary = parts[0]?.toLowerCase();
    const arg1 = parts[1]?.toLowerCase();
    const arg2 = parts[2]?.toLowerCase();
    const arg3 = parts[3]?.toLowerCase();

    const addLog = (text: string, type: 'info' | 'success' | 'warn' | 'error' = 'info') => {
      setConsoleMessages(prev => [
        ...prev,
        {
          id: `msg-cmd-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type,
          text,
          source: 'CLI'
        }
      ]);
    };

    switch (primary) {
      case 'help':
      case '?':
        addLog('=== AVAILABLE COMMANDS ===');
        addLog(' • select <id>       - Select element (e.g. "select C1", "select B12", "select W1")');
        addLog(' • deselect          - Clear selection');
        addLog(' • move <dx> <dy> <dz> - Move selected element (e.g. "move 0 3.5 0")');
        addLog(' • copy <dx> <dy> <dz> - Copy selected element (e.g. "copy 4 0 0")');
        addLog(' • delete            - Delete selected element');
        addLog(' • divide <segments> - Divide member into N segments (e.g. "divide 3")');
        addLog(' • merge             - Auto-merge coincident duplicate joints');
        addLog(' • mirror <XY|XZ|YZ> <coord> - Mirror selected element');
        addLog(' • array <count> <dx> <dy> <dz> - Linear array generation');
        addLog(' • validate          - Run complete structural model integrity check');
        addLog(' • palette / tools   - Open CAD modeling and transformation palette');
        addLog(' • undo / redo / save - History and persistence controls');
        addLog(' • fit / extents     - Fit 3D camera to bounding box');
        addLog(' • view <3d|plan|elev-xz|elev-yz|iso> - Switch camera preset');
        addLog(' • display <extruded|wireframe|deformed|bmd|sfd|axial|stress>');
        addLog(' • layer <grid|story|frame|shell|wall|load|support|result> <on|off>');
        addLog(' • stats             - Print model inventory summary');
        addLog(' • clear             - Clear console output');
        break;

      case 'palette':
      case 'tools':
      case 'draw':
        setShowModelingModal(true);
        addLog('Opened Structural Modeling Tools Palette.', 'info');
        break;

      case 'undo':
        handleUndo();
        break;

      case 'redo':
        handleRedo();
        break;

      case 'save':
        handleSaveProject();
        break;

      case 'move':
        if (!selectedElementId) {
          addLog('Select an element first before moving. E.g., "select C1" then "move 0 0 2"', 'warn');
        } else {
          const dx = parseFloat(parts[1]) || 0;
          const dy = parseFloat(parts[2]) || 0;
          const dz = parseFloat(parts[3]) || 0;
          const updated = StructuralModelingEngine.moveElements(model, [selectedElementId], { dx, dy, dz });
          handleUpdateModelWithHistory(updated, `Moved ${selectedElementId} by (${dx}, ${dy}, ${dz})`);
          addLog(`Moved element ${selectedElementId} by Δ(${dx}, ${dy}, ${dz}).`, 'success');
        }
        break;

      case 'copy':
        if (!selectedElementId) {
          addLog('Select an element first before copying.', 'warn');
        } else {
          const dx = parseFloat(parts[1]) || 4.0;
          const dy = parseFloat(parts[2]) || 0;
          const dz = parseFloat(parts[3]) || 0;
          const res = StructuralModelingEngine.copyElements(model, [selectedElementId], { dx, dy, dz });
          handleUpdateModelWithHistory(res.model, `Copied ${selectedElementId}`);
          addLog(`Copied element ${selectedElementId}. Created ${res.copiedIds.join(', ')}.`, 'success');
        }
        break;

      case 'delete':
      case 'del':
        if (!selectedElementId) {
          addLog('Select an element first to delete.', 'warn');
        } else {
          const updated = StructuralModelingEngine.deleteElements(model, [selectedElementId], { deleteOrphanJoints: true });
          handleUpdateModelWithHistory(updated, `Deleted ${selectedElementId}`);
          setSelectedElementId(null);
          addLog(`Deleted element ${selectedElementId} and reconciled topology.`, 'success');
        }
        break;

      case 'divide':
        if (!selectedElementId) {
          addLog('Select a frame member first to divide.', 'warn');
        } else {
          const segs = parseInt(parts[1], 10) || 2;
          const res = StructuralModelingEngine.divideMember(model, selectedElementId, segs);
          handleUpdateModelWithHistory(res.model, `Divided member ${selectedElementId} into ${segs} segments`);
          addLog(`Divided member ${selectedElementId} into ${segs} elements.`, 'success');
        }
        break;

      case 'merge':
        const mergeRes = StructuralModelingEngine.mergeDuplicateJoints(model, 0.005);
        if (mergeRes.mergedCount === 0) {
          addLog('No duplicate joints found within 5mm tolerance.', 'info');
        } else {
          handleUpdateModelWithHistory(mergeRes.model, `Merged ${mergeRes.mergedCount} duplicate joints`);
          addLog(`Successfully merged ${mergeRes.mergedCount} duplicate joints.`, 'success');
        }
        break;

      case 'validate':
      case 'check':
        const valReport = ModelIntegrityValidator.validate(model);
        if (valReport.isValid) {
          addLog(`✓ Model validation PASSED! 0 errors, ${valReport.totalWarnings} warnings.`, 'success');
        } else {
          addLog(`✗ Model validation FAILED: ${valReport.totalErrors} errors detected!`, 'error');
          valReport.issues.forEach(iss => addLog(`  • [${iss.code}] ${iss.title}: ${iss.message}`, iss.severity === 'ERROR' ? 'error' : 'warn'));
        }
        break;

      case 'select':
      case 'sel':
        if (!arg1) {
          addLog('Usage: select <element_id> (e.g. select C1, select B2, select S1, select W1)', 'warn');
        } else {
          const upperId = parts[1].toUpperCase();
          const foundMember = model.members.find(m => m.id.toUpperCase() === upperId);
          const foundSlab = model.slabs.find(s => s.id.toUpperCase() === upperId);
          const foundWall = model.walls?.find(w => w.id.toUpperCase() === upperId);
          const foundNode = model.nodes.find(n => n.id.toUpperCase() === upperId);

          if (foundMember || foundSlab || foundWall || foundNode) {
            setSelectedElementId(foundMember?.id || foundSlab?.id || foundWall?.id || foundNode?.id || upperId);
            addLog(`Selected element "${upperId}".`, 'success');
          } else {
            addLog(`Element "${upperId}" not found in current structural model.`, 'warn');
          }
        }
        break;

      case 'deselect':
      case 'desel':
        setSelectedElementId(null);
        addLog('Cleared object selection.', 'info');
        break;

      case 'fit':
      case 'extents':
      case 'zoom':
        setViewportMode('3d');
        addLog('Zoomed extents to fit all structural elements.', 'success');
        break;

      case 'view':
        if (arg1 === 'plan' || arg1 === 'top') {
          setViewportMode('plan');
          addLog('Switched camera to Plan View (Top Orthographic XY).', 'success');
        } else if (arg1 === 'elevation' || arg1 === 'front' || arg1 === 'elev-xz') {
          setViewportMode('elevation');
          addLog('Switched camera to Elevation View (XZ).', 'success');
        } else if (arg1 === 'side' || arg1 === 'elev-yz') {
          setViewportMode('elevation');
          addLog('Switched camera to Elevation View (YZ).', 'success');
        } else {
          setViewportMode('3d');
          addLog('Switched camera to 3D Isometric View.', 'success');
        }
        break;

      case 'display':
      case 'disp':
        if (['extruded', 'wireframe', 'deformed', 'bmd', 'sfd', 'axial', 'stress'].includes(arg1)) {
          setDisplayMode(arg1 as DisplayMode);
          addLog(`Display mode set to "${arg1}".`, 'success');
        } else {
          addLog('Usage: display <extruded|wireframe|deformed|bmd|sfd|axial|stress>', 'warn');
        }
        break;

      case 'layer':
        if (arg1 && ['grid', 'story', 'frame', 'shell', 'wall', 'load', 'support', 'result', 'selection', 'annotation'].includes(arg1)) {
          const layerKey = arg1 as keyof LayerVisibilityState;
          const turnOn = arg2 === 'on' || arg2 === 'true' || arg2 === '1';
          const turnOff = arg2 === 'off' || arg2 === 'false' || arg2 === '0';
          const newState = turnOn ? true : turnOff ? false : !layers[layerKey];
          setLayers(prev => ({ ...prev, [layerKey]: newState }));
          addLog(`Layer "${layerKey}" is now ${newState ? 'VISIBLE (ON)' : 'HIDDEN (OFF)'}.`, 'success');
        } else {
          addLog('Usage: layer <layer_name> <on|off>', 'warn');
        }
        break;

      case 'stats':
        addLog(`=== MODEL INVENTORY: ${model.projectName} ===`);
        addLog(` • Nodes: ${model.nodes.length} joints`);
        addLog(` • Frame Members: ${model.members.length} (${model.members.filter(m => m.type === 'column').length} cols, ${model.members.filter(m => m.type === 'beam').length} beams, ${model.members.filter(m => m.type === 'brace').length} braces)`);
        addLog(` • Slabs: ${model.slabs.length} shells`);
        addLog(` • Shear Walls: ${model.walls?.length || 0} wall panels`);
        addLog(` • Stories: ${model.stories.length} levels`);
        addLog(` • Diaphragms: ${model.diaphragms?.length || 0}`);
        addLog(` • Links / Springs: ${(model.links?.length || 0) + (model.springs?.length || 0)}`);
        break;

      case 'clear':
      case 'cls':
        setConsoleMessages([]);
        break;

      default:
        addLog(`Unrecognized command: "${cmd}". Type "help" for a list of valid commands.`, 'error');
        break;
    }
  }, [model, layers, selectedElementId, handleUpdateModelWithHistory, handleUndo, handleRedo, handleSaveProject]);

  const activeSelectedMember = model.members.find(m => m.id === selectedElementId) 
    || model.members.find(m => m.id === 'C1') 
    || model.members[0];

  const activeSection = model.sections.find(s => s.id === activeSelectedMember?.sectionId) || model.sections[0];
  const activeMaterial = model.materials.find(m => m.id === activeSelectedMember?.materialId) || model.materials[0];

  return (
    <div 
      className={`h-screen w-screen overflow-hidden flex flex-col bg-[#121416] text-[#e2e2e5] font-sans antialiased ${theme === 'light' ? 'light-mode-contrast' : ''}`}
      dir={lang === 'ar' ? 'rtl' : 'ltr'}
    >
      {/* 1. Top Navigation Bar */}
      <TopNavbar
        activeMenu={activeMenu}
        setActiveMenu={setActiveMenu}
        onRunAnalysis={handleStartAnalysis}
        onOpenTemplates={() => setShowTemplatesModal(true)}
        onOpenMaterials={() => setShowMaterialsModal(true)}
        onOpenSections={() => setShowSectionEditorModal(true)}
        onOpenReports={() => setShowReportsModal(true)}
        onOpenHelp={() => setShowHelpModal(true)}
        onOpenCadBim={() => setShowCadBimModal(true)}
        isAnalyzing={isAnalyzing}
        theme={theme}
        setTheme={setTheme}
        lang={lang}
        setLang={setLang}
      />

      {/* 2. Main Workspace Layout (Docked Sidebars + Viewport) */}
      <div className="flex flex-1 mt-[32px] mb-[24px] overflow-hidden relative w-full">
        {/* Left Sidebar: Model Explorer */}
        <ModelExplorer
          model={model}
          activeSidebarTab={activeSidebarTab}
          setActiveSidebarTab={setActiveSidebarTab}
          selectedElementId={selectedElementId}
          selectedFilterType={selectedFilterType}
          setSelectedFilterType={setSelectedFilterType}
          onSelectMember={handleSelectElement}
          onOpenSectionsModal={() => setShowSectionEditorModal(true)}
          onOpenMaterialsModal={() => setShowMaterialsModal(true)}
          onOpenReportsModal={() => setShowReportsModal(true)}
          onToggleMessages={() => setIsConsoleOpen(!isConsoleOpen)}
          lang={lang}
        />

        {/* Central Workspace Container */}
        <main className="flex-1 relative bg-[#0a0a0a] overflow-hidden flex">
          {/* Floating CAD / BIM Toolbar */}
          <CadToolbar
            activeTool={activeCadTool}
            setActiveTool={setActiveCadTool}
            isSnapping={isSnapping}
            setIsSnapping={setIsSnapping}
            onResetCamera={() => setViewportMode('3d')}
            onOpenModelingModal={() => setShowModelingModal(true)}
            onSetCameraPreset={(preset) => {
              if (preset === 'plan') setViewportMode('plan');
              else if (preset.startsWith('elevation')) setViewportMode('elevation');
              else setViewportMode('3d');
            }}
            lang={lang}
          />

          {/* 3D WebGL Structural Viewport with 10 Layer Architecture */}
          <Viewport3D
            model={model}
            selectedElementId={selectedElementId}
            onSelectElement={handleSelectElement}
            activeTool={activeCadTool}
            displayMode={displayMode}
            setDisplayMode={setDisplayMode}
            viewportMode={viewportMode}
            setViewportMode={setViewportMode}
            isAnalyzing={isAnalyzing}
            activeStoryFilter={activeStoryFilter}
            setActiveStoryFilter={setActiveStoryFilter}
            layerVisibility={layers}
            onToggleLayer={handleToggleLayer}
            onUpdateCoordinates={setCursorCoords}
            lang={lang}
          />

          {/* Phase 02 Interactive Engineering Console & CLI */}
          <Console
            messages={consoleMessages}
            onSendMessage={(msg) => setConsoleMessages(prev => [...prev, msg])}
            onClearMessages={() => setConsoleMessages([])}
            onExecuteCommand={handleExecuteCommand}
            isOpen={isConsoleOpen}
            onToggleOpen={() => setIsConsoleOpen(!isConsoleOpen)}
            lang={lang}
          />
        </main>

        {/* Right Sidebar: Property Inspector */}
        <PropertyInspector
          model={model}
          selectedElementId={selectedElementId}
          onOpenForcesModal={() => setShowForcesModal(true)}
          onOpenSectionEditor={() => setShowSectionEditorModal(true)}
          onDeleteMember={(id) => {
            const updated = StructuralModelingEngine.deleteElements(model, [id], { deleteOrphanJoints: true });
            handleUpdateModelWithHistory(updated, `Deleted element ${id}`);
            setSelectedElementId(null);
          }}
          lang={lang}
        />
      </div>

      {/* 3. Bottom Status Bar */}
      <StatusBar
        model={model}
        selectedElementId={selectedElementId}
        cursorCoordinates={cursorCoords}
        isSnapping={isSnapping}
        projectionMode={viewportMode === 'plan' || viewportMode === 'elevation' ? 'ORTHO' : 'PERS'}
        isConsoleOpen={isConsoleOpen}
        onToggleConsole={() => setIsConsoleOpen(!isConsoleOpen)}
        onOpenValidationModal={() => setShowValidationModal(true)}
        onSelectUnit={(unit) => handleUpdateModelWithHistory({ ...model, units: unit }, `Changed units to ${unit}`)}
        lang={lang}
      />

      {/* 4. Interactive Modals */}
      {showModelingModal && (
        <ModelingToolsModal
          isOpen={showModelingModal}
          onClose={() => setShowModelingModal(false)}
          model={model}
          onUpdateModel={handleUpdateModelWithHistory}
          selectedElementId={selectedElementId}
          onSelectElement={handleSelectElement}
          canUndo={historyIndex > 0}
          canRedo={historyIndex < history.length - 1}
          onUndo={handleUndo}
          onRedo={handleRedo}
          onSaveProject={handleSaveProject}
          lang={lang}
        />
      )}

      {showForcesModal && (
        <ElementForcesModal
          member={activeSelectedMember}
          section={activeSection}
          material={activeMaterial}
          onClose={() => setShowForcesModal(false)}
          lang={lang}
        />
      )}

      {showSectionEditorModal && (
        <SectionEditorModal
          sections={model.sections}
          materials={model.materials}
          onSaveSection={handleSaveSection}
          onClose={() => setShowSectionEditorModal(false)}
          lang={lang}
        />
      )}

      {showAnalysisModal && (
        <RunAnalysisModal
          model={model}
          onExecuteSolve={handleExecuteSolve}
          summary={analysisSummary}
          onClose={() => setShowAnalysisModal(false)}
          lang={lang}
          onLoadModel={(newModel, desc) => {
            handleUpdateModelWithHistory(newModel, desc);
            const res = runStructuralAnalysis(newModel);
            setAnalysisSummary(res.summary);
            setSelectedElementId(newModel.members[0]?.id || null);
            setConsoleMessages(prev => [
              ...prev,
              {
                id: `msg-scale-${Date.now()}`,
                timestamp: new Date().toLocaleTimeString(),
                type: 'success',
                text: `[PHASE 15 SCALE] Loaded large-scale model: ${desc} (${newModel.members.length.toLocaleString()} elements)`,
                source: 'SOLVER'
              }
            ]);
          }}
        />
      )}

      {showReportsModal && (
        <ReportsModal
          model={model}
          summary={analysisSummary}
          onClose={() => setShowReportsModal(false)}
          lang={lang}
        />
      )}

      {showTemplatesModal && (
        <TemplatesModal
          onSelectModel={(newModel) => {
            handleUpdateModelWithHistory(newModel, `Loaded template model ${newModel.projectName}`);
            const res = runStructuralAnalysis(newModel);
            setAnalysisSummary(res.summary);
            setSelectedElementId(newModel.members[0]?.id || null);
          }}
          onClose={() => setShowTemplatesModal(false)}
          lang={lang}
        />
      )}

      {showMaterialsModal && (
        <MaterialsModal
          materials={model.materials}
          onSaveMaterial={handleSaveMaterial}
          onClose={() => setShowMaterialsModal(false)}
          lang={lang}
        />
      )}

      {showValidationModal && (
        <ValidationLogsModal
          model={model}
          onClose={() => setShowValidationModal(false)}
          lang={lang}
        />
      )}

      {showHelpModal && (
        <HelpGuideModal
          onClose={() => setShowHelpModal(false)}
          lang={lang}
        />
      )}

      {showCadBimModal && (
        <CadBimModal
          currentModel={model}
          onCommitModel={(newModel, actionDescription) => {
            handleUpdateModelWithHistory(newModel, actionDescription);
            const res = runStructuralAnalysis(newModel);
            setAnalysisSummary(res.summary);
            setSelectedElementId(newModel.members[0]?.id || null);
          }}
          onClose={() => setShowCadBimModal(false)}
          lang={lang}
        />
      )}
    </div>
  );
}

