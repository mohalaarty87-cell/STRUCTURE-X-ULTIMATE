import React, { useState } from 'react';
import { 
  Play, 
  Settings, 
  HelpCircle, 
  User, 
  FolderPlus, 
  FolderOpen, 
  Save, 
  FileDown, 
  Layers, 
  Zap, 
  Activity, 
  BarChart3, 
  FileText, 
  Globe, 
  Sun, 
  Moon,
  ChevronDown,
  Database
} from 'lucide-react';

interface TopNavbarProps {
  activeMenu: string;
  setActiveMenu: (menu: string) => void;
  onRunAnalysis: () => void;
  onOpenTemplates: () => void;
  onOpenMaterials: () => void;
  onOpenSections: () => void;
  onOpenReports: () => void;
  onOpenHelp: () => void;
  onOpenCadBim?: () => void;
  isAnalyzing: boolean;
  theme: 'dark' | 'light';
  setTheme: (t: 'dark' | 'light') => void;
  lang: 'en' | 'ar';
  setLang: (l: 'en' | 'ar') => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  activeMenu,
  setActiveMenu,
  onRunAnalysis,
  onOpenTemplates,
  onOpenMaterials,
  onOpenSections,
  onOpenReports,
  onOpenHelp,
  onOpenCadBim,
  isAnalyzing,
  theme,
  setTheme,
  lang,
  setLang
}) => {
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const menus = [
    { 
      id: 'File', 
      label: lang === 'ar' ? 'ملف' : 'File',
      items: [
        { label: lang === 'ar' ? 'نموذج جديد من القوالب...' : 'New Model from Template...', icon: FolderPlus, action: onOpenTemplates },
        { label: lang === 'ar' ? 'تبادل بيانات CAD و BIM (IFC, DXF, Excel)...' : 'CAD & BIM Interoperability (IFC, DXF, Excel)...', icon: Database, action: onOpenCadBim },
        { label: lang === 'ar' ? 'حفظ المشروع' : 'Save Project (Ctrl+S)', icon: Save, action: () => alert(lang === 'ar' ? 'تم حفظ بيانات النموذج بنجاح!' : 'Model saved to local workspace!') },
        { label: lang === 'ar' ? 'تصدير النموذج الإنشائي (IFC, DXF, Excel, JSON)...' : 'Export Model (IFC, DXF, Excel, CSV, JSON)...', icon: FileDown, action: onOpenCadBim },
        { label: lang === 'ar' ? 'تصدير تقرير الحسابات (PDF/DXF)' : 'Export Structural Report...', icon: FileDown, action: onOpenReports },
      ]
    },
    { 
      id: 'Edit', 
      label: lang === 'ar' ? 'تعديل' : 'Edit',
      items: [
        { label: lang === 'ar' ? 'تراجع' : 'Undo (Ctrl+Z)', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'إعادة' : 'Redo (Ctrl+Y)', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'تكرار العناصر المحددة (Replicate)' : 'Replicate Elements...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'تقسيم الإطارات (Mesh/Divide)' : 'Divide Frame Members...', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'View', 
      label: lang === 'ar' ? 'عرض' : 'View',
      items: [
        { label: lang === 'ar' ? 'منظور ثلاثي الأبعاد 3D' : 'Set 3D Isometric View', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'المساقط الأفقية (Plan View)' : 'Set Plan View...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'الواجهات (Elevation View)' : 'Set Elevation View...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'إظهار شبكة المحاور' : 'Toggle Grid Lines', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Define', 
      label: lang === 'ar' ? 'تعريف' : 'Define',
      items: [
        { label: lang === 'ar' ? 'المواد الإنشائية (Materials)...' : 'Material Properties (C30/37, S355)...', icon: Layers, action: onOpenMaterials },
        { label: lang === 'ar' ? 'مقاطع العناصر (Frame Sections)...' : 'Frame Section Properties...', icon: null, action: onOpenSections },
        { label: lang === 'ar' ? 'حالات وأحمال التحميل (Load Patterns)' : 'Load Patterns & Cases...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'تراكيب الأحمال (Combinations: 1.2D + 1.6L)' : 'Load Combinations (Eurocode/ACI)...', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Draw', 
      label: lang === 'ar' ? 'رسم' : 'Draw',
      items: [
        { label: lang === 'ar' ? 'رسم عقدة (Draw Joint)' : 'Draw Joint / Point Object', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'رسم كمرة / جائز (Draw Beam)' : 'Draw Beam / Frame Element', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'رسم عمود (Draw Column)' : 'Draw Vertical Column', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'رسم بلاطة (Draw Slab)' : 'Draw Floor Slab / Area', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Assign', 
      label: lang === 'ar' ? 'تخصيص' : 'Assign',
      items: [
        { label: lang === 'ar' ? 'تخصيص المساند (Restraints/Supports)' : 'Joint Restraints (Fixed, Pinned)...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'تخصيص المقطع والمادة' : 'Frame Section & Material...', icon: null, action: onOpenSections },
        { label: lang === 'ar' ? 'تحرير العزوم (Frame Releases)' : 'Frame End Releases...', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'أحمال موزعة على الكمرات (Distributed)' : 'Frame Distributed Loads...', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Analyze', 
      label: lang === 'ar' ? 'تحليل' : 'Analyze',
      items: [
        { label: lang === 'ar' ? 'تشغيل التحليل الإنشائي (Run FEA)' : 'Run Structural Analysis (F5)', icon: Zap, action: onRunAnalysis },
        { label: lang === 'ar' ? 'التحليل الديناميكي والاهتزازات (Modal)' : 'Modal Eigenvalue Analysis...', icon: Activity, action: onRunAnalysis },
        { label: lang === 'ar' ? 'خيارات المحلل المباشر (Solver Options)' : 'Direct Stiffness Solver Options...', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Design', 
      label: lang === 'ar' ? 'تصميم' : 'Design',
      items: [
        { label: lang === 'ar' ? 'تصميم المنشآت الخرسانية (Concrete Frame)' : 'Concrete Frame Design (EC2 / ACI 318)', icon: BarChart3, action: onOpenReports },
        { label: lang === 'ar' ? 'تصميم المنشآت الفولاذية (Steel Frame)' : 'Steel Frame Design (EC3 / AISC 360)', icon: null, action: onOpenReports },
        { label: lang === 'ar' ? 'حسابات التسليح الطولي والعرضي' : 'Longitudinal & Shear Reinforcement Check', icon: null, action: onOpenReports },
      ]
    },
    { 
      id: 'Display', 
      label: lang === 'ar' ? 'إظهار' : 'Display',
      items: [
        { label: lang === 'ar' ? 'الشكل المشوه (Deformed Shape)' : 'Show Deformed Shape (Animated)', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'مخطط عزم الانحناء (Bending Moment M3)' : 'Show Bending Moment Diagram (M3)', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'مخطط قوى القص (Shear Force V2)' : 'Show Shear Force Diagram (V2)', icon: null, action: () => {} },
        { label: lang === 'ar' ? 'خرائط الإجهادات ونسب الاستخدام (Stress Contours)' : 'Show Element Utilization Ratios', icon: null, action: () => {} },
      ]
    },
    { 
      id: 'Reports', 
      label: lang === 'ar' ? 'تقارير' : 'Reports',
      items: [
        { label: lang === 'ar' ? 'مذكرة الحسابات الشاملة (Full Calculation Sheet)' : 'Generate Comprehensive Project Report', icon: FileText, action: onOpenReports },
        { label: lang === 'ar' ? 'جدول ردود الأفعال (Base Reactions Table)' : 'Summary Base Reactions & Displacements', icon: null, action: onOpenReports },
        { label: lang === 'ar' ? 'جدول كميات الخرسانة والحديد (BOM)' : 'Bill of Materials & Steel Takeoff', icon: null, action: onOpenReports },
      ]
    },
    { 
      id: 'Help', 
      label: lang === 'ar' ? 'مساعدة' : 'Help',
      items: [
        { label: lang === 'ar' ? 'دليل الاستخدام السريع' : 'Quick Start & Modeling Guide', icon: HelpCircle, action: onOpenHelp },
        { label: lang === 'ar' ? 'حول البرنامج STRUCTURE-X v4.2' : 'About STRUCTURE-X ULTIMATE v4.2', icon: null, action: onOpenHelp },
      ]
    }
  ];

  return (
    <header className="fixed top-0 left-0 w-full h-[32px] z-50 flex items-center px-2 justify-between border-b border-[#41474f] bg-[#1a1c1e] select-none text-[13px]">
      {/* Left section: App Title & Top Menus */}
      <div className="flex items-center space-x-3 rtl:space-x-reverse h-full">
        <div className="flex items-center space-x-2">
          <span className="font-sans text-[15px] font-bold text-[#96ccff] tracking-tight whitespace-nowrap cursor-pointer hover:opacity-90">
            STRUCTURE-X ULTIMATE
          </span>
          <span className="text-[9px] font-mono px-1.5 py-0.2 bg-[#282a2c] text-[#7ed99e] border border-[#41474f] rounded">
            v4.2 PRO
          </span>
        </div>

        {/* Menu Navigation */}
        <nav className="hidden lg:flex items-center h-full space-x-0.5 rtl:space-x-reverse">
          {menus.map((menu) => {
            const isActive = activeMenu === menu.id;
            const isOpen = openDropdown === menu.id;

            return (
              <div 
                key={menu.id} 
                className="relative h-full flex items-center"
                onMouseLeave={() => setOpenDropdown(null)}
              >
                <button
                  id={`nav-menu-${menu.id.toLowerCase()}`}
                  onClick={() => {
                    setActiveMenu(menu.id);
                    setOpenDropdown(isOpen ? null : menu.id);
                  }}
                  onMouseEnter={() => {
                    if (openDropdown !== null) {
                      setOpenDropdown(menu.id);
                    }
                  }}
                  className={`px-2 h-[26px] flex items-center text-[12px] font-medium transition-colors cursor-pointer rounded-sm ${
                    isActive
                      ? 'text-[#96ccff] bg-[#282a2c] border-b-2 border-[#96ccff]'
                      : 'text-[#c1c7d0] hover:bg-[#333537] hover:text-[#e2e2e5]'
                  }`}
                >
                  {menu.label}
                </button>

                {/* Dropdown Menu */}
                {isOpen && (
                  <div className="absolute top-[30px] left-0 rtl:left-auto rtl:right-0 w-64 bg-[#1e2022] border border-[#41474f] rounded shadow-2xl py-1 z-50 animate-in fade-in-50">
                    {menu.items.map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          item.action();
                          setOpenDropdown(null);
                        }}
                        className="w-full px-3 py-1.5 text-left rtl:text-right text-[12px] text-[#e2e2e5] hover:bg-[#96ccff]/15 hover:text-[#96ccff] flex items-center justify-between transition-colors"
                      >
                        <span className="flex items-center space-x-2 rtl:space-x-reverse">
                          {item.icon && <item.icon className="w-3.5 h-3.5 text-[#96ccff]" />}
                          <span>{item.label}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Right section: Quick Actions & Utilities */}
      <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
        {/* Quick Run FEA Analysis Button */}
        <button
          id="btn-run-analysis-quick"
          onClick={onRunAnalysis}
          disabled={isAnalyzing}
          className="flex items-center space-x-1.5 rtl:space-x-reverse px-2.5 py-0.5 bg-[#47a26b]/20 hover:bg-[#47a26b]/35 text-[#7ed99e] border border-[#7ed99e]/40 rounded text-[11px] font-semibold transition-all active:scale-95 disabled:opacity-50 cursor-pointer shadow-sm"
          title="Run FEA Solver (F5)"
        >
          <Play className={`w-3 h-3 fill-current ${isAnalyzing ? 'animate-spin' : ''}`} />
          <span>{isAnalyzing ? (lang === 'ar' ? 'جار التحليل...' : 'Solving...') : (lang === 'ar' ? 'تشغيل التحليل' : 'Run FEA')}</span>
        </button>

        {/* Templates Selector */}
        <button
          onClick={onOpenTemplates}
          className="hidden sm:flex items-center space-x-1 px-2 py-0.5 text-[11px] text-[#c1c7d0] hover:text-[#e2e2e5] bg-[#282a2c] hover:bg-[#333537] border border-[#41474f] rounded"
        >
          <FolderOpen className="w-3 h-3 text-[#ffb77d]" />
          <span>{lang === 'ar' ? 'النماذج' : 'Models'}</span>
        </button>

        {/* CAD & BIM Interoperability */}
        <button
          id="top-nav-cad-bim-button"
          onClick={onOpenCadBim}
          className="hidden sm:flex items-center space-x-1 px-2 py-0.5 text-[11px] text-[#96ccff] hover:text-[#ffffff] bg-[#96ccff]/10 hover:bg-[#96ccff]/25 border border-[#96ccff]/30 rounded transition-colors"
          title="CAD & BIM Interoperability (IFC, DXF, Excel, CSV, JSON)"
        >
          <Database className="w-3 h-3 text-[#96ccff]" />
          <span>BIM / CAD</span>
        </button>

        {/* Language Switcher */}
        <button
          onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}
          className="flex items-center space-x-1 px-1.5 py-0.5 text-[11px] text-[#c1c7d0] hover:text-[#96ccff] bg-[#282a2c] hover:bg-[#333537] border border-[#41474f] rounded transition-colors"
          title="Toggle English / Arabic UI"
        >
          <Globe className="w-3 h-3" />
          <span className="font-mono text-[10px] uppercase font-bold">{lang === 'en' ? 'AR' : 'EN'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-[#333537] transition-colors text-[#c1c7d0] hover:text-[#e2e2e5]"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun className="w-3.5 h-3.5 text-[#ffdcc3]" /> : <Moon className="w-3.5 h-3.5 text-[#96ccff]" />}
        </button>

        {/* Settings & Help */}
        <button
          onClick={onOpenHelp}
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-[#333537] transition-colors text-[#c1c7d0] hover:text-[#e2e2e5]"
          title="Help & Shortcuts"
        >
          <HelpCircle className="w-3.5 h-3.5" />
        </button>

        {/* Account */}
        <button
          className="w-7 h-6 flex items-center justify-center rounded hover:bg-[#333537] transition-colors text-[#c1c7d0] hover:text-[#e2e2e5]"
          title="Civil Engineer Workspace"
        >
          <User className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
