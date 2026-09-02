import React, { useState } from 'react';
import { 
  Building2, 
  Layers, 
  Grid3X3, 
  Box, 
  ChevronRight, 
  ChevronDown, 
  Compass, 
  ListOrdered, 
  FileText, 
  Terminal, 
  Ruler, 
  CheckCircle,
  Plus,
  Search,
  Building,
  Anchor,
  ArrowDownCircle
} from 'lucide-react';
import { StructuralModel, ElementType } from '../types/structure';

interface ModelExplorerProps {
  model: StructuralModel;
  activeSidebarTab: 'explorer' | 'properties' | 'drawing' | 'view' | 'reports';
  setActiveSidebarTab: (tab: 'explorer' | 'properties' | 'drawing' | 'view' | 'reports') => void;
  selectedElementId: string | null;
  selectedFilterType: ElementType | 'all';
  setSelectedFilterType: (type: ElementType | 'all') => void;
  onSelectMember: (memberId: string) => void;
  onOpenSectionsModal: () => void;
  onOpenMaterialsModal: () => void;
  onOpenReportsModal: () => void;
  onToggleMessages: () => void;
  lang: 'en' | 'ar';
}

export const ModelExplorer: React.FC<ModelExplorerProps> = ({
  model,
  activeSidebarTab,
  setActiveSidebarTab,
  selectedElementId,
  selectedFilterType,
  setSelectedFilterType,
  onSelectMember,
  onOpenSectionsModal,
  onOpenMaterialsModal,
  onOpenReportsModal,
  onToggleMessages,
  lang
}) => {
  // Search query
  const [searchQuery, setSearchQuery] = useState('');

  // Tree collapse states
  const [openStories, setOpenStories] = useState(true);
  const [openGrids, setOpenGrids] = useState(false);
  const [openMaterials, setOpenMaterials] = useState(false);
  const [openSections, setOpenSections] = useState(false);
  const [openElements, setOpenElements] = useState(true);
  const [openSupports, setOpenSupports] = useState(false);
  const [openLoads, setOpenLoads] = useState(false);

  const columnCount = model.members.filter(m => m.type === 'column').length;
  const beamCount = model.members.filter(m => m.type === 'beam').length;
  const braceCount = model.members.filter(m => m.type === 'brace').length;
  const slabCount = model.slabs.length;
  const wallCount = model.walls?.length || 0;
  const openingCount = model.openings?.length || 0;
  const linkCount = model.links?.length || 0;
  const springCount = model.springs?.length || 0;
  const diaphragmCount = model.diaphragms?.length || 0;
  const supportCount = model.nodes.filter(n => n.isRestrained).length;

  const filteredMembers = model.members.filter(m => 
    !searchQuery || m.id.toLowerCase().includes(searchQuery.toLowerCase()) || m.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className="w-[280px] h-full bg-[#1e2022] border-r border-[#41474f] flex flex-col flex-shrink-0 z-40 select-none text-[12px]">
      {/* Header Info */}
      <div className="p-3 border-b border-[#41474f] bg-[#1a1c1e]">
        <div className="flex items-center space-x-2.5 rtl:space-x-reverse">
          <div className="w-8 h-8 bg-[#333537] rounded flex items-center justify-center shrink-0 border border-[#41474f]/50">
            <Building2 className="w-4 h-4 text-[#96ccff]" />
          </div>
          <div className="min-w-0">
            <h2 className="text-[14px] font-semibold text-[#e2e2e5] tracking-tight truncate">
              {lang === 'ar' ? 'مستكشف النموذج' : 'Model Explorer'}
            </h2>
            <div className="font-mono text-[10px] text-[#c1c7d0] mt-0.5 flex items-center space-x-1.5 rtl:space-x-reverse">
              <span>{model.projectName}</span>
              <span className="text-[#7ed99e] font-bold">{model.version}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Side Nav Tabs */}
      <div className="flex flex-col p-2 space-y-1 border-b border-[#41474f] bg-[#1e2022]">
        <button
          onClick={() => setActiveSidebarTab('explorer')}
          className={`flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right rounded-xs transition-all cursor-pointer ${
            activeSidebarTab === 'explorer'
              ? 'bg-[#783f00] text-[#ffad68] font-semibold shadow-inner'
              : 'text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5]'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'المستكشف' : 'EXPLORER'}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveSidebarTab('properties');
            onOpenSectionsModal();
          }}
          className={`flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right rounded-xs transition-all cursor-pointer ${
            activeSidebarTab === 'properties'
              ? 'bg-[#783f00] text-[#ffad68] font-semibold'
              : 'text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5]'
          }`}
        >
          <ListOrdered className="w-4 h-4" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'الخصائص والمقاطع' : 'PROPERTIES'}
          </span>
        </button>

        <button
          onClick={() => setActiveSidebarTab('drawing')}
          className={`flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right rounded-xs transition-all cursor-pointer ${
            activeSidebarTab === 'drawing'
              ? 'bg-[#783f00] text-[#ffad68] font-semibold'
              : 'text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5]'
          }`}
        >
          <Compass className="w-4 h-4" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'الرسم والمحاور' : 'DRAWING'}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveSidebarTab('reports');
            onOpenReportsModal();
          }}
          className={`flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right rounded-xs transition-all cursor-pointer ${
            activeSidebarTab === 'reports'
              ? 'bg-[#783f00] text-[#ffad68] font-semibold'
              : 'text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5]'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'التقارير الإنشائية' : 'REPORTS'}
          </span>
        </button>
      </div>

      {/* Search Input */}
      <div className="p-2 border-b border-[#41474f] bg-[#1a1c1e]">
        <div className="flex items-center bg-[#282a2c] border border-[#41474f] rounded px-2 py-1">
          <Search className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search elements (C1, B2, S1)..."
            className="w-full bg-transparent outline-none text-[11px] text-[#e2e2e5] placeholder-[#60656c] font-mono"
          />
        </div>
      </div>

      {/* Structure Tree Content */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        <div className="text-[10px] font-bold text-[#8b919a] uppercase tracking-wider mb-2 pl-1">
          {lang === 'ar' ? 'شجرة المنشأ' : 'Structure Tree'}
        </div>

        <div className="flex flex-col font-mono text-[11px] space-y-0.5">
          {/* Stories Tree */}
          <div>
            <div
              onClick={() => setOpenStories(!openStories)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openStories ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Layers className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'الطوابق' : 'Stories'} ({model.stories.length})
              </span>
            </div>

            {openStories && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5 text-[10px]">
                {model.stories.map((story) => (
                  <div key={story.id} className="flex items-center justify-between h-[20px] hover:bg-[#282a2c] px-2 rounded text-[#c1c7d0]">
                    <span>{story.name}</span>
                    <span className="text-[#8b919a] font-mono">+{story.elevation.toFixed(1)}m</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Grids Tree */}
          <div>
            <div
              onClick={() => setOpenGrids(!openGrids)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openGrids ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Grid3X3 className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'المحاور الإنشائية' : 'Grids'} ({model.gridLinesX.length}x{model.gridLinesY.length})
              </span>
            </div>

            {openGrids && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5 text-[10px]">
                <div className="text-[#8b919a] px-1 py-0.5">X: {model.gridLinesX.map(g => g.label).join(', ')}</div>
                <div className="text-[#8b919a] px-1 py-0.5">Y: {model.gridLinesY.map(g => g.label).join(', ')}</div>
              </div>
            )}
          </div>

          {/* Materials Tree */}
          <div>
            <div
              onClick={() => setOpenMaterials(!openMaterials)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openMaterials ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Box className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'المواد الإنشائية' : 'Materials'} ({model.materials.length})
              </span>
            </div>

            {openMaterials && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5">
                {model.materials.map((mat) => (
                  <div
                    key={mat.id}
                    onClick={onOpenMaterialsModal}
                    className="flex items-center h-[22px] hover:bg-[#282a2c] cursor-pointer rounded px-2 text-[#c1c7d0] transition-colors"
                  >
                    <div 
                      className="w-2 h-2 rounded-full mr-2 rtl:mr-0 rtl:ml-2 shrink-0" 
                      style={{ backgroundColor: mat.color }} 
                    />
                    <span>{mat.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sections Tree */}
          <div>
            <div
              onClick={() => setOpenSections(!openSections)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openSections ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Ruler className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'المقاطع العرضية' : 'Sections'} ({model.sections.length})
              </span>
            </div>

            {openSections && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5">
                {model.sections.map((sec) => (
                  <div
                    key={sec.id}
                    onClick={onOpenSectionsModal}
                    className="flex items-center justify-between h-[22px] hover:bg-[#282a2c] cursor-pointer rounded px-2 text-[#c1c7d0]"
                  >
                    <span className="truncate">{sec.name}</span>
                    <span className="text-[9px] text-[#7ed99e] font-mono">{sec.shape}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Elements Tree (Columns, Beams, Slabs, Walls) */}
          <div>
            <div
              onClick={() => setOpenElements(!openElements)}
              className="flex items-center h-[24px] bg-[#333537] cursor-pointer rounded px-1.5 border border-[#41474f] transition-colors"
            >
              {openElements ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#96ccff] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#96ccff] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Box className="w-3.5 h-3.5 text-[#96ccff] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5] font-bold">
                {lang === 'ar' ? 'العناصر الإنشائية' : 'Elements'}
              </span>
            </div>

            {openElements && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#96ccff] ml-2 rtl:ml-0 rtl:mr-2 my-0.5 space-y-0.5">
                {/* Columns */}
                <div
                  onClick={() => {
                    setSelectedFilterType(selectedFilterType === 'column' ? 'all' : 'column');
                    const firstCol = model.members.find(m => m.type === 'column');
                    if (firstCol) onSelectMember(firstCol.id);
                  }}
                  className={`flex items-center justify-between h-[22px] cursor-pointer rounded px-2 transition-colors ${
                    selectedFilterType === 'column' || selectedElementId?.startsWith('C')
                      ? 'bg-[#96ccff]/15 text-[#96ccff] font-bold border border-[#96ccff]/30'
                      : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                  }`}
                >
                  <span>Columns ({columnCount})</span>
                  <span className="text-[9px] text-[#7ed99e]">RC 400x400</span>
                </div>

                {/* Beams */}
                <div
                  onClick={() => {
                    setSelectedFilterType(selectedFilterType === 'beam' ? 'all' : 'beam');
                    const firstBeam = model.members.find(m => m.type === 'beam');
                    if (firstBeam) onSelectMember(firstBeam.id);
                  }}
                  className={`flex items-center justify-between h-[22px] cursor-pointer rounded px-2 transition-colors ${
                    selectedFilterType === 'beam'
                      ? 'bg-[#96ccff]/15 text-[#96ccff] font-bold border border-[#96ccff]/30'
                      : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                  }`}
                >
                  <span>Beams ({beamCount})</span>
                  <span className="text-[9px] text-[#8b919a]">300x500</span>
                </div>

                {/* Braces */}
                {braceCount > 0 && (
                  <div
                    onClick={() => {
                      setSelectedFilterType(selectedFilterType === 'brace' ? 'all' : 'brace');
                      const firstBrace = model.members.find(m => m.type === 'brace');
                      if (firstBrace) onSelectMember(firstBrace.id);
                    }}
                    className={`flex items-center justify-between h-[22px] cursor-pointer rounded px-2 transition-colors ${
                      selectedFilterType === 'brace' || selectedElementId?.startsWith('BR')
                        ? 'bg-[#96ccff]/15 text-[#96ccff] font-bold border border-[#96ccff]/30'
                        : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                    }`}
                  >
                    <span>Braces ({braceCount})</span>
                    <span className="text-[9px] text-[#7ed99e]">Steel/RC</span>
                  </div>
                )}

                {/* Slabs */}
                <div
                  onClick={() => {
                    setSelectedFilterType(selectedFilterType === 'slab' ? 'all' : 'slab');
                    if (model.slabs.length > 0) onSelectMember(model.slabs[0].id);
                  }}
                  className={`flex items-center justify-between h-[22px] cursor-pointer rounded px-2 transition-colors ${
                    selectedFilterType === 'slab'
                      ? 'bg-[#96ccff]/15 text-[#96ccff] font-bold border border-[#96ccff]/30'
                      : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                  }`}
                >
                  <span>Slabs ({slabCount})</span>
                  <span className="text-[9px] text-[#8b919a]">200mm</span>
                </div>

                {/* Shear Walls */}
                {wallCount > 0 && (
                  <div
                    onClick={() => {
                      setSelectedFilterType(selectedFilterType === 'wall' ? 'all' : 'wall');
                      if (model.walls && model.walls.length > 0) onSelectMember(model.walls[0].id);
                    }}
                    className={`flex items-center justify-between h-[22px] cursor-pointer rounded px-2 transition-colors ${
                      selectedFilterType === 'wall'
                        ? 'bg-[#96ccff]/15 text-[#96ccff] font-bold border border-[#96ccff]/30'
                        : 'text-[#c1c7d0] hover:bg-[#282a2c]'
                    }`}
                  >
                    <span>Shear Walls ({wallCount})</span>
                    <span className="text-[9px] text-[#8b919a]">250mm</span>
                  </div>
                )}

                {/* Openings */}
                {openingCount > 0 && (
                  <div
                    onClick={() => {
                      if (model.openings && model.openings.length > 0) onSelectMember(model.openings[0].id);
                    }}
                    className="flex items-center justify-between h-[22px] cursor-pointer rounded px-2 text-[#c1c7d0] hover:bg-[#282a2c]"
                  >
                    <span>Openings ({openingCount})</span>
                    <span className="text-[9px] text-[#ffb77d]">Cutout</span>
                  </div>
                )}

                {/* Links */}
                {linkCount > 0 && (
                  <div
                    onClick={() => {
                      if (model.links && model.links.length > 0) onSelectMember(model.links[0].id);
                    }}
                    className="flex items-center justify-between h-[22px] cursor-pointer rounded px-2 text-[#c1c7d0] hover:bg-[#282a2c]"
                  >
                    <span>Links ({linkCount})</span>
                    <span className="text-[9px] text-[#ffad68]">Two-Node</span>
                  </div>
                )}

                {/* Springs */}
                {springCount > 0 && (
                  <div
                    onClick={() => {
                      if (model.springs && model.springs.length > 0) onSelectMember(model.springs[0].id);
                    }}
                    className="flex items-center justify-between h-[22px] cursor-pointer rounded px-2 text-[#c1c7d0] hover:bg-[#282a2c]"
                  >
                    <span>Springs ({springCount})</span>
                    <span className="text-[9px] text-[#7ed99e]">Soil-Base</span>
                  </div>
                )}

                {/* Diaphragms */}
                {diaphragmCount > 0 && (
                  <div
                    onClick={() => {
                      if (model.diaphragms && model.diaphragms.length > 0) onSelectMember(model.diaphragms[0].id);
                    }}
                    className="flex items-center justify-between h-[22px] cursor-pointer rounded px-2 text-[#c1c7d0] hover:bg-[#282a2c]"
                  >
                    <span>Diaphragms ({diaphragmCount})</span>
                    <span className="text-[9px] text-[#96ccff]">Rigid Floor</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Supports Tree */}
          <div>
            <div
              onClick={() => setOpenSupports(!openSupports)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openSupports ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <Anchor className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'الركائز والقيود' : 'Supports'} ({supportCount})
              </span>
            </div>

            {openSupports && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5 text-[10px] text-[#8b919a]">
                <div>Fixed Base Footings (Story 0)</div>
              </div>
            )}
          </div>

          {/* Loads Tree */}
          <div>
            <div
              onClick={() => setOpenLoads(!openLoads)}
              className="flex items-center h-[24px] hover:bg-[#282a2c] cursor-pointer rounded px-1.5 transition-colors"
            >
              {openLoads ? (
                <ChevronDown className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-[#8b919a] mr-1 rtl:mr-0 rtl:ml-1" />
              )}
              <ArrowDownCircle className="w-3.5 h-3.5 text-[#8b919a] mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              <span className="text-[#e2e2e5]">
                {lang === 'ar' ? 'الأحمال والتراكيب' : 'Loads & Combos'}
              </span>
            </div>

            {openLoads && (
              <div className="flex flex-col pl-4 rtl:pl-0 rtl:pr-4 border-l rtl:border-l-0 rtl:border-r border-[#41474f] ml-2 rtl:ml-0 rtl:mr-2 my-0.5 text-[10px] text-[#8b919a]">
                <div>• Dead Load (DL = 5 kN/m2)</div>
                <div>• Live Load (LL = 3 kN/m2)</div>
                <div>• 1.2 DL + 1.6 LL (Ultimate ULS)</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Nav in Sidebar */}
      <div className="flex flex-col p-2 space-y-1 border-t border-[#41474f] bg-[#1a1c1e] mt-auto">
        <button
          onClick={onToggleMessages}
          className="flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5] rounded-xs transition-colors cursor-pointer"
        >
          <Terminal className="w-4 h-4 text-[#7ed99e]" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'سجل المحلل والرسائل' : 'MESSAGES & LOGS'}
          </span>
        </button>

        <button
          onClick={onOpenReportsModal}
          className="flex items-center space-x-2.5 rtl:space-x-reverse px-3 py-1.5 w-full text-left rtl:text-right text-[#c1c7d0] hover:bg-[#282a2c] hover:text-[#e2e2e5] rounded-xs transition-colors cursor-pointer"
        >
          <Ruler className="w-4 h-4 text-[#96ccff]" />
          <span className="font-bold text-[10px] tracking-wider uppercase">
            {lang === 'ar' ? 'الوحدات والمعايير' : 'UNITS: ' + model.units}
          </span>
        </button>
      </div>
    </aside>
  );
};
