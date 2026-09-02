import React, { useState } from 'react';
import {
  X,
  Compass,
  Move,
  Copy,
  Trash2,
  FlipHorizontal,
  Grid,
  Scissors,
  Merge,
  AlignLeft,
  Layers,
  Plus,
  CircleDot,
  Minus,
  Columns3,
  Square,
  Building2,
  Anchor,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  RotateCw,
  Save,
  Check,
  RefreshCw,
  Sparkles,
  Sliders,
  ShieldCheck,
  Maximize2
} from 'lucide-react';
import {
  StructuralModel,
  NodePoint,
  StructuralMember,
  SlabElement,
  WallElement,
  OpeningElement,
  LinkElement,
  SpringElement,
  DiaphragmDefinition,
  ElementType
} from '../types/structure';
import { StructuralModelingEngine, Point3D } from '../core/modeling/StructuralModelingEngine';
import { ModelIntegrityValidator, ValidationReport } from '../core/validation/ModelIntegrityValidator';

interface ModelingToolsModalProps {
  isOpen: boolean;
  onClose: () => void;
  model: StructuralModel;
  onUpdateModel: (newModel: StructuralModel, actionDescription: string) => void;
  selectedElementId: string | null;
  onSelectElement: (id: string | null) => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onSaveProject: () => void;
  lang: 'en' | 'ar';
}

type ModelingTab = 'draw' | 'transform' | 'replicate' | 'mesh' | 'validate' | 'diaphragm';

