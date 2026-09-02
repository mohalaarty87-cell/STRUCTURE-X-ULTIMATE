import React, { useState } from 'react';
import { CheckCircle2, ChevronDown, Activity, Terminal, Magnet, Camera } from 'lucide-react';
import { StructuralModel } from '../types/structure';

interface StatusBarProps {
  model: StructuralModel;
  selectedElementId: string | null;
  cursorCoordinates?: { x: number; y: number; z: number };
  isSnapping?: boolean;
  projectionMode?: string;
  isConsoleOpen?: boolean;
  onToggleConsole?: () => void;
  onOpenValidationModal: () => void;
  onSelectUnit: (unit: StructuralModel['units']) => void;
  lang: 'en' | 'ar';
}

export const StatusBar: React.FC<StatusBarProps> = ({
  model,
  selectedElementId,
  cursorCoordinates = { x: 0, y: 0, z: 0 },
  isSnapping = true,
  projectionMode = 'PERS',
  isConsoleOpen = false,
  onToggleConsole,
  onOpenValidationModal,
  onSelectUnit,
  lang
}) => {
  const [showUnitsMenu, setShowUnitsMenu] = useState(false);

  const unitsList: StructuralModel['units'][] = [
    'kN-m, C',
    'N-mm, C',
    'kip-ft, F',
    'kgf-cm, C'
  ];

  return (
    <footer className="fixed bottom-0 left-0 w-full h-[24px] z-50 flex items-center px-2.5 justify-between border-t border-[#41474f] bg-[#0c0e10] font-mono text-[11px] select-none text-[#c1c7d0]">
      {/* Left side: Copyright & Engine Status + Model Validation */}
      <div className="flex items-center space-x-3 rtl:space-x-reverse h-full">
        <span className="text-[10px] font-bold text-[#8b919a] uppercase tracking-wider">
          STRUCTURE-X ULTIMATE | CAD ENGINE V4.2
        </span>

        <div className="w-px h-3.5 bg-[#41474f]" />

        {/* Model Validation Status */}
        <button
          onClick={onOpenValidationModal}
          className="flex items-center space-x-1.5 rtl:space-x-reverse text-[#7ed99e] hover:underline cursor-pointer"
          title="Click to view model health validation logs"
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-[#7ed99e] fill-[#7ed99e]/20" />
          <span className="text-[10px]">
            {lang === 'ar' ? 'فحص النموذج: 0 أخطاء' : 'Model Health: 0 Errors, 0 Warnings'}
          </span>
        </button>

        <div className="w-px h-3.5 bg-[#41474f]" />

        {/* Console Toggle */}
        {onToggleConsole && (
          <button
            onClick={onToggleConsole}
            className={`flex items-center space-x-1 px-1.5 py-0.5 rounded transition-colors cursor-pointer text-[10px] ${
              isConsoleOpen ? 'bg-[#96ccff]/20 text-[#96ccff]' : 'text-[#8b919a] hover:text-[#e2e2e5]'
            }`}
            title="Toggle Engineering Console"
          >
            <Terminal className="w-3 h-3 text-[#96ccff]" />
            <span>CLI</span>
          </button>
        )}
      </div>

      {/* Center: Live Cursor & Selection Status */}
      <div className="hidden md:flex items-center space-x-3 rtl:space-x-reverse h-full text-[10px]">
        <div className="text-[#8b919a]">
          XYZ: <span className="text-[#96ccff]">({cursorCoordinates.x.toFixed(2)}, {cursorCoordinates.y.toFixed(2)}, {cursorCoordinates.z.toFixed(2)})m</span>
        </div>

        <div className="w-px h-3.5 bg-[#41474f]" />

        <div className="flex items-center space-x-1">
          <Magnet className={`w-3 h-3 ${isSnapping ? 'text-[#7ed99e]' : 'text-[#8b919a]'}`} />
          <span>SNAP: {isSnapping ? 'ON' : 'OFF'}</span>
        </div>

        <div className="w-px h-3.5 bg-[#41474f]" />

        <div className="text-[#c1c7d0]">
          {selectedElementId ? (
            <span className="text-[#7ed99e] font-bold">1 Selected [{selectedElementId}]</span>
          ) : (
            <span className="text-[#8b919a]">No selection</span>
          )}
        </div>
      </div>

      {/* Right side: System Status & Units Switcher */}
      <div className="flex items-center space-x-3 rtl:space-x-reverse h-full">
        <div 
          onClick={onOpenValidationModal}
          className="flex items-center space-x-1 text-[#c1c7d0] hover:text-[#96ccff] transition-colors cursor-pointer text-[10px]"
        >
          <Activity className="w-3 h-3 text-[#7ed99e]" />
          <span>{lang === 'ar' ? 'الحالة: متصل' : 'System: Ready'}</span>
        </div>

        <div className="w-px h-3.5 bg-[#41474f]" />

        {/* Active Units Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowUnitsMenu(!showUnitsMenu)}
            className="flex items-center text-[#7ed99e] font-bold px-2 py-0.5 bg-[#47a26b]/15 hover:bg-[#47a26b]/25 border border-[#7ed99e]/30 rounded cursor-pointer transition-colors text-[10px]"
          >
            <span>{model.units}</span>
            <ChevronDown className="w-3 h-3 ml-1 rtl:ml-0 rtl:mr-1" />
          </button>

          {showUnitsMenu && (
            <div className="absolute bottom-[26px] right-0 rtl:right-auto rtl:left-0 w-36 bg-[#1e2022] border border-[#41474f] rounded shadow-2xl py-1 z-50">
              {unitsList.map((unit) => (
                <button
                  key={unit}
                  onClick={() => {
                    onSelectUnit(unit);
                    setShowUnitsMenu(false);
                  }}
                  className={`w-full px-3 py-1 text-left rtl:text-right text-[11px] font-mono hover:bg-[#96ccff]/20 hover:text-[#96ccff] transition-colors ${
                    model.units === unit ? 'text-[#7ed99e] font-bold bg-[#7ed99e]/10' : 'text-[#e2e2e5]'
                  }`}
                >
                  {unit}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </footer>
  );
};
