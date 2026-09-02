import React from 'react';
import { CameraPreset } from '../../types/structure';
import { Compass, RotateCw } from 'lucide-react';

interface ViewCubeProps {
  onSelectPreset: (preset: CameraPreset) => void;
  onResetView: () => void;
  lang?: 'en' | 'ar';
}

export const ViewCube: React.FC<ViewCubeProps> = ({
  onSelectPreset,
  onResetView,
  lang = 'en'
}) => {
  return (
    <div className="absolute top-3 right-3 z-30 flex flex-col items-center select-none">
      {/* 3D ViewCube Box Widget */}
      <div className="w-[84px] h-[84px] bg-[#1e2022]/90 backdrop-blur-md border border-[#41474f] rounded-lg shadow-2xl p-1 flex flex-col justify-between">
        {/* Top View Cube Button */}
        <div className="flex justify-center">
          <button
            onClick={() => onSelectPreset('plan')}
            className="px-2 py-0.5 text-[9px] font-mono font-bold bg-[#282a2c] hover:bg-[#96ccff] hover:text-[#003353] text-[#c1c7d0] rounded transition-all cursor-pointer"
            title="Plan View (Top XY)"
          >
            TOP
          </button>
        </div>

        {/* Middle row: Left, ISO, Right */}
        <div className="flex justify-between items-center px-0.5">
          <button
            onClick={() => onSelectPreset('elevation-yz')}
            className="px-1.5 py-0.5 text-[8px] font-mono font-bold bg-[#282a2c] hover:bg-[#96ccff] hover:text-[#003353] text-[#c1c7d0] rounded transition-all cursor-pointer"
            title="Left / Side View (YZ)"
          >
            L
          </button>

          <button
            onClick={() => onSelectPreset('iso')}
            className="px-2 py-1 text-[9px] font-mono font-bold bg-[#47a26b]/20 border border-[#7ed99e]/40 hover:bg-[#7ed99e] hover:text-[#003353] text-[#7ed99e] rounded transition-all cursor-pointer shadow"
            title="3D Isometric View"
          >
            3D
          </button>

          <button
            onClick={() => onSelectPreset('elevation-yz')}
            className="px-1.5 py-0.5 text-[8px] font-mono font-bold bg-[#282a2c] hover:bg-[#96ccff] hover:text-[#003353] text-[#c1c7d0] rounded transition-all cursor-pointer"
            title="Right / Side View (YZ)"
          >
            R
          </button>
        </div>

        {/* Bottom row: Front View */}
        <div className="flex justify-center">
          <button
            onClick={() => onSelectPreset('elevation-xz')}
            className="px-2 py-0.5 text-[9px] font-mono font-bold bg-[#282a2c] hover:bg-[#96ccff] hover:text-[#003353] text-[#c1c7d0] rounded transition-all cursor-pointer"
            title="Front Elevation View (XZ)"
          >
            FRONT
          </button>
        </div>
      </div>

      {/* Quick Corner Preset Pills */}
      <div className="flex items-center space-x-1 rtl:space-x-reverse mt-1.5 bg-[#121416]/80 p-0.5 rounded border border-[#282a2c]">
        <button
          onClick={() => onSelectPreset('iso-ne')}
          className="px-1 text-[8px] font-mono text-[#8b919a] hover:text-[#96ccff] hover:bg-[#282a2c] rounded"
          title="Isometric North-East"
        >
          NE
        </button>
        <button
          onClick={() => onSelectPreset('iso-nw')}
          className="px-1 text-[8px] font-mono text-[#8b919a] hover:text-[#96ccff] hover:bg-[#282a2c] rounded"
          title="Isometric North-West"
        >
          NW
        </button>
        <button
          onClick={() => onSelectPreset('iso-se')}
          className="px-1 text-[8px] font-mono text-[#8b919a] hover:text-[#96ccff] hover:bg-[#282a2c] rounded"
          title="Isometric South-East"
        >
          SE
        </button>
        <button
          onClick={() => onSelectPreset('iso-sw')}
          className="px-1 text-[8px] font-mono text-[#8b919a] hover:text-[#96ccff] hover:bg-[#282a2c] rounded"
          title="Isometric South-West"
        >
          SW
        </button>
      </div>
    </div>
  );
};
