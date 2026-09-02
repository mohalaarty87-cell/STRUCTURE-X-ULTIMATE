import React, { useState } from 'react';
import { X, Layers, Plus, Check } from 'lucide-react';
import { Material, MaterialType } from '../types/structure';

interface MaterialsModalProps {
  materials: Material[];
  onSaveMaterial: (material: Material) => void;
  onClose: () => void;
  lang: 'en' | 'ar';
}

export const MaterialsModal: React.FC<MaterialsModalProps> = ({
  materials,
  onSaveMaterial,
  onClose,
  lang
}) => {
  const [selectedMatId, setSelectedMatId] = useState(materials[0]?.id || '');
  const current = materials.find(m => m.id === selectedMatId) || materials[0];

  const [name, setName] = useState(current?.name || '');
  const [type, setType] = useState<MaterialType>(current?.type || 'concrete');
  const [elasticModulusE, setElasticModulusE] = useState(current?.elasticModulusE || 33);
  const [poissonRatio, setPoissonRatio] = useState(current?.poissonRatio || 0.2);
  const [unitWeight, setUnitWeight] = useState(current?.unitWeight || 25);
  const [fc, setFc] = useState(current?.compressiveStrengthFc || 30);
  const [fy, setFy] = useState(current?.yieldStrengthFy || 355);
  const [color, setColor] = useState(current?.color || '#7ed99e');

  const handleSelect = (m: Material) => {
    setSelectedMatId(m.id);
    setName(m.name);
    setType(m.type);
    setElasticModulusE(m.elasticModulusE);
    setPoissonRatio(m.poissonRatio);
    setUnitWeight(m.unitWeight);
    setFc(m.compressiveStrengthFc || 30);
    setFy(m.yieldStrengthFy || 355);
    setColor(m.color);
  };

  const handleSave = () => {
    const updated: Material = {
      id: selectedMatId,
      name,
      grade: name,
      type,
      elasticModulusE,
      poissonRatio,
      unitWeight,
      compressiveStrengthFc: type === 'concrete' ? fc : undefined,
      yieldStrengthFy: type === 'steel' ? fy : undefined,
      color
    };
    onSaveMaterial(updated);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in-50">
      <div className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-2xl flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="h-10 bg-[#282a2c] border-b border-[#41474f] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Layers className="w-4 h-4 text-[#7ed99e]" />
            <span className="font-semibold text-[13px] text-[#e2e2e5]">
              {lang === 'ar' ? 'تعريف خواص المواد الإنشائية' : 'Structural Material Property Definition'}
            </span>
          </div>
          <button onClick={onClose} className="text-[#c1c7d0] hover:text-[#e2e2e5]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex h-80">
          {/* Material List */}
          <div className="w-52 bg-[#1a1c1e] border-r border-[#41474f] p-3 space-y-1">
            <div className="text-[10px] font-bold text-[#8b919a] uppercase tracking-wider mb-2">
              {lang === 'ar' ? 'المواد المعرفة' : 'Materials'}
            </div>
            {materials.map(m => (
              <button
                key={m.id}
                onClick={() => handleSelect(m)}
                className={`w-full px-2.5 py-1.5 rounded text-left rtl:text-right text-[11px] font-mono flex items-center justify-between ${
                  m.id === selectedMatId
                    ? 'bg-[#7ed99e]/20 text-[#7ed99e] font-bold border border-[#7ed99e]/40'
                    : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                }`}
              >
                <div className="flex items-center space-x-2 rtl:space-x-reverse">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: m.color }} />
                  <span>{m.name}</span>
                </div>
                <span className="text-[9px] opacity-70 uppercase">{m.type}</span>
              </button>
            ))}
          </div>

          {/* Form */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 text-[11px]">
            <div>
              <label className="block text-[#c1c7d0] mb-1 font-mono">Material Name / Grade</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[#121416] border border-[#41474f] rounded px-2.5 py-1 text-[#e2e2e5] font-mono focus:border-[#7ed99e] focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Type</label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value as MaterialType)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono focus:border-[#7ed99e] focus:outline-none"
                >
                  <option value="concrete">Concrete</option>
                  <option value="steel">Structural Steel</option>
                </select>
              </div>
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Elastic Modulus E (GPa)</label>
                <input
                  type="number"
                  value={elasticModulusE}
                  onChange={(e) => setElasticModulusE(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Unit Weight γ (kN/m³)</label>
                <input
                  type="number"
                  value={unitWeight}
                  onChange={(e) => setUnitWeight(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono"
                />
              </div>
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Poisson's Ratio ν</label>
                <input
                  type="number"
                  step="0.05"
                  value={poissonRatio}
                  onChange={(e) => setPoissonRatio(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono"
                />
              </div>
            </div>

            {type === 'concrete' ? (
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Compressive Strength f'c / fck (MPa)</label>
                <input
                  type="number"
                  value={fc}
                  onChange={(e) => setFc(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono"
                />
              </div>
            ) : (
              <div>
                <label className="block text-[#c1c7d0] mb-1 font-mono">Yield Strength fy (MPa)</label>
                <input
                  type="number"
                  value={fy}
                  onChange={(e) => setFy(parseFloat(e.target.value) || 0)}
                  className="w-full bg-[#121416] border border-[#41474f] rounded px-2 py-1 text-[#e2e2e5] font-mono"
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="h-12 bg-[#282a2c] border-t border-[#41474f] px-4 flex items-center justify-end space-x-2 rtl:space-x-reverse">
          <button onClick={onClose} className="px-3 py-1 bg-[#333537] text-[#c1c7d0] text-[12px] rounded">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 bg-[#7ed99e] text-[#00391d] font-bold text-[12px] rounded flex items-center space-x-1"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Save Material</span>
          </button>
        </div>
      </div>
    </div>
  );
};
