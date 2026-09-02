import React from 'react';
import {
  MousePointer2,
  CircleDot,
  Minus,
  Columns3,
  Square,
  Building2,
  Anchor,
  Ruler,
  Magnet,
  RotateCw,
  Maximize2,
  ArrowDownCircle,
  Eye,
  Sliders,
  Activity,
  Split,
  Box
} from 'lucide-react';
import { ActiveCadTool } from '../types/structure';

interface CadToolbarProps {
  activeTool: ActiveCadTool;
  setActiveTool: (tool: ActiveCadTool) => void;
  isSnapping: boolean;
  setIsSnapping: (snap: boolean) => void;
  onResetCamera: () => void;
  onOpenModelingModal?: () => void;
  onSetCameraPreset?: (preset: 'iso' | 'plan' | 'elevation-xz' | 'elevation-yz') => void;
  lang: 'en' | 'ar';
}

export const CadToolbar: React.FC<CadToolbarProps> = ({
  activeTool,
  setActiveTool,
  isSnapping,
  setIsSnapping,
  onResetCamera,
  onOpenModelingModal,
  onSetCameraPreset,
  lang
}) => {
  return (
    <div className="absolute left-2.5 top-3 z-30 flex flex-col items-center bg-[#1a1c1e]/95 backdrop-blur-md border border-[#41474f] rounded-lg p-1.5 space-y-1 shadow-2xl">
      {/* 1. Select Tool */}
      <button
        id="tool-select"
        onClick={() => setActiveTool('select')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'select'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'أداة التحديد (Select)' : 'Select Object (S)'}
      >
        <MousePointer2 className="w-4 h-4" />
      </button>

      <div className="w-5 border-b border-[#41474f] my-0.5" />

      {/* 2. Draw Joint */}
      <button
        id="tool-joint"
        onClick={() => setActiveTool('joint')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'joint'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم عقدة (Draw Joint Point)' : 'Draw Joint Point (J)'}
      >
        <CircleDot className="w-4 h-4" />
      </button>

      {/* 3. Draw Beam */}
      <button
        id="tool-beam"
        onClick={() => setActiveTool('beam')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'beam'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم كمرة (Draw Beam)' : 'Draw Beam / Frame Member (B)'}
      >
        <Minus className="w-4 h-4" />
      </button>

      {/* 4. Draw Column */}
      <button
        id="tool-column"
        onClick={() => setActiveTool('column')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'column'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold ring-1 ring-[#96ccff]'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم عمود رأسي (Draw Column)' : 'Draw Column (C)'}
      >
        <Columns3 className="w-4 h-4" />
      </button>

      {/* 5. Draw Brace */}
      <button
        id="tool-brace"
        onClick={() => setActiveTool('brace')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'brace'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم عنصر تدعيم مائل (Draw Diagonal Brace)' : 'Draw Diagonal Brace (BR)'}
      >
        <Split className="w-4 h-4 rotate-45" />
      </button>

      {/* 6. Draw Slab */}
      <button
        id="tool-slab"
        onClick={() => setActiveTool('slab')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'slab'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم بلاطة (Draw Slab Area)' : 'Draw Slab Area Shell (A)'}
      >
        <Square className="w-4 h-4" />
      </button>

      {/* 7. Draw Shear Wall */}
      <button
        id="tool-wall"
        onClick={() => setActiveTool('wall')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'wall'
            ? 'bg-[#96ccff] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'رسم جدار قص خرساني (Draw Shear Wall)' : 'Draw Shear Wall (W)'}
      >
        <Building2 className="w-4 h-4" />
      </button>

      {/* 8. Assign Restraints / Supports */}
      <button
        id="tool-support"
        onClick={() => setActiveTool('support')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'support'
            ? 'bg-[#7ed99e] text-[#003353] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'تعيين الركائز والقيود (Boundary Supports)' : 'Assign Joint Supports (R)'}
      >
        <Anchor className="w-4 h-4" />
      </button>

      {/* 9. Apply Loads */}
      <button
        id="tool-load"
        onClick={() => setActiveTool('load')}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          activeTool === 'load'
            ? 'bg-[#ffb77d] text-[#4d2600] shadow-md font-bold'
            : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
        }`}
        title={lang === 'ar' ? 'تطبيق أحمال (Apply Loads)' : 'Apply Structural Loads (L)'}
      >
        <ArrowDownCircle className="w-4 h-4" />
      </button>

      <div className="w-5 border-b border-[#41474f] my-0.5" />

      {/* 10. Modeling Operations Palette */}
      {onOpenModelingModal && (
        <button
          id="tool-modeling-palette"
          onClick={onOpenModelingModal}
          className="w-8 h-8 flex items-center justify-center rounded bg-[#96ccff]/15 text-[#96ccff] hover:bg-[#96ccff]/30 transition-all cursor-pointer"
          title={lang === 'ar' ? 'لوحة النمذجة وعمليات التعديل (Modeling Tools Palette)' : 'Structural Modeling & Transform Palette (P)'}
        >
          <Sliders className="w-4 h-4" />
        </button>
      )}

      {/* 11. Snapping Toggle */}
      <button
        id="tool-snap"
        onClick={() => setIsSnapping(!isSnapping)}
        className={`w-8 h-8 flex items-center justify-center rounded transition-all cursor-pointer ${
          isSnapping
            ? 'bg-[#47a26b]/30 text-[#7ed99e] border border-[#7ed99e]/50'
            : 'text-[#8b919a] hover:bg-[#333537]'
        }`}
        title={isSnapping ? (lang === 'ar' ? 'المغناطيس والالتقاط مفعل' : 'CAD Snapping Active (ON)') : (lang === 'ar' ? 'الالتقاط معطل' : 'CAD Snapping OFF')}
      >
        <Magnet className="w-4 h-4" />
      </button>

      {/* 12. Reset Camera */}
      <button
        onClick={onResetCamera}
        className="w-8 h-8 flex items-center justify-center rounded text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5] transition-colors cursor-pointer"
        title={lang === 'ar' ? 'إعادة ضبط الكاميرا (Reset 3D View)' : 'Reset Isometric Camera (Home)'}
      >
        <RotateCw className="w-4 h-4" />
      </button>
    </div>
  );
};

