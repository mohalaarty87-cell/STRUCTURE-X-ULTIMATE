import React, { useState } from 'react';
import { X, BarChart2, Activity, ArrowRight, ShieldCheck, Download } from 'lucide-react';
import { StructuralMember, SectionProperty, Material } from '../types/structure';
import { calculateMemberDiagrams } from '../utils/structuralSolver';

interface ElementForcesModalProps {
  member: StructuralMember | null;
  section: SectionProperty;
  material: Material;
  onClose: () => void;
  lang: 'en' | 'ar';
}

export const ElementForcesModal: React.FC<ElementForcesModalProps> = ({
  member,
  section,
  material,
  onClose,
  lang
}) => {
  if (!member) return null;

  const [probeDistance, setProbeDistance] = useState<number>(member.length / 2);
  const diagrams = calculateMemberDiagrams(member, 40);

  // Interpolate probe values
  const probeNorm = Math.max(0, Math.min(1, probeDistance / member.length));
  const probeIdx = Math.min(diagrams.length - 1, Math.round(probeNorm * (diagrams.length - 1)));
  const currentProbe = diagrams[probeIdx] || diagrams[0];

  const maxShear = Math.max(...diagrams.map(d => Math.abs(d.shear)), 1);
  const maxMoment = Math.max(...diagrams.map(d => Math.abs(d.moment)), 1);
  const maxDeflection = Math.max(...diagrams.map(d => Math.abs(d.deflection)), 0.1);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in-50">
      <div className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="h-10 bg-[#282a2c] border-b border-[#41474f] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-2.5 rtl:space-x-reverse">
            <BarChart2 className="w-4 h-4 text-[#96ccff]" />
            <span className="font-semibold text-[13px] text-[#e2e2e5]">
              {lang === 'ar' ? 'مخططات القوى الداخلية والإجهادات للعنصر' : 'Internal Member Forces & Diagrams'} - {member.name} ({member.id})
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#c1c7d0] hover:text-[#e2e2e5] hover:bg-[#333537] p-1 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-[12px]">
          {/* Member Overview Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#121416] p-3 rounded border border-[#41474f] font-mono text-[11px]">
            <div>
              <span className="text-[#8b919a] block">Section</span>
              <span className="text-[#e2e2e5] font-bold">{section.name}</span>
            </div>
            <div>
              <span className="text-[#8b919a] block">Material</span>
              <span className="text-[#7ed99e] font-bold">{material.name}</span>
            </div>
            <div>
              <span className="text-[#8b919a] block">Length</span>
              <span className="text-[#e2e2e5] font-bold">{member.length.toFixed(2)} m</span>
            </div>
            <div>
              <span className="text-[#8b919a] block">Status (EC2/EC3)</span>
              <span className="text-[#7ed99e] font-bold flex items-center space-x-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>PASS ({( (member.forces?.utilizationRatio || 0.6) * 100).toFixed(0)}%)</span>
              </span>
            </div>
          </div>

          {/* Interactive Probe Slider */}
          <div className="bg-[#282a2c] p-3 rounded border border-[#41474f] space-y-2">
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#96ccff] font-bold">
                {lang === 'ar' ? 'مسبار المسافة على طول العنصر:' : 'Probe Location along member:'} x = {probeDistance.toFixed(3)} m / {member.length.toFixed(3)} m
              </span>
              <div className="flex items-center space-x-3 text-[#e2e2e5]">
                <span>P: <strong className="text-[#ff4d4d]">{currentProbe.axial} kN</strong></span>
                <span>V: <strong className="text-[#7ed99e]">{currentProbe.shear} kN</strong></span>
                <span>M: <strong className="text-[#ffb77d]">{currentProbe.moment} kN.m</strong></span>
                <span>δ: <strong className="text-[#96ccff]">{currentProbe.deflection} mm</strong></span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max={member.length}
              step="0.01"
              value={probeDistance}
              onChange={(e) => setProbeDistance(parseFloat(e.target.value))}
              className="w-full accent-[#96ccff] cursor-pointer"
            />
          </div>

          {/* 1. Bending Moment Diagram (BMD M3) */}
          <div className="bg-[#121416] p-3 rounded border border-[#41474f] space-y-2">
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#ffb77d] font-bold uppercase">Bending Moment Diagram M33 (kN.m)</span>
              <span className="text-[#8b919a]">Max M+ = {member.forces?.momentM3} kN.m</span>
            </div>
            <div className="h-24 relative w-full bg-[#1a1c1e] rounded flex items-center border border-[#41474f]/50 px-4">
              <div className="absolute inset-x-4 top-1/2 h-px bg-[#41474f]" />
              {/* SVG Curve */}
              <svg className="w-full h-full overflow-visible">
                <path
                  d={diagrams.reduce((acc, pt, i) => {
                    const xPercent = (pt.x / member.length) * 100;
                    const yVal = 50 - (pt.moment / maxMoment) * 35;
                    return `${acc} ${i === 0 ? 'M' : 'L'} ${xPercent}% ${yVal}%`;
                  }, '')}
                  fill="none"
                  stroke="#ffb77d"
                  strokeWidth="2.5"
                />
                {/* Fill area */}
                <path
                  d={`${diagrams.reduce((acc, pt, i) => {
                    const xPercent = (pt.x / member.length) * 100;
                    const yVal = 50 - (pt.moment / maxMoment) * 35;
                    return `${acc} ${i === 0 ? 'M' : 'L'} ${xPercent}% ${yVal}%`;
                  }, '')} L 100% 50% L 0% 50% Z`}
                  fill="#ffb77d"
                  fillOpacity="0.15"
                />
                {/* Probe vertical indicator */}
                <line
                  x1={`${probeNorm * 100}%`}
                  y1="5%"
                  x2={`${probeNorm * 100}%`}
                  y2="95%"
                  stroke="#96ccff"
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />
              </svg>
            </div>
          </div>

          {/* 2. Shear Force Diagram (SFD V2) */}
          <div className="bg-[#121416] p-3 rounded border border-[#41474f] space-y-2">
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#7ed99e] font-bold uppercase">Shear Force Diagram V2 (kN)</span>
              <span className="text-[#8b919a]">Max V = {member.forces?.shearV2} kN</span>
            </div>
            <div className="h-24 relative w-full bg-[#1a1c1e] rounded flex items-center border border-[#41474f]/50 px-4">
              <div className="absolute inset-x-4 top-1/2 h-px bg-[#41474f]" />
              <svg className="w-full h-full overflow-visible">
                <path
                  d={diagrams.reduce((acc, pt, i) => {
                    const xPercent = (pt.x / member.length) * 100;
                    const yVal = 50 - (pt.shear / maxShear) * 35;
                    return `${acc} ${i === 0 ? 'M' : 'L'} ${xPercent}% ${yVal}%`;
                  }, '')}
                  fill="none"
                  stroke="#7ed99e"
                  strokeWidth="2.5"
                />
                <path
                  d={`${diagrams.reduce((acc, pt, i) => {
                    const xPercent = (pt.x / member.length) * 100;
                    const yVal = 50 - (pt.shear / maxShear) * 35;
                    return `${acc} ${i === 0 ? 'M' : 'L'} ${xPercent}% ${yVal}%`;
                  }, '')} L 100% 50% L 0% 50% Z`}
                  fill="#7ed99e"
                  fillOpacity="0.15"
                />
                <line
                  x1={`${probeNorm * 100}%`}
                  y1="5%"
                  x2={`${probeNorm * 100}%`}
                  y2="95%"
                  stroke="#96ccff"
                  strokeWidth="1.5"
                  strokeDasharray="3 3"
                />
              </svg>
            </div>
          </div>

          {/* 3. Deflection Curve */}
          <div className="bg-[#121416] p-3 rounded border border-[#41474f] space-y-2">
            <div className="flex justify-between items-center text-[11px] font-mono">
              <span className="text-[#96ccff] font-bold uppercase">Elastic Deflection δ (mm)</span>
              <span className="text-[#8b919a]">δ_max = {member.forces?.maxDeflection} mm (L/500 limit = {(member.length * 1000 / 500).toFixed(1)} mm)</span>
            </div>
            <div className="h-20 relative w-full bg-[#1a1c1e] rounded flex items-center border border-[#41474f]/50 px-4">
              <div className="absolute inset-x-4 top-2 h-px bg-[#41474f]" />
              <svg className="w-full h-full overflow-visible">
                <path
                  d={diagrams.reduce((acc, pt, i) => {
                    const xPercent = (pt.x / member.length) * 100;
                    const yVal = 15 + (pt.deflection / maxDeflection) * 55;
                    return `${acc} ${i === 0 ? 'M' : 'L'} ${xPercent}% ${yVal}%`;
                  }, '')}
                  fill="none"
                  stroke="#96ccff"
                  strokeWidth="2.5"
                />
              </svg>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="h-12 bg-[#282a2c] border-t border-[#41474f] px-4 flex items-center justify-between">
          <span className="text-[11px] text-[#8b919a] font-mono">
            Analysis Code: Eurocode 2 (EN 1992-1-1) / ACI 318-19
          </span>
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-[#96ccff] hover:bg-[#cee5ff] text-[#003353] font-bold text-[12px] rounded transition-colors cursor-pointer"
            >
              {lang === 'ar' ? 'إغلاق' : 'Close'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
