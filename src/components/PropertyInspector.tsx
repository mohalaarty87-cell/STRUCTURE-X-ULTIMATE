import React from 'react';
import { 
  Columns, 
  Minus, 
  Square, 
  MoreVertical, 
  Edit3, 
  BarChart2, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle,
  Copy,
  Trash2
} from 'lucide-react';
import { StructuralModel, StructuralMember, SlabElement } from '../types/structure';

interface PropertyInspectorProps {
  model: StructuralModel;
  selectedElementId: string | null;
  onOpenForcesModal: () => void;
  onOpenSectionEditor: () => void;
  onUpdateMember?: (updated: StructuralMember) => void;
  onDeleteMember?: (memberId: string) => void;
  lang: 'en' | 'ar';
}

export const PropertyInspector: React.FC<PropertyInspectorProps> = ({
  model,
  selectedElementId,
  onOpenForcesModal,
  onOpenSectionEditor,
  onUpdateMember,
  onDeleteMember,
  lang
}) => {
  // Find selected member or slab or default to C1
  const activeMember = model.members.find(m => m.id === selectedElementId) 
    || model.members.find(m => m.id === 'C1') 
    || model.members[0];

  const activeSlab = model.slabs.find(s => s.id === selectedElementId);
  const activeWall = model.walls?.find(w => w.id === selectedElementId);
  const isSlab = Boolean(activeSlab && selectedElementId?.startsWith('S'));
  const isWall = Boolean(activeWall && selectedElementId?.startsWith('W'));

  const section = model.sections.find(s => s.id === (activeMember?.sectionId || 'sec-400rc')) || model.sections[0];
  const material = model.materials.find(m => m.id === (activeWall?.materialId || activeSlab?.materialId || activeMember?.materialId || 'mat-c3037')) || model.materials[0];

  return (
    <aside className="w-[280px] h-full bg-[#1e2022] border-l border-[#41474f] flex flex-col flex-shrink-0 z-40 select-none text-[12px]">
      {/* Top Toolbar Header */}
      <div className="h-[32px] bg-[#282a2c] border-b border-[#41474f] flex items-center px-3 justify-between">
        <span className="text-[13px] font-semibold text-[#e2e2e5]">
          {lang === 'ar' ? 'فاحص الخصائص' : 'Property Inspector'}
        </span>
        <button className="text-[#c1c7d0] hover:text-[#e2e2e5] cursor-pointer">
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Selection Banner (Matches Screenshot) */}
        <div className="bg-[#96ccff]/10 border border-[#96ccff]/30 rounded p-2.5 flex items-start space-x-3 rtl:space-x-reverse">
          {isWall ? (
            <Square className="w-5 h-5 text-[#96ccff] mt-0.5 shrink-0" />
          ) : isSlab ? (
            <Square className="w-5 h-5 text-[#96ccff] mt-0.5 shrink-0" />
          ) : activeMember.type === 'column' ? (
            <Columns className="w-5 h-5 text-[#96ccff] mt-0.5 shrink-0" />
          ) : (
            <Minus className="w-5 h-5 text-[#96ccff] mt-0.5 shrink-0" />
          )}

          <div className="min-w-0">
            <div className="text-[13px] font-semibold text-[#96ccff] tracking-tight">
              {isWall
                ? (lang === 'ar' ? 'تم تحديد جدار القص' : 'Shear Wall Selected')
                : isSlab
                ? (lang === 'ar' ? 'تم تحديد البلاطة' : 'Slab Selected')
                : activeMember.type === 'column'
                ? (lang === 'ar' ? 'تم تحديد العمود' : 'Column Selected')
                : (lang === 'ar' ? 'تم تحديد الكمرة' : 'Beam Selected')}
            </div>
            <div className="font-mono text-[10px] text-[#c1c7d0] mt-0.5">
              1 Object Selected ({isWall ? activeWall?.id : isSlab ? activeSlab?.id : activeMember?.id})
            </div>
          </div>
        </div>

        {/* 1. Bento Block: General */}
        <div className="bg-[#333537] rounded border border-[#41474f] overflow-hidden">
          <div className="bg-[#282a2c] px-2.5 py-1 text-[10px] font-bold text-[#e2e2e5] border-b border-[#41474f] uppercase tracking-wider">
            {lang === 'ar' ? 'عام' : 'GENERAL'}
          </div>
          <div className="p-2 space-y-2 text-[11px]">
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">ID</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#e2e2e5] font-semibold">
                {isWall ? activeWall?.id : isSlab ? activeSlab?.id : activeMember?.id}
              </div>
            </div>
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Type</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#e2e2e5]">
                {isWall ? 'Shear Wall (Wall)' : isSlab ? 'Slab (Shell)' : activeMember?.type === 'column' ? 'Column (Frame)' : 'Beam (Frame)'}
              </div>
            </div>
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Story</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#c1c7d0]">
                {isWall ? activeWall?.story : isSlab ? activeSlab?.story : activeMember?.story}
              </div>
            </div>
          </div>
        </div>

        {/* 2. Bento Block: Geometry & Section */}
        <div className="bg-[#333537] rounded border border-[#41474f] overflow-hidden">
          <div className="bg-[#282a2c] px-2.5 py-1 text-[10px] font-bold text-[#e2e2e5] border-b border-[#41474f] uppercase tracking-wider flex items-center justify-between">
            <span>{lang === 'ar' ? 'الهندسة والمقطع' : 'GEOMETRY & SECTION'}</span>
            <button 
              onClick={onOpenSectionEditor}
              className="text-[#96ccff] hover:underline text-[9px] lowercase font-normal"
            >
              edit
            </button>
          </div>
          <div className="p-2 space-y-2 text-[11px]">
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Section</label>
              <div className="col-span-8 flex items-center">
                <div className="flex-1 bg-[#121416] border border-[#41474f] border-r-0 rtl:border-r rtl:border-l-0 rounded-l rtl:rounded-l-none rtl:rounded-r px-2 py-1 font-mono text-[#e2e2e5] truncate">
                  {section.name}
                </div>
                <button 
                  onClick={onOpenSectionEditor}
                  className="bg-[#282a2c] border border-[#41474f] rounded-r rtl:rounded-r-none rtl:rounded-l px-1.5 py-1 hover:bg-[#333537] cursor-pointer text-[#c1c7d0]"
                  title="Modify Section Dimensions"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Material</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#7ed99e] font-semibold">
                {material.name}
              </div>
            </div>

            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Length</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#e2e2e5] text-right rtl:text-left">
                {activeMember?.length?.toFixed(3)} m
              </div>
            </div>
          </div>
        </div>

        {/* 3. Bento Block: Assignments */}
        <div className="bg-[#333537] rounded border border-[#41474f] overflow-hidden">
          <div className="bg-[#282a2c] px-2.5 py-1 text-[10px] font-bold text-[#e2e2e5] border-b border-[#41474f] uppercase tracking-wider">
            {lang === 'ar' ? 'التخصيصات والتحرير' : 'ASSIGNMENTS'}
          </div>
          <div className="p-2 space-y-2 text-[11px]">
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Releases</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#c1c7d0] italic">
                {activeMember?.releases || 'Continuous'}
              </div>
            </div>
            <div className="grid grid-cols-12 gap-2 items-center">
              <label className="col-span-4 text-[#c1c7d0]">Local Axis</label>
              <div className="col-span-8 bg-[#121416] border border-[#41474f] rounded px-2 py-1 font-mono text-[#e2e2e5] text-right rtl:text-left">
                {(activeMember?.localAxisAngle || 0).toFixed(1)} deg
              </div>
            </div>
          </div>
        </div>

        {/* 4. Bento Block: Forces & Capacity */}
        {activeMember?.forces && (
          <div className="bg-[#333537] rounded border border-[#41474f] overflow-hidden">
            <div className="bg-[#282a2c] px-2.5 py-1 text-[10px] font-bold text-[#e2e2e5] border-b border-[#41474f] uppercase tracking-wider flex items-center justify-between">
              <span>{lang === 'ar' ? 'القوى والتحقق الإنشائي' : 'FORCES & CAPACITY'}</span>
              <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                activeMember.forces.designStatus === 'PASS' 
                  ? 'bg-[#7ed99e]/20 text-[#7ed99e]' 
                  : 'bg-[#ffb4ab]/20 text-[#ffb4ab]'
              }`}>
                {activeMember.forces.designStatus}
              </span>
            </div>
            <div className="p-2 space-y-1.5 text-[11px]">
              <div className="flex justify-between items-center py-0.5 border-b border-[#41474f]/40 font-mono">
                <span className="text-[#c1c7d0]">Axial P (kN)</span>
                <span className="text-[#e2e2e5] font-bold">{activeMember.forces.axialP.toFixed(1)}</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-[#41474f]/40 font-mono">
                <span className="text-[#c1c7d0]">Moment M3 (kN.m)</span>
                <span className="text-[#ffb77d] font-bold">{activeMember.forces.momentM3.toFixed(1)}</span>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-[#41474f]/40 font-mono">
                <span className="text-[#c1c7d0]">Shear V2 (kN)</span>
                <span className="text-[#7ed99e] font-bold">{activeMember.forces.shearV2.toFixed(1)}</span>
              </div>
              <div className="flex justify-between items-center py-0.5 font-mono">
                <span className="text-[#c1c7d0]">Utilization Ratio</span>
                <span className={`font-bold ${
                  activeMember.forces.utilizationRatio > 0.9 ? 'text-[#ffb4ab]' : 'text-[#7ed99e]'
                }`}>
                  {(activeMember.forces.utilizationRatio * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Primary Action: View Element Forces Button (Matches Screenshot) */}
        <button
          id="btn-view-element-forces"
          onClick={onOpenForcesModal}
          className="w-full bg-[#96ccff]/10 hover:bg-[#96ccff]/20 text-[#96ccff] border border-[#96ccff]/30 rounded py-2 text-[13px] font-semibold transition-all flex items-center justify-center space-x-2 rtl:space-x-reverse cursor-pointer shadow-sm active:scale-[0.98]"
        >
          <BarChart2 className="w-4 h-4" />
          <span>{lang === 'ar' ? 'عرض مخططات قوى العنصر' : 'View Element Forces'}</span>
        </button>
      </div>
    </aside>
  );
};