export const ModelingToolsModal: React.FC<ModelingToolsModalProps> = ({
  isOpen,
  onClose,
  model,
  onUpdateModel,
  selectedElementId,
  onSelectElement,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onSaveProject,
  lang
}) => {
  const [activeTab, setActiveTab] = useState<ModelingTab>('draw');

  // Draw sub-tool
  const [drawEntity, setDrawEntity] = useState<
    'joint' | 'member' | 'slab' | 'wall' | 'opening' | 'link' | 'spring'
  >('joint');

  // Form states for Drawing
  const [jointForm, setJointForm] = useState({ x: 0, y: 3.5, z: 0, isRestrained: 'free' });
  const [memberForm, setMemberForm] = useState({
    type: 'column' as 'column' | 'beam' | 'brace',
    startNodeId: '',
    endNodeId: '',
    sectionId: model.sections[0]?.id || 'sec-400rc',
    materialId: model.materials[0]?.id || 'mat-c3037',
    story: model.stories[1]?.name || 'Story 1',
    releases: 'Continuous' as 'Continuous' | 'Pinned-Pinned',
    localAngle: 0
  });
  const [slabForm, setSlabForm] = useState({
    story: model.stories[1]?.name || 'Story 1',
    thickness: 0.2,
    materialId: model.materials[0]?.id || 'mat-c3037',
    nodeIds: '',
    diaphragm: 'rigid' as 'rigid' | 'semi-rigid' | 'flexible' | 'none',
    loadDead: 2.5,
    loadLive: 3.0
  });
  const [wallForm, setWallForm] = useState({
    story: model.stories[1]?.name || 'Story 1',
    thickness: 0.25,
    materialId: model.materials[0]?.id || 'mat-c3037',
    nodeIds: '',
    loadDistributed: 0
  });
  const [openingForm, setOpeningForm] = useState({
    parentType: 'slab' as 'slab' | 'wall',
    parentId: model.slabs[0]?.id || '',
    story: model.stories[1]?.name || 'Story 1',
    nodeIds: '',
    width: 1.5,
    height: 1.5
  });
  const [linkForm, setLinkForm] = useState({
    startNodeId: '',
    endNodeId: '',
    type: 'linear' as 'linear' | 'gap' | 'hook' | 'damper',
    kx: 10000,
    ky: 10000,
    kz: 10000
  });
  const [springForm, setSpringForm] = useState({
    nodeId: '',
    type: 'ground' as 'ground' | 'line',
    kx: 50000,
    ky: 50000,
    kz: 50000
  });
  const [diaphragmForm, setDiaphragmForm] = useState({
    story: model.stories[1]?.name || 'Story 1',
    type: 'rigid' as 'rigid' | 'semi-rigid' | 'flexible'
  });

  // Transform states
  const [moveDelta, setMoveDelta] = useState({ dx: 0, dy: 0, dz: 0 });
  const [copyDelta, setCopyDelta] = useState({ dx: 4.0, dy: 0, dz: 0 });
  const [mirrorPlane, setMirrorPlane] = useState<'XY' | 'XZ' | 'YZ'>('YZ');
  const [mirrorCoord, setMirrorCoord] = useState(0);
  const [linearArrayForm, setLinearArrayForm] = useState({ count: 3, dx: 4.0, dy: 0, dz: 0 });
  const [radialArrayForm, setRadialArrayForm] = useState({
    count: 4,
    cx: 0,
    cy: 0,
    cz: 0,
    axis: 'Y' as 'X' | 'Y' | 'Z',
    angleDeg: 90
  });
  const [divideForm, setDivideForm] = useState({ segments: 2 });
  const [alignForm, setAlignForm] = useState({ axis: 'X' as 'X' | 'Y' | 'Z', targetType: 'mean' as 'mean' | 'min' | 'max' | 'custom', customVal: 0 });
  const [replicateForm, setReplicateForm] = useState({
    sourceStory: model.stories[1]?.name || 'Story 1',
    targetStories: [model.stories[2]?.name || 'Story 2']
  });

  // Validation report state
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(() => ModelIntegrityValidator.validate(model));
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  if (!isOpen) return null;

  const showFeedback = (msg: string) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 4000);
  };

  // 1. Draw Actions
  const handleAddJoint = () => {
    let restraints: NodePoint['isRestrained'] = undefined;
    if (jointForm.isRestrained === 'fixed') {
      restraints = { fx: true, fy: true, fz: true, mx: true, my: true, mz: true };
    } else if (jointForm.isRestrained === 'pinned') {
      restraints = { fx: true, fy: true, fz: true, mx: false, my: false, mz: false };
    } else if (jointForm.isRestrained === 'roller') {
      restraints = { fx: false, fy: true, fz: false, mx: false, my: false, mz: false };
    }

    const res = StructuralModelingEngine.addJoint(model, {
      x: Number(jointForm.x),
      y: Number(jointForm.y),
      z: Number(jointForm.z)
    }, {
      isRestrained: restraints
    });

    onUpdateModel(res.model, `Added Joint ${res.joint.id} at (${jointForm.x}, ${jointForm.y}, ${jointForm.z})`);
    onSelectElement(res.joint.id);
    showFeedback(`Joint ${res.joint.id} ${res.isExisting ? 'already exists' : 'created successfully'}!`);
  };

  const handleAddMember = () => {
    try {
      const res = StructuralModelingEngine.addFrameMember(model, {
        type: memberForm.type,
        startNodeId: memberForm.startNodeId,
        endNodeId: memberForm.endNodeId,
        sectionId: memberForm.sectionId,
        materialId: memberForm.materialId,
        story: memberForm.story,
        releases: memberForm.releases,
        localAxisAngle: Number(memberForm.localAngle)
      });
      onUpdateModel(res.model, `Added ${memberForm.type.toUpperCase()} ${res.member.id}`);
      onSelectElement(res.member.id);
      showFeedback(`Created ${memberForm.type} ${res.member.id} (${res.member.length}m)!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddSlab = () => {
    try {
      const ids = slabForm.nodeIds.split(',').map(s => s.trim()).filter(Boolean);
      if (ids.length < 3) {
        alert('Please enter at least 3 comma-separated Joint IDs (e.g. N_L1_0_0, N_L1_1_0, N_L1_1_1, N_L1_0_1)');
        return;
      }
      const res = StructuralModelingEngine.addSlab(model, {
        story: slabForm.story,
        thickness: Number(slabForm.thickness),
        materialId: slabForm.materialId,
        nodeIds: ids,
        diaphragm: slabForm.diaphragm,
        loadDead: Number(slabForm.loadDead),
        loadLive: Number(slabForm.loadLive)
      });
      onUpdateModel(res.model, `Added Slab ${res.slab.id}`);
      onSelectElement(res.slab.id);
      showFeedback(`Created Slab Shell ${res.slab.id} (${res.slab.thickness * 1000}mm)!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddWall = () => {
    try {
      const ids = wallForm.nodeIds.split(',').map(s => s.trim()).filter(Boolean);
      if (ids.length < 4) {
        alert('Please enter 4 corner Joint IDs (e.g. N_L0_0_0, N_L0_1_0, N_L1_1_0, N_L1_0_0)');
        return;
      }
      const res = StructuralModelingEngine.addWall(model, {
        story: wallForm.story,
        thickness: Number(wallForm.thickness),
        materialId: wallForm.materialId,
        nodeIds: ids,
        loadDistributed: Number(wallForm.loadDistributed)
      });
      onUpdateModel(res.model, `Added Shear Wall ${res.wall.id}`);
      onSelectElement(res.wall.id);
      showFeedback(`Created Shear Wall ${res.wall.id}!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddOpening = () => {
    try {
      const ids = openingForm.nodeIds.split(',').map(s => s.trim()).filter(Boolean);
      const res = StructuralModelingEngine.addOpening(model, {
        parentType: openingForm.parentType,
        parentId: openingForm.parentId,
        story: openingForm.story,
        nodeIds: ids.length >= 3 ? ids : undefined,
        width: Number(openingForm.width),
        height: Number(openingForm.height)
      });
      onUpdateModel(res.model, `Added Opening ${res.opening.id}`);
      showFeedback(`Created Opening Cutout ${res.opening.id}!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddLink = () => {
    try {
      const res = StructuralModelingEngine.addLink(model, {
        startNodeId: linkForm.startNodeId,
        endNodeId: linkForm.endNodeId,
        type: linkForm.type,
        stiffness: {
          kx: Number(linkForm.kx),
          ky: Number(linkForm.ky),
          kz: Number(linkForm.kz)
        }
      });
      onUpdateModel(res.model, `Added Link ${res.link.id}`);
      showFeedback(`Created Two-Node Link ${res.link.id}!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAddSpring = () => {
    try {
      const res = StructuralModelingEngine.addSpring(model, {
        nodeId: springForm.nodeId,
        type: springForm.type,
        kx: Number(springForm.kx),
        ky: Number(springForm.ky),
        kz: Number(springForm.kz)
      });
      onUpdateModel(res.model, `Added Spring ${res.spring.id}`);
      showFeedback(`Created Foundation Spring ${res.spring.id}!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleAssignDiaphragm = () => {
    const storyNodes = model.nodes.filter(n => {
      const story = model.stories.find(s => s.name === diaphragmForm.story);
      return story && Math.abs(n.y - story.elevation) < 0.1;
    });

    if (storyNodes.length === 0) {
      alert(`No joints found on story "${diaphragmForm.story}"`);
      return;
    }

    const res = StructuralModelingEngine.assignDiaphragm(model, {
      story: diaphragmForm.story,
      type: diaphragmForm.type,
      nodeIds: storyNodes.map(n => n.id)
    });
    onUpdateModel(res.model, `Assigned ${diaphragmForm.type} Diaphragm to ${diaphragmForm.story}`);
    showFeedback(`Assigned ${diaphragmForm.type} Diaphragm (${storyNodes.length} joints constrained)!`);
  };

  // 2. Transform Actions
  const handleMove = () => {
    if (!selectedElementId) {
      alert('Please select an element first (e.g. C1, B12, S1, or a Joint ID).');
      return;
    }
    const updated = StructuralModelingEngine.moveElements(model, [selectedElementId], {
      dx: Number(moveDelta.dx),
      dy: Number(moveDelta.dy),
      dz: Number(moveDelta.dz)
    });
    onUpdateModel(updated, `Moved ${selectedElementId} by (${moveDelta.dx}, ${moveDelta.dy}, ${moveDelta.dz})`);
    showFeedback(`Moved selected element ${selectedElementId} successfully.`);
  };

  const handleCopy = () => {
    if (!selectedElementId) {
      alert('Please select an element first to copy.');
      return;
    }
    const res = StructuralModelingEngine.copyElements(model, [selectedElementId], {
      dx: Number(copyDelta.dx),
      dy: Number(copyDelta.dy),
      dz: Number(copyDelta.dz)
    });
    onUpdateModel(res.model, `Copied ${selectedElementId} (Created ${res.copiedIds.join(', ')})`);
    if (res.copiedIds[0]) onSelectElement(res.copiedIds[0]);
    showFeedback(`Copied successfully: created ${res.copiedIds.length} new entity/entities.`);
  };

  const handleDelete = (deleteOrphans: boolean = true) => {
    if (!selectedElementId) {
      alert('Please select an element to delete.');
      return;
    }
    const updated = StructuralModelingEngine.deleteElements(model, [selectedElementId], {
      deleteOrphanJoints: deleteOrphans
    });
    onUpdateModel(updated, `Deleted element ${selectedElementId}`);
    onSelectElement(null);
    showFeedback(`Deleted element ${selectedElementId} and reconciled topology.`);
  };

  const handleMirror = () => {
    if (!selectedElementId) {
      alert('Please select elements to mirror.');
      return;
    }
    const res = StructuralModelingEngine.mirrorElements(model, [selectedElementId], {
      axis: mirrorPlane,
      coordinate: Number(mirrorCoord)
    });
    onUpdateModel(res.model, `Mirrored ${selectedElementId} across ${mirrorPlane}`);
    showFeedback(`Mirrored ${selectedElementId}: created ${res.createdIds.length} mirrored entities.`);
  };

  const handleLinearArray = () => {
    if (!selectedElementId) {
      alert('Please select elements to array.');
      return;
    }
    const res = StructuralModelingEngine.linearArray(model, [selectedElementId], Number(linearArrayForm.count), {
      dx: Number(linearArrayForm.dx),
      dy: Number(linearArrayForm.dy),
      dz: Number(linearArrayForm.dz)
    });
    onUpdateModel(res.model, `Linear array of ${selectedElementId} (${linearArrayForm.count}x)`);
    showFeedback(`Generated linear array (${res.createdIds.length} entities created).`);
  };

  const handleRadialArray = () => {
    if (!selectedElementId) {
      alert('Please select elements to rotate array.');
      return;
    }
    const res = StructuralModelingEngine.radialArray(
      model,
      [selectedElementId],
      Number(radialArrayForm.count),
      { x: Number(radialArrayForm.cx), y: Number(radialArrayForm.cy), z: Number(radialArrayForm.cz) },
      radialArrayForm.axis,
      Number(radialArrayForm.angleDeg)
    );
    onUpdateModel(res.model, `Radial array of ${selectedElementId} (${radialArrayForm.count}x @ ${radialArrayForm.angleDeg}°)`);
    showFeedback(`Generated radial array (${res.createdIds.length} entities created).`);
  };

  const handleDivide = () => {
    if (!selectedElementId || !selectedElementId.match(/^(C|B|BR)\d+/i)) {
      alert('Please select a frame member (Column, Beam, or Brace) to divide.');
      return;
    }
    const res = StructuralModelingEngine.divideMember(model, selectedElementId, Number(divideForm.segments));
    onUpdateModel(res.model, `Divided member ${selectedElementId} into ${divideForm.segments} segments`);
    if (res.newMemberIds[0]) onSelectElement(res.newMemberIds[0]);
    showFeedback(`Divided member ${selectedElementId} into ${divideForm.segments} elements with intermediate joints.`);
  };

  const handleMergeDuplicates = () => {
    const res = StructuralModelingEngine.mergeDuplicateJoints(model, 0.005);
    if (res.mergedCount === 0) {
      showFeedback('No duplicate coincident joints found within 5mm tolerance.');
    } else {
      onUpdateModel(res.model, `Merged ${res.mergedCount} coincident joints`);
      showFeedback(`Successfully merged ${res.mergedCount} duplicate joints and updated member connectivity.`);
    }
  };

  const handleAlign = () => {
    if (!selectedElementId) {
      alert('Please select elements/joints to align.');
      return;
    }
    let target: number | 'min' | 'max' | 'mean' = alignForm.targetType;
    if (alignForm.targetType === 'custom') {
      target = Number(alignForm.customVal);
    }
    const updated = StructuralModelingEngine.alignElements(model, [selectedElementId], alignForm.axis, target);
    onUpdateModel(updated, `Aligned ${selectedElementId} along ${alignForm.axis} axis`);
    showFeedback(`Aligned elements along ${alignForm.axis} axis.`);
  };

  const handleStoryReplicate = () => {
    if (!selectedElementId) {
      alert('Please select elements to replicate across stories.');
      return;
    }
    const res = StructuralModelingEngine.replicateToStories(
      model,
      [selectedElementId],
      replicateForm.sourceStory,
      replicateForm.targetStories
    );
    onUpdateModel(res.model, `Replicated ${selectedElementId} to ${replicateForm.targetStories.join(', ')}`);
    showFeedback(`Replicated to target stories (${res.createdIds.length} new structural elements created).`);
  };

  const handleRunValidation = () => {
    const report = ModelIntegrityValidator.validate(model);
    setValidationReport(report);
    if (report.isValid) {
      showFeedback('Model integrity verified! Zero errors found. Ready for structural analysis.');
    } else {
      showFeedback(`Validation completed with ${report.totalErrors} errors and ${report.totalWarnings} warnings.`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl text-[13px] text-[#e2e2e5] overflow-hidden">
        {/* Header Bar */}
        <div className="bg-[#282a2c] px-4 py-3 border-b border-[#41474f] flex items-center justify-between">
          <div className="flex items-center space-x-3 rtl:space-x-reverse">
            <div className="w-8 h-8 rounded bg-[#96ccff]/20 flex items-center justify-center text-[#96ccff]">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#e2e2e5]">
                {lang === 'ar' ? 'محرك النمذجة الإنشائية وأدوات الرسم' : 'Structural Modeling Engine & CAD Operations'}
              </h2>
              <div className="text-[11px] text-[#c1c7d0] flex items-center space-x-3 rtl:space-x-reverse">
                <span>Phase 03 Active Engine</span>
                <span className="text-[#96ccff]">Model: {model.projectName}</span>
                {selectedElementId && (
                  <span className="bg-[#96ccff]/20 text-[#96ccff] px-2 py-0.5 rounded font-mono text-[10px]">
                    Selected: {selectedElementId}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            {/* Quick Undo / Redo */}
            <button
              onClick={onUndo}
              disabled={!canUndo}
              className={`p-1.5 rounded transition-colors ${canUndo ? 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5] cursor-pointer' : 'text-[#555a60] cursor-not-allowed'}`}
              title="Undo (Ctrl+Z)"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={onRedo}
              disabled={!canRedo}
              className={`p-1.5 rounded transition-colors ${canRedo ? 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5] cursor-pointer' : 'text-[#555a60] cursor-not-allowed'}`}
              title="Redo (Ctrl+Y)"
            >
              <RotateCw className="w-4 h-4" />
            </button>
            <div className="w-px h-5 bg-[#41474f]" />
            <button
              onClick={onSaveProject}
              className="flex items-center space-x-1.5 bg-[#47a26b]/20 hover:bg-[#47a26b]/30 text-[#7ed99e] border border-[#7ed99e]/40 px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{lang === 'ar' ? 'حفظ' : 'Autosaved'}</span>
            </button>
            <button
              onClick={onClose}
              className="text-[#c1c7d0] hover:text-[#e2e2e5] hover:bg-[#333537] p-1.5 rounded cursor-pointer transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Feedback Banner */}
        {actionNotice && (
          <div className="bg-[#7ed99e]/15 border-b border-[#7ed99e]/30 px-4 py-1.5 text-xs text-[#7ed99e] flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionNotice}</span>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-[#41474f] bg-[#1a1c1e] px-4 space-x-1 rtl:space-x-reverse overflow-x-auto">
          {[
            { id: 'draw' as ModelingTab, label: '1. Draw Entities', icon: Plus },
            { id: 'transform' as ModelingTab, label: '2. Move / Copy / Mirror', icon: Move },
            { id: 'replicate' as ModelingTab, label: '3. Story Replicate / Array', icon: Grid },
            { id: 'mesh' as ModelingTab, label: '4. Divide / Merge / Align', icon: Scissors },
            { id: 'diaphragm' as ModelingTab, label: '5. Diaphragms & Links', icon: Activity },
            { id: 'validate' as ModelingTab, label: '6. Model Validation', icon: ShieldCheck }
          ].map(t => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center space-x-2 rtl:space-x-reverse px-3.5 py-2.5 border-b-2 font-medium text-xs whitespace-nowrap transition-colors cursor-pointer ${
                  active
                    ? 'border-[#96ccff] text-[#96ccff] bg-[#282a2c]'
                    : 'border-transparent text-[#c1c7d0] hover:text-[#e2e2e5] hover:bg-[#282a2c]/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* TAB 1: DRAW ENTITIES */}
          {activeTab === 'draw' && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2 pb-3 border-b border-[#41474f]">
                {[
                  { id: 'joint', label: 'Joint (Point)', icon: CircleDot },
                  { id: 'member', label: 'Frame (Column/Beam/Brace)', icon: Columns3 },
                  { id: 'slab', label: 'Slab Area Shell', icon: Square },
                  { id: 'wall', label: 'Shear Wall', icon: Building2 },
                  { id: 'opening', label: 'Opening / Cutout', icon: Minus },
                  { id: 'link', label: 'Two-Node Link', icon: Activity },
                  { id: 'spring', label: 'Base Spring', icon: Anchor }
                ].map(ent => {
                  const Icon = ent.icon;
                  return (
                    <button
                      key={ent.id}
                      onClick={() => setDrawEntity(ent.id as any)}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs transition-colors cursor-pointer ${
                        drawEntity === ent.id
                          ? 'bg-[#96ccff] text-[#003353] font-semibold'
                          : 'bg-[#333537] text-[#c1c7d0] hover:bg-[#41474f] hover:text-[#e2e2e5]'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{ent.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Joint Form */}
              {drawEntity === 'joint' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw Joint Object (Node)</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">X Coordinate (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={jointForm.x}
                        onChange={e => setJointForm({ ...jointForm, x: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Y Elevation (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={jointForm.y}
                        onChange={e => setJointForm({ ...jointForm, y: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Z Coordinate (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={jointForm.z}
                        onChange={e => setJointForm({ ...jointForm, z: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Boundary Support Restraint</label>
                    <select
                      value={jointForm.isRestrained}
                      onChange={e => setJointForm({ ...jointForm, isRestrained: e.target.value })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      <option value="free">Free Node (No Restraints - Typical Floor/Roof)</option>
                      <option value="fixed">Fixed Base (UX, UY, UZ, RX, RY, RZ Restrained)</option>
                      <option value="pinned">Pinned Base (UX, UY, UZ Restrained, Moments Free)</option>
                      <option value="roller">Roller Support (Vertical UY Restrained)</option>
                    </select>
                  </div>
                  <button
                    onClick={handleAddJoint}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Add Joint to Model
                  </button>
                </div>
              )}

              {/* Member Form */}
              {drawEntity === 'member' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw 1D Frame Member (Column, Beam, Brace)</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Member Type</label>
                      <select
                        value={memberForm.type}
                        onChange={e => setMemberForm({ ...memberForm, type: e.target.value as any })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        <option value="column">Column (Vertical Frame)</option>
                        <option value="beam">Beam (Horizontal Floor Beam)</option>
                        <option value="brace">Brace (Diagonal Truss/Bracing)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Start Joint (I-End)</label>
                      <select
                        value={memberForm.startNodeId}
                        onChange={e => setMemberForm({ ...memberForm, startNodeId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      >
                        <option value="">Select Joint...</option>
                        {model.nodes.map(n => (
                          <option key={n.id} value={n.id}>
                            {n.id} ({n.x}, {n.y}, {n.z})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">End Joint (J-End)</label>
                      <select
                        value={memberForm.endNodeId}
                        onChange={e => setMemberForm({ ...memberForm, endNodeId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      >
                        <option value="">Select Joint...</option>
                        {model.nodes.map(n => (
                          <option key={n.id} value={n.id}>
                            {n.id} ({n.x}, {n.y}, {n.z})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Section Property</label>
                      <select
                        value={memberForm.sectionId}
                        onChange={e => setMemberForm({ ...memberForm, sectionId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.sections.map(s => (
                          <option key={s.id} value={s.id}>{s.name} ({s.shape})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Material</label>
                      <select
                        value={memberForm.materialId}
                        onChange={e => setMemberForm({ ...memberForm, materialId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.materials.map(m => (
                          <option key={m.id} value={m.id}>{m.name} ({m.type})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Story Assignment</label>
                      <select
                        value={memberForm.story}
                        onChange={e => setMemberForm({ ...memberForm, story: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.stories.map(s => (
                          <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={handleAddMember}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Create Frame Member
                  </button>
                </div>
              )}

              {/* Slab Form */}
              {drawEntity === 'slab' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw 2D Planar Slab Shell</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Thickness (m)</label>
                      <input
                        type="number"
                        step="0.05"
                        value={slabForm.thickness}
                        onChange={e => setSlabForm({ ...slabForm, thickness: parseFloat(e.target.value) || 0.2 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Story Level</label>
                      <select
                        value={slabForm.story}
                        onChange={e => setSlabForm({ ...slabForm, story: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.stories.map(s => (
                          <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">
                      Boundary Vertex Joint IDs (Comma-separated, 3 or 4 joints)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. N_L1_0_0, N_L1_1_0, N_L1_1_1, N_L1_0_1"
                      value={slabForm.nodeIds}
                      onChange={e => setSlabForm({ ...slabForm, nodeIds: e.target.value })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Diaphragm Constraint</label>
                      <select
                        value={slabForm.diaphragm}
                        onChange={e => setSlabForm({ ...slabForm, diaphragm: e.target.value as any })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        <option value="rigid">Rigid Diaphragm</option>
                        <option value="semi-rigid">Semi-Rigid Shell</option>
                        <option value="flexible">Flexible Diaphragm</option>
                        <option value="none">None (Independent Nodes)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Dead Load (kN/m²)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={slabForm.loadDead}
                        onChange={e => setSlabForm({ ...slabForm, loadDead: parseFloat(e.target.value) || 2.5 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Live Load (kN/m²)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={slabForm.loadLive}
                        onChange={e => setSlabForm({ ...slabForm, loadLive: parseFloat(e.target.value) || 3.0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleAddSlab}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Generate Slab Shell Element
                  </button>
                </div>
              )}

              {/* Wall Form */}
              {drawEntity === 'wall' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw Shear Wall Shell</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Wall Thickness (m)</label>
                      <input
                        type="number"
                        step="0.05"
                        value={wallForm.thickness}
                        onChange={e => setWallForm({ ...wallForm, thickness: parseFloat(e.target.value) || 0.25 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Story Level</label>
                      <select
                        value={wallForm.story}
                        onChange={e => setWallForm({ ...wallForm, story: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.stories.map(s => (
                          <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">
                      4 Corner Joint IDs (Bottom-Left, Bottom-Right, Top-Right, Top-Left)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. N_L0_0_0, N_L0_1_0, N_L1_1_0, N_L1_0_0"
                      value={wallForm.nodeIds}
                      onChange={e => setWallForm({ ...wallForm, nodeIds: e.target.value })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <button
                    onClick={handleAddWall}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Create Shear Wall
                  </button>
                </div>
              )}

              {/* Opening Form */}
              {drawEntity === 'opening' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw Slab / Wall Opening</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Parent Entity</label>
                      <select
                        value={openingForm.parentId}
                        onChange={e => setOpeningForm({ ...openingForm, parentId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        {model.slabs.map(s => (
                          <option key={s.id} value={s.id}>Slab {s.id} ({s.story})</option>
                        ))}
                        {model.walls?.map(w => (
                          <option key={w.id} value={w.id}>Wall {w.id} ({w.story})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Opening Dimensions (Width x Height)</label>
                      <div className="flex space-x-2">
                        <input
                          type="number"
                          step="0.1"
                          placeholder="Width (m)"
                          value={openingForm.width}
                          onChange={e => setOpeningForm({ ...openingForm, width: parseFloat(e.target.value) || 1.0 })}
                          className="w-1/2 bg-[#1e2022] border border-[#41474f] rounded px-2 py-1.5 text-xs"
                        />
                        <input
                          type="number"
                          step="0.1"
                          placeholder="Height (m)"
                          value={openingForm.height}
                          onChange={e => setOpeningForm({ ...openingForm, height: parseFloat(e.target.value) || 1.0 })}
                          className="w-1/2 bg-[#1e2022] border border-[#41474f] rounded px-2 py-1.5 text-xs"
                        />
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={handleAddOpening}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Add Opening Cutout
                  </button>
                </div>
              )}

              {/* Link Form */}
              {drawEntity === 'link' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw Two-Node Link Element</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Start Joint</label>
                      <select
                        value={linkForm.startNodeId}
                        onChange={e => setLinkForm({ ...linkForm, startNodeId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      >
                        <option value="">Select Joint...</option>
                        {model.nodes.map(n => <option key={n.id} value={n.id}>{n.id}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">End Joint</label>
                      <select
                        value={linkForm.endNodeId}
                        onChange={e => setLinkForm({ ...linkForm, endNodeId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      >
                        <option value="">Select Joint...</option>
                        {model.nodes.map(n => <option key={n.id} value={n.id}>{n.id}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Link Type</label>
                      <select
                        value={linkForm.type}
                        onChange={e => setLinkForm({ ...linkForm, type: e.target.value as any })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                      >
                        <option value="linear">Linear Elastic</option>
                        <option value="gap">Compression Gap</option>
                        <option value="hook">Tension Hook</option>
                        <option value="damper">Viscous Damper</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={handleAddLink}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Create Link Element
                  </button>
                </div>
              )}

              {/* Spring Form */}
              {drawEntity === 'spring' && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <h3 className="font-semibold text-[#96ccff] text-sm">Draw Foundation Spring (Soil-Structure Interaction)</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Joint ID</label>
                      <select
                        value={springForm.nodeId}
                        onChange={e => setSpringForm({ ...springForm, nodeId: e.target.value })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      >
                        <option value="">Select Base Joint...</option>
                        {model.nodes.map(n => <option key={n.id} value={n.id}>{n.id} (Y={n.y})</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[#c1c7d0] mb-1">Vertical Stiffness Kz (kN/m)</label>
                      <input
                        type="number"
                        value={springForm.kz}
                        onChange={e => setSpringForm({ ...springForm, kz: parseFloat(e.target.value) || 50000 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleAddSpring}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                  >
                    + Attach Ground Spring
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: MOVE, COPY, MIRROR, DELETE */}
          {activeTab === 'transform' && (
            <div className="space-y-4">
              <div className="p-3 bg-[#333537] rounded border border-[#41474f] flex items-center justify-between">
                <div>
                  <span className="text-xs text-[#c1c7d0]">Target Element: </span>
                  <span className="font-mono font-bold text-[#96ccff]">
                    {selectedElementId || 'None (Please select an object)'}
                  </span>
                </div>
                <button
                  onClick={() => handleDelete(true)}
                  disabled={!selectedElementId}
                  className="flex items-center space-x-1.5 bg-[#93000a]/20 hover:bg-[#93000a]/40 text-[#ffb4ab] border border-[#ffb4ab]/30 px-3 py-1.5 rounded text-xs transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Selected Object</span>
                </button>
              </div>

              {/* Move & Copy Blocks */}
              <div className="grid grid-cols-2 gap-4">
                {/* Move */}
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <div className="flex items-center space-x-2 text-[#96ccff]">
                    <Move className="w-4 h-4" />
                    <h3 className="font-semibold text-sm">Move Translation (ΔX, ΔY, ΔZ)</h3>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔX (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={moveDelta.dx}
                        onChange={e => setMoveDelta({ ...moveDelta, dx: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔY Elev (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={moveDelta.dy}
                        onChange={e => setMoveDelta({ ...moveDelta, dy: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔZ (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={moveDelta.dz}
                        onChange={e => setMoveDelta({ ...moveDelta, dz: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleMove}
                    disabled={!selectedElementId}
                    className="w-full bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] font-medium py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Execute Move Translation
                  </button>
                </div>

                {/* Copy */}
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <div className="flex items-center space-x-2 text-[#7ed99e]">
                    <Copy className="w-4 h-4" />
                    <h3 className="font-semibold text-sm">Copy Offset (ΔX, ΔY, ΔZ)</h3>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔX (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={copyDelta.dx}
                        onChange={e => setCopyDelta({ ...copyDelta, dx: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔY Elev (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={copyDelta.dy}
                        onChange={e => setCopyDelta({ ...copyDelta, dy: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">ΔZ (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={copyDelta.dz}
                        onChange={e => setCopyDelta({ ...copyDelta, dz: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleCopy}
                    disabled={!selectedElementId}
                    className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Execute Copy Duplicate
                  </button>
                </div>
              </div>

              {/* Mirror Block */}
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#ffb77d]">
                  <FlipHorizontal className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Mirror Reflection Plane</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Mirror Plane</label>
                    <select
                      value={mirrorPlane}
                      onChange={e => setMirrorPlane(e.target.value as any)}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      <option value="YZ">YZ Plane (Mirror along X-axis)</option>
                      <option value="XZ">XZ Plane (Mirror along Y-axis / Elevation)</option>
                      <option value="XY">XY Plane (Mirror along Z-axis)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Plane Coordinate (m)</label>
                    <input
                      type="number"
                      step="1"
                      value={mirrorCoord}
                      onChange={e => setMirrorCoord(parseFloat(e.target.value) || 0)}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>
                <button
                  onClick={handleMirror}
                  disabled={!selectedElementId}
                  className="w-full bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] font-medium py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                >
                  Generate Symmetrical Mirrored Geometry
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: REPLICATE & ARRAYS */}
          {activeTab === 'replicate' && (
            <div className="space-y-4">
              {/* Story Replicate */}
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#96ccff]">
                  <Layers className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Multi-Story Replicate</h3>
                </div>
                <p className="text-xs text-[#c1c7d0]">
                  Replicates selected structural columns, beams, slabs, and walls from a source story level to target stories, maintaining elevation offsets.
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Source Story</label>
                    <select
                      value={replicateForm.sourceStory}
                      onChange={e => setReplicateForm({ ...replicateForm, sourceStory: e.target.value })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      {model.stories.map(s => <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Target Story Destination</label>
                    <select
                      value={replicateForm.targetStories[0]}
                      onChange={e => setReplicateForm({ ...replicateForm, targetStories: [e.target.value] })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      {model.stories.map(s => <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>)}
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleStoryReplicate}
                  disabled={!selectedElementId}
                  className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer disabled:opacity-50"
                >
                  Replicate Selected Elements to Target Story
                </button>
              </div>

              {/* Linear & Radial Arrays */}
              <div className="grid grid-cols-2 gap-4">
                {/* Linear Array */}
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <div className="flex items-center space-x-2 text-[#7ed99e]">
                    <Grid className="w-4 h-4" />
                    <h3 className="font-semibold text-sm">Linear Array</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">Number of Copies</label>
                      <input
                        type="number"
                        min="1"
                        max="20"
                        value={linearArrayForm.count}
                        onChange={e => setLinearArrayForm({ ...linearArrayForm, count: parseInt(e.target.value, 10) || 1 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">Pitch ΔX (m)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={linearArrayForm.dx}
                        onChange={e => setLinearArrayForm({ ...linearArrayForm, dx: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleLinearArray}
                    disabled={!selectedElementId}
                    className="w-full bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] font-medium py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Generate Linear Array
                  </button>
                </div>

                {/* Radial Array */}
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                  <div className="flex items-center space-x-2 text-[#ffb77d]">
                    <RotateCw className="w-4 h-4" />
                    <h3 className="font-semibold text-sm">Radial Array</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">Copies Count</label>
                      <input
                        type="number"
                        min="1"
                        max="16"
                        value={radialArrayForm.count}
                        onChange={e => setRadialArrayForm({ ...radialArrayForm, count: parseInt(e.target.value, 10) || 1 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#c1c7d0]">Step Angle (°)</label>
                      <input
                        type="number"
                        step="15"
                        value={radialArrayForm.angleDeg}
                        onChange={e => setRadialArrayForm({ ...radialArrayForm, angleDeg: parseFloat(e.target.value) || 90 })}
                        className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2 py-1 text-xs font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleRadialArray}
                    disabled={!selectedElementId}
                    className="w-full bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] font-medium py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Generate Radial Array
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: DIVIDE, MERGE, ALIGN */}
          {activeTab === 'mesh' && (
            <div className="space-y-4">
              {/* Divide Frame */}
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#96ccff]">
                  <Scissors className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Divide Frame Element into N Segments</h3>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="flex-1">
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Number of Segments</label>
                    <input
                      type="number"
                      min="2"
                      max="10"
                      value={divideForm.segments}
                      onChange={e => setDivideForm({ segments: parseInt(e.target.value, 10) || 2 })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <button
                    onClick={handleDivide}
                    disabled={!selectedElementId || !selectedElementId.match(/^(C|B|BR)\d+/i)}
                    className="mt-4 bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold px-4 py-2 rounded transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Divide Frame Member
                  </button>
                </div>
              </div>

              {/* Merge Duplicate Joints */}
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#7ed99e]">
                  <Merge className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Auto-Merge Duplicate / Coincident Joints</h3>
                </div>
                <p className="text-xs text-[#c1c7d0]">
                  Finds all overlapping joints within geometric tolerance (5 mm) and merges them into a single master node, reconnecting attached beams, columns, and slabs automatically.
                </p>
                <button
                  onClick={handleMergeDuplicates}
                  className="bg-[#333537] hover:bg-[#41474f] text-[#7ed99e] font-semibold px-4 py-2 rounded border border-[#7ed99e]/30 transition-colors cursor-pointer"
                >
                  Scan & Merge Coincident Joints
                </button>
              </div>

              {/* Align Joints */}
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#ffb77d]">
                  <AlignLeft className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Align Selected Joints</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Alignment Axis</label>
                    <select
                      value={alignForm.axis}
                      onChange={e => setAlignForm({ ...alignForm, axis: e.target.value as any })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      <option value="X">X Axis</option>
                      <option value="Y">Y Elevation Axis</option>
                      <option value="Z">Z Axis</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Target Reference</label>
                    <select
                      value={alignForm.targetType}
                      onChange={e => setAlignForm({ ...alignForm, targetType: e.target.value as any })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      <option value="mean">Average / Mean Coordinate</option>
                      <option value="min">Minimum Coordinate</option>
                      <option value="max">Maximum Coordinate</option>
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleAlign}
                  disabled={!selectedElementId}
                  className="w-full bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] font-medium py-1.5 rounded transition-colors cursor-pointer disabled:opacity-50"
                >
                  Align Elements
                </button>
              </div>
            </div>
          )}

          {/* TAB 5: DIAPHRAGMS */}
          {activeTab === 'diaphragm' && (
            <div className="space-y-4">
              <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-3">
                <div className="flex items-center space-x-2 text-[#96ccff]">
                  <Activity className="w-4 h-4" />
                  <h3 className="font-semibold text-sm">Floor Diaphragm Assignment & Kinematic Constraints</h3>
                </div>
                <p className="text-xs text-[#c1c7d0]">
                  Assigns floor diaphragm behavior to constrain story floor nodes, computing center of mass (CM) and center of rigidity (CR) for lateral seismic and wind analysis.
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Story Level</label>
                    <select
                      value={diaphragmForm.story}
                      onChange={e => setDiaphragmForm({ ...diaphragmForm, story: e.target.value })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      {model.stories.map(s => <option key={s.id} value={s.name}>{s.name} (+{s.elevation}m)</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] text-[#c1c7d0] mb-1">Diaphragm Behavior</label>
                    <select
                      value={diaphragmForm.type}
                      onChange={e => setDiaphragmForm({ ...diaphragmForm, type: e.target.value as any })}
                      className="w-full bg-[#1e2022] border border-[#41474f] rounded px-2.5 py-1.5 text-xs"
                    >
                      <option value="rigid">Rigid Diaphragm (3 Master DOFs: UX, UZ, R_Y)</option>
                      <option value="semi-rigid">Semi-Rigid Diaphragm (In-plane shell stiffness)</option>
                      <option value="flexible">Flexible Diaphragm (Tributary width load distribution)</option>
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleAssignDiaphragm}
                  className="w-full bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold py-2 rounded transition-colors cursor-pointer"
                >
                  Assign Diaphragm to Story
                </button>
              </div>

              {/* Active Diaphragms List */}
              {model.diaphragms && model.diaphragms.length > 0 && (
                <div className="bg-[#282a2c] p-4 rounded border border-[#41474f] space-y-2">
                  <h4 className="font-semibold text-xs text-[#e2e2e5]">Active Defined Diaphragms</h4>
                  <div className="space-y-1.5">
                    {model.diaphragms.map(d => (
                      <div key={d.id} className="flex items-center justify-between bg-[#1e2022] px-3 py-2 rounded border border-[#41474f] text-xs">
                        <div>
                          <span className="font-bold text-[#96ccff]">{d.name}</span>
                          <span className="text-[#c1c7d0] ml-2">({d.type} on {d.story})</span>
                        </div>
                        <div className="font-mono text-[11px] text-[#7ed99e]">
                          CM: ({d.centerOfMass.x}, {d.centerOfMass.y}, {d.centerOfMass.z}) | {d.nodeIds.length} Nodes
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: MODEL INTEGRITY VALIDATION */}
          {activeTab === 'validate' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-[#282a2c] rounded border border-[#41474f]">
                <div>
                  <h3 className="font-semibold text-sm text-[#e2e2e5]">Model Integrity Verification</h3>
                  <p className="text-xs text-[#c1c7d0]">
                    Scans geometry for duplicate joints, duplicate members, zero-length elements, disconnected joints, and missing materials/sections.
                  </p>
                </div>
                <button
                  onClick={handleRunValidation}
                  className="flex items-center space-x-1.5 bg-[#004a77] hover:bg-[#005a92] text-[#c2e7ff] font-semibold px-4 py-2 rounded transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Run Validation Scan</span>
                </button>
              </div>

              {/* Report Summary */}
              {validationReport && (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div className={`p-3 rounded border ${validationReport.isValid ? 'bg-[#47a26b]/15 border-[#7ed99e]/40' : 'bg-[#93000a]/15 border-[#ffb4ab]/40'}`}>
                      <div className="text-[11px] text-[#c1c7d0]">Integrity Status</div>
                      <div className={`text-base font-bold ${validationReport.isValid ? 'text-[#7ed99e]' : 'text-[#ffb4ab]'}`}>
                        {validationReport.isValid ? 'PASSED (Clean)' : 'FAILED (Errors Detected)'}
                      </div>
                    </div>
                    <div className="p-3 bg-[#333537] rounded border border-[#41474f]">
                      <div className="text-[11px] text-[#c1c7d0]">Total Errors</div>
                      <div className="text-base font-bold text-[#ffb4ab]">{validationReport.totalErrors}</div>
                    </div>
                    <div className="p-3 bg-[#333537] rounded border border-[#41474f]">
                      <div className="text-[11px] text-[#c1c7d0]">Total Warnings</div>
                      <div className="text-base font-bold text-[#ffb77d]">{validationReport.totalWarnings}</div>
                    </div>
                  </div>

                  {/* Issues List */}
                  <div className="bg-[#282a2c] rounded border border-[#41474f] overflow-hidden">
                    <div className="bg-[#1e2022] px-3 py-2 text-xs font-semibold border-b border-[#41474f]">
                      Diagnostics & Topology Checks ({validationReport.issues.length})
                    </div>
                    <div className="max-h-60 overflow-y-auto divide-y divide-[#41474f]">
                      {validationReport.issues.length === 0 ? (
                        <div className="p-4 text-center text-xs text-[#7ed99e] flex items-center justify-center space-x-2">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>No structural defects detected. Model topology is pristine!</span>
                        </div>
                      ) : (
                        validationReport.issues.map((iss, idx) => (
                          <div key={idx} className="p-3 text-xs space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${
                                iss.severity === 'ERROR' || iss.severity === 'CRITICAL'
                                  ? 'bg-[#93000a] text-[#ffdad6]'
                                  : 'bg-[#783f00] text-[#ffdcbe]'
                              }`}>
                                {iss.code} [{iss.severity}]
                              </span>
                              <span className="font-semibold text-[#e2e2e5]">{iss.title}</span>
                            </div>
                            <div className="text-[#c1c7d0]">{iss.message}</div>
                            {iss.remedySuggestion && (
                              <div className="text-[#7ed99e] text-[11px]">
                                💡 Remedy: {iss.remedySuggestion}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-[#282a2c] px-4 py-2.5 border-t border-[#41474f] flex items-center justify-between text-xs text-[#c1c7d0]">
          <div className="flex items-center space-x-4 rtl:space-x-reverse font-mono text-[11px]">
            <span>Joints: {model.nodes.length}</span>
            <span>Frames: {model.members.length}</span>
            <span>Slabs: {model.slabs.length}</span>
            <span>Walls: {model.walls?.length || 0}</span>
            <span>Stories: {model.stories.length}</span>
          </div>
          <button
            onClick={onClose}
            className="bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] px-4 py-1.5 rounded transition-colors cursor-pointer"
          >
            {lang === 'ar' ? 'إغلاق' : 'Close Palette'}
          </button>
        </div>
      </div>
    </div>
  );
};
