import React from 'react';
import { X, Building2, Factory, Network, Layers, Check } from 'lucide-react';
import { createDefaultRCBuilding, createSteelPortalFrameModel } from '../data/defaultModels';
import { StructuralModel } from '../types/structure';

interface TemplatesModalProps {
  onSelectModel: (model: StructuralModel) => void;
  onClose: () => void;
  lang: 'en' | 'ar';
}

export const TemplatesModal: React.FC<TemplatesModalProps> = ({
  onSelectModel,
  onClose,
  lang
}) => {
  const templates = [
    {
      id: 'rc-2story',
      title: lang === 'ar' ? 'مبنى خرساني دورين (2-Story RC Frame)' : '2-Story RC Building (Structure-X Default)',
      desc: lang === 'ar' ? 'نموذج الإطار الخرساني الافتراضي المطابق للمشروع: 24 عمود، 42 كمرة، 12 بلاطة، خرسانة C30/37' : 'Standard 2-story reinforced concrete frame with 24 columns, 42 beams, 12 slabs, C30/37 concrete & 400x400 RC columns.',
      icon: Building2,
      badge: 'PRO DEFAULT',
      modelGen: createDefaultRCBuilding
    },
    {
      id: 'steel-portal',
      title: lang === 'ar' ? 'إطار جمالوني حديدي (Industrial Portal Frame)' : 'Steel Industrial Portal Frame',
      desc: lang === 'ar' ? 'هيكل فولاذي صناعي بمقاطع HEB 300 للأعمدة و IPE 400 للكمرات وجسور السقف، فولاذ S355' : 'Clear-span industrial steel warehouse frame with HEB 300 columns, IPE 400 rafters, and longitudinal purlins.',
      icon: Factory,
      badge: 'STEEL EC3',
      modelGen: createSteelPortalFrameModel
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in-50">
      <div className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-2xl flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="h-10 bg-[#282a2c] border-b border-[#41474f] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Building2 className="w-4 h-4 text-[#96ccff]" />
            <span className="font-semibold text-[13px] text-[#e2e2e5]">
              {lang === 'ar' ? 'قوالب ونماذج المنشآت الهندسية الجاهزة' : 'Structural Project Templates & Archetypes'}
            </span>
          </div>
          <button onClick={onClose} className="text-[#c1c7d0] hover:text-[#e2e2e5]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          <p className="text-[12px] text-[#c1c7d0]">
            {lang === 'ar' ? 'اختر قالباً لبدء العمل فوراً في بيئة النمذجة والتحليل الإنشائي:' : 'Select a structural archetype to instantly initialize the 3D CAD modeling and analysis workspace:'}
          </p>

          <div className="grid grid-cols-1 gap-3">
            {templates.map((tpl) => (
              <div
                key={tpl.id}
                onClick={() => {
                  onSelectModel(tpl.modelGen());
                  onClose();
                }}
                className="bg-[#1a1c1e] hover:bg-[#282a2c] border border-[#41474f] hover:border-[#96ccff] rounded-lg p-3 cursor-pointer transition-all flex items-start space-x-3 rtl:space-x-reverse group"
              >
                <div className="w-10 h-10 bg-[#333537] group-hover:bg-[#96ccff]/20 rounded-md flex items-center justify-center shrink-0 border border-[#41474f]">
                  <tpl.icon className="w-5 h-5 text-[#96ccff]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <h3 className="text-[13px] font-semibold text-[#e2e2e5] group-hover:text-[#96ccff] transition-colors">
                      {tpl.title}
                    </h3>
                    <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 bg-[#47a26b]/20 text-[#7ed99e] rounded border border-[#7ed99e]/30">
                      {tpl.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#8b919a] mt-1 leading-relaxed">
                    {tpl.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="h-10 bg-[#282a2c] border-t border-[#41474f] px-4 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1 bg-[#333537] hover:bg-[#41474f] text-[#c1c7d0] text-[12px] rounded"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
