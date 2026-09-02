import React, { useState } from 'react';
import { X, Ruler, Plus, Check, Trash2, Edit } from 'lucide-react';
import { SectionProperty, CrossSectionShape, Material } from '../types/structure';

interface SectionEditorModalProps {
  sections: SectionProperty[];
  materials: Material[];
  onSaveSection: (section: SectionProperty) => void;
  onClose: () => void;
  lang: 'en' | 'ar';
}

export const SectionEditorModal: React.FC<SectionEditorModalProps> = ({
  sections,
  materials,
  onSaveSection,
  onClose,
  lang
}) => {
  const [selectedSecId, setSelectedSecId] = useState<string>(sections[0]?.id || '');
  const currentSection = sections.find(s => s.id === selectedSecId) || sections[0];

  const [name, setName] = useState(currentSection?.name || '');
  const [shape, setShape] = useState<CrossSectionShape>(currentSection?.shape || 'rectangular');
  const [width, setWidth] = useState(currentSection?.dimensions.width || 400);
  const [height, setHeight] = useState(currentSection?.dimensions.height || 400);
  const [flangeThk, setFlangeThk] = useState(currentSection?.dimensions.flangeThickness || 15);
  const [webThk, setWebThk] = useState(currentSection?.dimensions.webThickness || 10);
  const [materialId, setMaterialId] = useState(currentSection?.materialId || materials[0]?.id);

  // Sync state when selected section changes
  const handleSelectSection = (sec: SectionProperty) => {
    setSelectedSecId(sec.id);
    setName(sec.name);
    setShape(sec.shape);
    setWidth(sec.dimensions.width);
    setHeight(sec.dimensions.height);
    setFlangeThk(sec.dimensions.flangeThickness || 15);
    setWebThk(sec.dimensions.webThickness || 10);
    setMaterialId(sec.materialId);
  };

  // Recalculate geometric properties
  let area = 0; // cm2
  let Ixx = 0; // cm4
  let Iyy = 0; // cm4
  let weightPerMeter = 0; // kg/m
  const selectedMat = materials.find(m => m.id === materialId) || materials[0];
  const rho = selectedMat.type === 'concrete' ? 2500 : 7850; // kg/m3

  if (shape === 'rectangular') {
    area = (width * height) / 100; // mm2 to cm2
    Ixx = (width * Math.pow(height, 3)) / 12 / 10000; // mm4 to cm4
    Iyy = (height * Math.pow(width, 3)) / 12 / 10000;
    weightPerMeter = (area / 10000) * rho;
  } else if (shape === 'i_beam') {
    const tf = flangeThk;
    const tw = webThk;
    const hw = height - 2 * tf;
    area = (2 * width * tf + hw * tw) / 100;
    Ixx = ((width * Math.pow(height, 3)) - ((width - tw) * Math.pow(hw, 3))) / 12 / 10000;
    Iyy = (2 * (tf * Math.pow(width, 3)) / 12 + (hw * Math.pow(tw, 3)) / 12) / 10000;
    weightPerMeter = (area / 10000) * rho;
  } else if (shape === 'circular') {
    const r = width / 2;
    area = (Math.PI * r * r) / 100;
    Ixx = (Math.PI * Math.pow(width, 4)) / 64 / 10000;
    Iyy = Ixx;
    weightPerMeter = (area / 10000) * rho;
  }

  const handleSave = () => {
    const updated: SectionProperty = {
      id: selectedSecId,
      name,
      shape,
      materialId,
      dimensions: {
        width,
        height,
        flangeThickness: shape === 'i_beam' ? flangeThk : undefined,
        webThickness: shape === 'i_beam' ? webThk : undefined
      },
      area: Math.round(area * 10) / 10,
      momentOfInertiaIxx: Math.round(Ixx),
      momentOfInertiaIyy: Math.round(Iyy),
      torsionalConstantJ: Math.round(Ixx * 1.5),
      weightPerMeter: Math.round(weightPerMeter * 10) / 10
    };
    onSaveSection(updated);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in-50">
      <div className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-3xl flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="h-10 bg-[#282a2c] border-b border-[#41474f] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Ruler className="w-4 h-4 text-[#96ccff]" />
            <span className="font-semibold text-[13px] text-[#e2e2e5]">
              {lang === 'ar' ? 'محرر مقاطع الإطارات والجوائز' : 'Frame Section Property Definition'}
            </span>
          </div>
          <button onClick={onClose} className="text-[#c1c7d0] hover:text-[#e2e2e5]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-col md:flex-row h-[420px]">
          {/* Section List Left */}
          <div className="w-full md:w-56 bg-[#1a1c1e] border-r border-[#41474f] p-3 overflow-y-auto space-y-1">
            <div className="text-[10px] font-bold text-[#8b919a] uppercase tracking-wider mb-2">
              {lang === 'ar' ? 'المقاطع المعرفة' : 'Defined Sections'}
            </div>
            {sections.map(s => (
              <button
                key={s.id}
                onClick={() => handleSelectSection(s)}
                className={`w-full px-2.5 py-1.5 rounded text-left rtl:text-right text-[11px] font-mono flex items-center justify-between transition-colors ${
                  s.id === selectedSecId
                    ? 'bg-[#96ccff]/20 text-[#96ccff] font-bold border border-[#96ccff]/40'
                    : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                }`}
              >
                <span className="truncate">{s.name}</span>
                <span className="text-[9px] opacity-70">{s.shape}</span>
              </button>
            ))}
          </div>

          {/* Section Form & 2D CAD Preview */}
          <div className="flex-1 p-4 overflow-y-auto flex flex-col md:flex-row gap-4 bg-[#1e2022]">
            {/* Form Inputs */}
            <div className="flex-1 space-y-3 text-[11px]">
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Section Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono focus:border-[#96ccff] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#c1c7d0] mb-1 font-mono">Shape Type</label>
                  <select
                    value={shape}
                    onChange={(e) => setShape(e.target.value as CrossSectionShape)}
                    className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono focus:border-[#96ccff] focus:outline-none"
                  >
                    <option value="rectangular">Rectangular RC</option>
                    <option value="i_beam">I / H Steel Beam</option>
                    <option value="circular">Circular Column</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[#c1c7d0] mb-1 font-mono">Material</label>
                  <select
                    value={materialId}
                    onChange={(e) => setMaterialId(e.target.value)}
                    className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#7ed99e] font-mono focus:border-[#96ccff] focus:outline-none"
                  >
                    {materials.map(m => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[#c1c7d0] mb-1 font-mono">Width / Flange b (mm)</label>
                  <input
                    type="number"
                    value={width}
                    onChange={(e) => setWidth(Math.max(50, parseFloat(e.target.value) || 0))}
                    className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono focus:border-[#96ccff] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[#c1c7d0] mb-1 font-mono">Height / Depth h (mm)</label>
                  <input
                    type="number"
                    value={height}
                    onChange={(e) => setHeight(Math.max(50, parseFloat(e.target.value) || 0))}
                    className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono focus:border-[#96ccff] focus:outline-none"
                  />
                </div>
              </div>

              {shape === 'i_beam' && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[#c1c7d0] mb-1 font-mono">Flange Thk tf (mm)</label>
                    <input
                      type="number"
                      value={flangeThk}
                      onChange={(e) => setFlangeThk(parseFloat(e.target.value) || 0)}
                      className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[#c1c7d0] mb-1 font-mono">Web Thk tw (mm)</label>
                    <input
                      type="number"
                      value={webThk}
                      onChange={(e) => setWebThk(parseFloat(e.target.value) || 0)}
                      className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono"
                    />
                  </div>
                </div>
              )}

              {/* Calculated Section Properties */}
              <div className="bg-[#121416] p-2.5 rounded border border-[#41474f] space-y-1 font-mono text-[10px]">
                <div className="flex justify-between text-[#c1c7d0]">
                  <span>Gross Area (Ag):</span>
                  <span className="text-[#e2e2e5] font-bold">{area.toFixed(1)} cm²</span>
                </div>
                <div className="flex justify-between text-[#c1c7d0]">
                  <span>Moment of Inertia (Ixx):</span>
                  <span className="text-[#7ed99e] font-bold">{Ixx.toFixed(0)} cm⁴</span>
                </div>
                <div className="flex justify-between text-[#c1c7d0]">
                  <span>Moment of Inertia (Iyy):</span>
                  <span className="text-[#7ed99e] font-bold">{Iyy.toFixed(0)} cm⁴</span>
                </div>
                <div className="flex justify-between text-[#c1c7d0]">
                  <span>Self-Weight:</span>
                  <span className="text-[#ffb77d] font-bold">{weightPerMeter.toFixed(1)} kg/m</span>
                </div>
              </div>
            </div>

            {/* 2D Cross Section Diagram */}
            <div className="w-48 bg-[#121416] border border-[#41474f] rounded p-3 flex flex-col items-center justify-center relative">
              <span className="absolute top-2 left-2 text-[9px] font-mono text-[#8b919a]">2D Section View</span>
              <div className="w-32 h-32 flex items-center justify-center relative">
                {shape === 'rectangular' && (
                  <div 
                    className="bg-[#7ed99e]/30 border-2 border-[#7ed99e] rounded-xs flex items-center justify-center font-mono text-[9px] text-[#7ed99e]"
                    style={{
                      width: `${Math.min(120, Math.max(40, (width / 500) * 100))}px`,
                      height: `${Math.min(120, Math.max(40, (height / 500) * 100))}px`
                    }}
                  >
                    {width}x{height}
                  </div>
                )}
                {shape === 'circular' && (
                  <div 
                    className="bg-[#7ed99e]/30 border-2 border-[#7ed99e] rounded-full flex items-center justify-center font-mono text-[9px] text-[#7ed99e]"
                    style={{
                      width: `${Math.min(120, Math.max(40, (width / 500) * 100))}px`,
                      height: `${Math.min(120, Math.max(40, (width / 500) * 100))}px`
                    }}
                  >
                    Ø{width}
                  </div>
                )}
                {shape === 'i_beam' && (
                  <div className="flex flex-col items-center">
                    <div className="w-24 h-3 bg-[#96ccff] border border-[#96ccff]" />
                    <div className="w-3 h-16 bg-[#96ccff] border-x border-[#96ccff]" />
                    <div className="w-24 h-3 bg-[#96ccff] border border-[#96ccff]" />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="h-12 bg-[#282a2c] border-t border-[#41474f] px-4 flex items-center justify-between">
          <span className="text-[11px] text-[#8b919a] font-mono">
            Auto-calculated according to EN 1992-1 / AISC Steel Manual
          </span>
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <button
              onClick={onClose}
              className="px-3 py-1 bg-[#333537] hover:bg-[#41474f] text-[#c1c7d0] text-[12px] rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 bg-[#96ccff] hover:bg-[#cee5ff] text-[#003353] font-bold text-[12px] rounded transition-colors cursor-pointer flex items-center space-x-1"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Apply & Save</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
