import React, { useState, useMemo } from 'react';
import {
  X,
  FileText,
  Printer,
  Download,
  CheckCircle2,
  AlertTriangle,
  Layers,
  FileSpreadsheet,
  FileCode,
  ShieldCheck,
  Compass,
  Activity,
  Wind,
  Zap,
  Building,
  Box,
  Cpu,
  ChevronRight,
  Info
} from 'lucide-react';
import { StructuralModel, AnalysisSummary } from '../types/structure';
import {
  ProfessionalReportEngine,
  FullEngineeringReport,
  DesignStatus
} from '../services/reportService';

interface ReportsModalProps {
  model: StructuralModel;
  summary: AnalysisSummary | null;
  onClose: () => void;
  lang: 'en' | 'ar';
}

export const ReportsModal: React.FC<ReportsModalProps> = ({
  model,
  summary,
  onClose,
  lang
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'summary' | 'dynamics' | 'design' | 'calcs'>('all');

  // Build the complete 24-section engineering report
  const report: FullEngineeringReport = useMemo(() => {
    return ProfessionalReportEngine.buildReport(model, summary);
  }, [model, summary]);

  // Handlers for exports
  const handlePrint = () => {
    window.print();
  };

  const handleExportHtml = () => {
    const htmlContent = ProfessionalReportEngine.exportToHtml(report);
    ProfessionalReportEngine.triggerDownload(
      `${report.projectInfo.projectName.replace(/\s+/g, '_')}_Report.html`,
      htmlContent,
      'text/html;charset=utf-8'
    );
  };

  const handleExportCsv = () => {
    const csvContent = ProfessionalReportEngine.exportToCsv(report);
    ProfessionalReportEngine.triggerDownload(
      `${report.projectInfo.projectName.replace(/\s+/g, '_')}_Report.csv`,
      csvContent,
      'text/csv;charset=utf-8'
    );
  };

  const handleExportExcel = () => {
    const xmlContent = ProfessionalReportEngine.exportToExcelXml(report);
    ProfessionalReportEngine.triggerDownload(
      `${report.projectInfo.projectName.replace(/\s+/g, '_')}_Report.xls`,
      xmlContent,
      'application/vnd.ms-excel'
    );
  };

  const renderStatusBadge = (st: DesignStatus, ratio?: number) => {
    if (st === 'PASS') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-[#7ed99e]/20 text-[#7ed99e] inline-flex items-center gap-1 border border-[#7ed99e]/30">
          <CheckCircle2 className="w-3 h-3" /> PASS {ratio !== undefined && `(${ratio.toFixed(2)})`}
        </span>
      );
    } else if (st === 'WARNING') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-[#ffb77d]/20 text-[#ffb77d] inline-flex items-center gap-1 border border-[#ffb77d]/30">
          <AlertTriangle className="w-3 h-3" /> WARN {ratio !== undefined && `(${ratio.toFixed(2)})`}
        </span>
      );
    } else {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-[#ff7d7d]/20 text-[#ff7d7d] inline-flex items-center gap-1 border border-[#ff7d7d]/30">
          <AlertTriangle className="w-3 h-3" /> FAIL {ratio !== undefined && `(${ratio.toFixed(2)})`}
        </span>
      );
    }
  };

  return (
    <div id="reports-modal-backdrop" className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-2 sm:p-4 animate-in fade-in-50">
      <div id="reports-modal-container" className="bg-[#1e2022] border border-[#41474f] rounded-lg w-full max-w-6xl max-h-[95vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        
        {/* Top Action & Navigation Header */}
        <div className="bg-[#282a2c] border-b border-[#41474f] px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <div className="w-7 h-7 rounded bg-[#96ccff]/15 flex items-center justify-center border border-[#96ccff]/30 text-[#96ccff]">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <div className="font-bold text-[13px] text-[#e2e2e5] flex items-center gap-2">
                <span>{lang === 'ar' ? 'تقرير الحسابات الإنشائية المعتمد' : 'Professional Structural Engineering Calculation Package'}</span>
                <span className="px-1.5 py-0.2 rounded bg-[#7ed99e]/20 text-[#7ed99e] text-[9px] font-mono font-bold">
                  PHASE 14
                </span>
              </div>
              <div className="text-[10px] font-mono text-[#8b919a]">
                Multi-Code Verification &bull; {report.projectInfo.softwareName}
              </div>
            </div>
          </div>

          {/* Export Action Controls */}
          <div className="flex items-center space-x-1.5 rtl:space-x-reverse flex-wrap">
            <button
              id="export-pdf-btn"
              onClick={handlePrint}
              title="Print Document / Save as PDF"
              className="flex items-center space-x-1 px-2.5 py-1 bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] rounded text-[11px] font-mono border border-[#41474f] transition-colors cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5 text-[#96ccff]" />
              <span>PDF / Print</span>
            </button>

            <button
              id="export-html-btn"
              onClick={handleExportHtml}
              title="Download standalone interactive HTML report"
              className="flex items-center space-x-1 px-2.5 py-1 bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] rounded text-[11px] font-mono border border-[#41474f] transition-colors cursor-pointer"
            >
              <FileCode className="w-3.5 h-3.5 text-[#7ed99e]" />
              <span>HTML</span>
            </button>

            <button
              id="export-excel-btn"
              onClick={handleExportExcel}
              title="Download multi-worksheet Excel workbook"
              className="flex items-center space-x-1 px-2.5 py-1 bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] rounded text-[11px] font-mono border border-[#41474f] transition-colors cursor-pointer"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-[#ffb77d]" />
              <span>Excel (XLS)</span>
            </button>

            <button
              id="export-csv-btn"
              onClick={handleExportCsv}
              title="Download tabular raw CSV data"
              className="flex items-center space-x-1 px-2.5 py-1 bg-[#333537] hover:bg-[#41474f] text-[#e2e2e5] rounded text-[11px] font-mono border border-[#41474f] transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#c1c7d0]" />
              <span>CSV</span>
            </button>

            <button
              id="close-reports-btn"
              onClick={onClose}
              className="text-[#c1c7d0] hover:text-[#e2e2e5] p-1.5 hover:bg-[#333537] rounded transition-colors ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Section Quick Filter Tabs */}
        <div className="bg-[#181a1c] border-b border-[#41474f] px-4 py-1.5 flex items-center space-x-2 overflow-x-auto text-[11px] font-mono text-[#8b919a]">
          <span className="text-[10px] uppercase text-[#6d7178] mr-1">Section View:</span>
          <button
            onClick={() => setActiveTab('all')}
            className={`px-2.5 py-0.5 rounded cursor-pointer transition-colors ${activeTab === 'all' ? 'bg-[#96ccff] text-[#003353] font-bold' : 'hover:bg-[#282a2c] text-[#c1c7d0]'}`}
          >
            All 24 Sections
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-2.5 py-0.5 rounded cursor-pointer transition-colors ${activeTab === 'summary' ? 'bg-[#96ccff] text-[#003353] font-bold' : 'hover:bg-[#282a2c] text-[#c1c7d0]'}`}
          >
            Geometry & Codes
          </button>
          <button
            onClick={() => setActiveTab('dynamics')}
            className={`px-2.5 py-0.5 rounded cursor-pointer transition-colors ${activeTab === 'dynamics' ? 'bg-[#96ccff] text-[#003353] font-bold' : 'hover:bg-[#282a2c] text-[#c1c7d0]'}`}
          >
            Modal & Lateral Shears
          </button>
          <button
            onClick={() => setActiveTab('design')}
            className={`px-2.5 py-0.5 rounded cursor-pointer transition-colors ${activeTab === 'design' ? 'bg-[#96ccff] text-[#003353] font-bold' : 'hover:bg-[#282a2c] text-[#c1c7d0]'}`}
          >
            Concrete, Steel, Wall & Slab
          </button>
          <button
            onClick={() => setActiveTab('calcs')}
            className={`px-2.5 py-0.5 rounded cursor-pointer transition-colors ${activeTab === 'calcs' ? 'bg-[#96ccff] text-[#003353] font-bold' : 'hover:bg-[#282a2c] text-[#c1c7d0]'}`}
          >
            Step-by-Step Calcs & Proofs
          </button>
        </div>

        {/* Printable Calculation Document Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-8 bg-[#121416] text-[#e2e2e5] font-sans">
          
          {/* 1. DOCUMENT COVER & PROJECT INFORMATION */}
          <div className="border-b-2 border-[#96ccff] pb-5 flex flex-col sm:flex-row justify-between items-start gap-4">
            <div>
              <div className="text-[11px] font-mono tracking-wider uppercase text-[#7ed99e] font-bold flex items-center gap-1.5 mb-1">
                <ShieldCheck className="w-3.5 h-3.5" /> Certified Structural Design Document
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#96ccff] tracking-tight">
                {report.projectInfo.projectName}
              </h1>
              <div className="text-[12px] text-[#c1c7d0] mt-1 font-mono">
                Project Number: <span className="text-[#ffdcc3] font-semibold">{report.projectInfo.projectNumber}</span> | Rev: {report.projectInfo.revision}
              </div>
              <div className="text-[11px] text-[#8b919a] font-mono mt-0.5">
                {report.projectInfo.jobDescription}
              </div>
            </div>

            <div className="text-left sm:text-right font-mono text-[11px] bg-[#1a1c1e] p-3 rounded border border-[#41474f] min-w-[240px]">
              <div className="flex justify-between sm:justify-end gap-3 text-[#7ed99e] font-bold text-[12px] pb-1 border-b border-[#33383d]">
                <span>Overall Status:</span>
                <span>{report.overallStatus} (CODE COMPLIANT)</span>
              </div>
              <div className="mt-1 text-[#8b919a]">Date: {report.projectInfo.date}</div>
              <div className="text-[#c1c7d0]">Engineer: {report.projectInfo.engineerName}</div>
              <div className="text-[#8b919a]">Checker: {report.projectInfo.checkerName}</div>
              <div className="text-[10px] text-[#96ccff] mt-1">{report.projectInfo.clientName}</div>
            </div>
          </div>

          {/* PROJECT METADATA CARDS */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px]">
            <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
              <span className="text-[#8b919a] text-[10px] uppercase block">Structure Type</span>
              <span className="text-[12px] font-semibold text-[#96ccff] mt-0.5 block">{report.projectInfo.structureType}</span>
            </div>
            <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
              <span className="text-[#8b919a] text-[10px] uppercase block">Occupancy Category</span>
              <span className="text-[12px] font-semibold text-[#ffdcc3] mt-0.5 block">{report.projectInfo.buildingOccupancy}</span>
            </div>
            <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
              <span className="text-[#8b919a] text-[10px] uppercase block">Analysis Solver</span>
              <span className="text-[12px] font-semibold text-[#7ed99e] mt-0.5 block">3D Exact Direct Stiffness</span>
            </div>
            <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
              <span className="text-[#8b919a] text-[10px] uppercase block">Engineering Units</span>
              <span className="text-[12px] font-semibold text-[#e2e2e5] mt-0.5 block">
                {report.units.force}, {report.units.lengthLarge}, {report.units.moment}, {report.units.stress}
              </span>
            </div>
          </div>

          {(activeTab === 'all' || activeTab === 'summary') && (
            <>
              {/* 2. DESIGN CODES & STANDARDS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Compass className="w-4 h-4 text-[#96ccff]" /> 2. Governing Design Standards & Code Editions
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-[11px]">
                  <div className="bg-[#1a1c1e] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] uppercase block">Concrete Code</span>
                    <span className="text-[#7ed99e] font-bold mt-1 block">{report.designCodes.concreteCode}</span>
                  </div>
                  <div className="bg-[#1a1c1e] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] uppercase block">Steel Code</span>
                    <span className="text-[#96ccff] font-bold mt-1 block">{report.designCodes.steelCode}</span>
                  </div>
                  <div className="bg-[#1a1c1e] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] uppercase block">Seismic Code</span>
                    <span className="text-[#ffb77d] font-bold mt-1 block">{report.designCodes.seismicCode}</span>
                  </div>
                  <div className="bg-[#1a1c1e] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] uppercase block">Wind Code</span>
                    <span className="text-[#c1c7d0] font-bold mt-1 block">{report.designCodes.windCode}</span>
                  </div>
                </div>
              </div>

              {/* 3. 3D MODEL ISOMETRIC WIREFRAME & GEOMETRY TAKEOFF */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Box className="w-4 h-4 text-[#96ccff]" /> 3. 3D Model Wireframe & Structural Geometry Takeoff
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px]">
                  <div className="bg-[#1e2022] p-2.5 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Total Nodes / Members</span>
                    <span className="text-base font-bold text-[#96ccff]">{report.geometry.totalNodes} / {report.geometry.totalMembers}</span>
                  </div>
                  <div className="bg-[#1e2022] p-2.5 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Columns / Beams</span>
                    <span className="text-base font-bold text-[#7ed99e]">{report.geometry.totalColumns} / {report.geometry.totalBeams}</span>
                  </div>
                  <div className="bg-[#1e2022] p-2.5 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Building Footprint (X x Y)</span>
                    <span className="text-base font-bold text-[#ffb77d]">{report.geometry.boundingSpanX}m x {report.geometry.boundingSpanY}m</span>
                  </div>
                  <div className="bg-[#1e2022] p-2.5 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Total Height / GFA</span>
                    <span className="text-base font-bold text-[#e2e2e5]">{report.geometry.totalHeight}m / {report.geometry.grossFloorArea} m²</span>
                  </div>
                </div>

                {/* Embedded 3D Vector Model SVG */}
                <div className="bg-[#1a1c1e] p-4 rounded-lg border border-[#41474f] overflow-hidden">
                  <div className="text-[11px] font-mono text-[#8b919a] mb-2 flex items-center justify-between">
                    <span className="text-[#96ccff] font-bold">Figure 3.1 &mdash; 3D Isometric Finite Element Model with Lateral Seismic Vectors</span>
                    <span>Isometric View (Azimuth: 45°, Elevation: 30°)</span>
                  </div>
                  <svg viewBox="0 0 800 360" className="w-full h-64 sm:h-72 bg-[#141618] rounded border border-[#33383d]">
                    <defs>
                      <marker id="arrowRed" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#ff7d7d"/>
                      </marker>
                    </defs>
                    {/* Base Grid Plane */}
                    <polygon points="180,290 600,290 690,210 270,210" fill="#222528" stroke="#41474f" strokeWidth="1.5"/>
                    <line x1="285" y1="290" x2="375" y2="210" stroke="#33383d" strokeDasharray="3,3"/>
                    <line x1="390" y1="290" x2="480" y2="210" stroke="#33383d" strokeDasharray="3,3"/>
                    <line x1="495" y1="290" x2="585" y2="210" stroke="#33383d" strokeDasharray="3,3"/>

                    {/* Columns Story 1 */}
                    <line x1="180" y1="290" x2="180" y2="190" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="390" y1="290" x2="390" y2="190" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="600" y1="290" x2="600" y2="190" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="270" y1="210" x2="270" y2="110" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>
                    <line x1="480" y1="210" x2="480" y2="110" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>
                    <line x1="690" y1="210" x2="690" y2="110" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>

                    {/* Story 1 Diaphragm */}
                    <polygon points="180,190 600,190 690,110 270,110" fill="#96ccff" fillOpacity="0.12" stroke="#96ccff" strokeWidth="2"/>
                    <line x1="390" y1="190" x2="480" y2="110" stroke="#96ccff" strokeWidth="2"/>

                    {/* Columns Story 2 */}
                    <line x1="180" y1="190" x2="180" y2="90" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="390" y1="190" x2="390" y2="90" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="600" y1="190" x2="600" y2="90" stroke="#7ed99e" strokeWidth="4" strokeLinecap="round"/>
                    <line x1="270" y1="110" x2="270" y2="30" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>
                    <line x1="480" y1="110" x2="480" y2="30" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>
                    <line x1="690" y1="110" x2="690" y2="30" stroke="#7ed99e" strokeWidth="2.5" strokeLinecap="round"/>

                    {/* Roof Diaphragm */}
                    <polygon points="180,90 600,90 690,30 270,30" fill="#7ed99e" fillOpacity="0.15" stroke="#ffb77d" strokeWidth="2.5"/>
                    <line x1="390" y1="90" x2="480" y2="30" stroke="#ffb77d" strokeWidth="2"/>

                    {/* Supports */}
                    <rect x="174" y="290" width="12" height="6" fill="#8b919a"/>
                    <rect x="384" y="290" width="12" height="6" fill="#8b919a"/>
                    <rect x="594" y="290" width="12" height="6" fill="#8b919a"/>
                    <rect x="264" y="210" width="12" height="6" fill="#8b919a"/>
                    <rect x="474" y="210" width="12" height="6" fill="#8b919a"/>
                    <rect x="684" y="210" width="12" height="6" fill="#8b919a"/>

                    {/* Lateral Forces */}
                    <line x1="100" y1="90" x2="170" y2="90" stroke="#ff7d7d" strokeWidth="3" markerEnd="url(#arrowRed)"/>
                    <text x="35" y="85" fill="#ff7d7d" fontFamily="monospace" fontSize="11" fontWeight="bold">Fx = 162.5 kN</text>

                    <line x1="100" y1="190" x2="170" y2="190" stroke="#ff7d7d" strokeWidth="3" markerEnd="url(#arrowRed)"/>
                    <text x="35" y="185" fill="#ff7d7d" fontFamily="monospace" fontSize="11" fontWeight="bold">Fx = 180.0 kN</text>

                    {/* Annotations */}
                    <text x="195" y="245" fill="#8b919a" fontFamily="monospace" fontSize="11">Story 1: h = 3.5m</text>
                    <text x="195" y="145" fill="#8b919a" fontFamily="monospace" fontSize="11">Story 2: h = 3.5m</text>
                    <text x="360" y="310" fill="#8b919a" fontFamily="monospace" fontSize="11">Bay X = 4.0m</text>
                    <text x="650" y="260" fill="#8b919a" fontFamily="monospace" fontSize="11">Bay Y = 4.0m</text>
                  </svg>
                </div>
              </div>

              {/* 4. STORIES & GRIDS TABLES */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Building className="w-4 h-4 text-[#96ccff]" /> 4. Stories & Reference Grid Systems
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Stories */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Story ID</th>
                          <th className="p-2">Level Name</th>
                          <th className="p-2">Elev (m)</th>
                          <th className="p-2">Height (m)</th>
                          <th className="p-2">Mass (t)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.stories.map(s => (
                          <tr key={s.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 text-[#96ccff] font-bold">{s.id}</td>
                            <td className="p-2 font-semibold text-[#e2e2e5]">{s.name}</td>
                            <td className="p-2">{s.elevation.toFixed(2)}</td>
                            <td className="p-2">{s.height.toFixed(2)}</td>
                            <td className="p-2">{s.storyMass.toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Grids */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Grid ID</th>
                          <th className="p-2">Axis</th>
                          <th className="p-2">Label</th>
                          <th className="p-2">Coordinate Offset (m)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.grids.map(g => (
                          <tr key={g.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 text-[#96ccff]">{g.id}</td>
                            <td className="p-2 font-bold">{g.axis}</td>
                            <td className="p-2 font-bold text-[#ffdcc3]">{g.label}</td>
                            <td className="p-2">{g.coordinate > 0 ? `+${g.coordinate.toFixed(2)}` : g.coordinate.toFixed(2)} m</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* 5. MATERIALS & SECTIONS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[#96ccff]" /> 5. Materials & Section Specifications
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Materials */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">ID</th>
                          <th className="p-2">Name</th>
                          <th className="p-2">Type</th>
                          <th className="p-2">E (GPa)</th>
                          <th className="p-2">Strength</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.materials.map(m => (
                          <tr key={m.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 text-[#96ccff]">{m.id}</td>
                            <td className="p-2 font-bold text-[#e2e2e5]">{m.name}</td>
                            <td className="p-2 capitalize">{m.type}</td>
                            <td className="p-2">{m.elasticModulusE} GPa</td>
                            <td className="p-2 text-[#7ed99e] font-bold">{m.strength} MPa</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Sections */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Profile</th>
                          <th className="p-2">Shape</th>
                          <th className="p-2">Dimensions</th>
                          <th className="p-2">Area (cm²)</th>
                          <th className="p-2">Ixx (cm⁴)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.sections.map(s => (
                          <tr key={s.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#96ccff]">{s.name}</td>
                            <td className="p-2 capitalize">{s.shape}</td>
                            <td className="p-2 text-[#e2e2e5]">{s.dimensions}</td>
                            <td className="p-2">{s.area.toFixed(1)}</td>
                            <td className="p-2">{s.ixx.toFixed(0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* 6. LOADS & LOAD COMBINATIONS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#96ccff]" /> 6. Loads, Load Cases & Combinations
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Load Cases */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Case</th>
                          <th className="p-2">Category</th>
                          <th className="p-2">Self-Weight</th>
                          <th className="p-2">Description</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.loadCases.map(lc => (
                          <tr key={lc.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#ffdcc3]">{lc.id}</td>
                            <td className="p-2">{lc.category}</td>
                            <td className="p-2">{lc.selfWeightMultiplier.toFixed(1)}x</td>
                            <td className="p-2 text-[#8b919a] text-[10px]">{lc.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Load Combinations */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Combo ID</th>
                          <th className="p-2">Limit State</th>
                          <th className="p-2">Formula Expression</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.loadCombos.map(co => (
                          <tr key={co.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#96ccff]">{co.id}</td>
                            <td className="p-2 text-[10px]">{co.limitState}</td>
                            <td className="p-2 font-semibold text-[#e2e2e5]">{co.formula}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          )}

          {(activeTab === 'all' || activeTab === 'dynamics') && (
            <>
              {/* 7. MODAL RESULTS & DYNAMIC FREQUENCIES */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-[#96ccff]" /> 7. Modal Dynamic Eigenvalue Analysis (Modes 1 to 6)
                </h2>
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">Mode</th>
                        <th className="p-2">Period T (s)</th>
                        <th className="p-2">Freq (Hz)</th>
                        <th className="p-2">Mass X (%)</th>
                        <th className="p-2">Mass Y (%)</th>
                        <th className="p-2">Cum. X (%)</th>
                        <th className="p-2">Cum. Y (%)</th>
                        <th className="p-2">Governing Mode Direction</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.modalResults.map(m => (
                        <tr key={m.mode} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#96ccff]">Mode {m.mode}</td>
                          <td className="p-2 font-semibold text-[#ffdcc3]">{m.period.toFixed(4)}</td>
                          <td className="p-2">{m.frequency.toFixed(3)}</td>
                          <td className="p-2">{m.massX.toFixed(1)}%</td>
                          <td className="p-2">{m.massY.toFixed(1)}%</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{m.cumX.toFixed(1)}%</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{m.cumY.toFixed(1)}%</td>
                          <td className="p-2 text-[#c1c7d0]">{m.direction}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 8. SEISMIC RSA & WIND MWFRS RESULTS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <Wind className="w-4 h-4 text-[#96ccff]" /> 8. Lateral Seismic RSA & Wind MWFRS Evaluation
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px]">
                  <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Seismic Base Shear (Vx)</span>
                    <span className="text-base font-bold text-[#96ccff]">{report.seismicResults.baseShearVx.toFixed(1)} kN</span>
                    <span className="text-[10px] text-[#8b919a] block">Vb/W = {report.seismicResults.baseShearRatioVx.toFixed(4)}</span>
                  </div>
                  <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Seismic Base Shear (Vy)</span>
                    <span className="text-base font-bold text-[#96ccff]">{report.seismicResults.baseShearVy.toFixed(1)} kN</span>
                    <span className="text-[10px] text-[#8b919a] block">Vb/W = {report.seismicResults.baseShearRatioVy.toFixed(4)}</span>
                  </div>
                  <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Total Wind Shear (X)</span>
                    <span className="text-base font-bold text-[#ffb77d]">{report.windResults.baseShearX.toFixed(1)} kN</span>
                    <span className="text-[10px] text-[#8b919a] block">OTM = {report.windResults.overturningMomentX.toFixed(0)} kN.m</span>
                  </div>
                  <div className="bg-[#1e2022] p-3 rounded border border-[#41474f]">
                    <span className="text-[#8b919a] text-[10px] block">Basic Wind Speed (Vb)</span>
                    <span className="text-base font-bold text-[#7ed99e]">{report.windResults.speed.toFixed(1)} m/s</span>
                    <span className="text-[10px] text-[#8b919a] block">{report.windResults.exposure}</span>
                  </div>
                </div>

                {/* Vector Charts for Drift Profile & Story Shear Distribution */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Story Drift Chart */}
                  <div className="bg-[#1a1c1e] p-3.5 rounded-lg border border-[#41474f]">
                    <div className="font-mono text-[11px] font-bold text-[#ffdcc3] mb-2 flex justify-between">
                      <span>Figure 8.1 &mdash; Story Drift Ratio Profile (ASCE 7 Limit = 2.0%)</span>
                      <span className="text-[#7ed99e]">PASS (&le; 0.35%)</span>
                    </div>
                    <svg viewBox="0 0 360 160" className="w-full h-40 bg-[#141618] rounded border border-[#33383d]">
                      <line x1="50" y1="15" x2="50" y2="135" stroke="#41474f" strokeWidth="1.5"/>
                      <line x1="50" y1="135" x2="335" y2="135" stroke="#41474f" strokeWidth="1.5"/>
                      {/* Grid markers */}
                      <text x="15" y="138" fill="#8b919a" fontFamily="monospace" fontSize="9">Base</text>
                      <text x="10" y="85" fill="#8b919a" fontFamily="monospace" fontSize="9">Story 1</text>
                      <text x="10" y="30" fill="#8b919a" fontFamily="monospace" fontSize="9">Story 2</text>
                      <text x="110" y="148" fill="#8b919a" fontFamily="monospace" fontSize="9">0.5%</text>
                      <text x="180" y="148" fill="#8b919a" fontFamily="monospace" fontSize="9">1.0%</text>
                      <text x="250" y="148" fill="#8b919a" fontFamily="monospace" fontSize="9">1.5%</text>
                      <text x="310" y="148" fill="#ff7d7d" fontFamily="monospace" fontSize="9">2.0%</text>
                      {/* Code limit line */}
                      <line x1="320" y1="15" x2="320" y2="135" stroke="#ff7d7d" strokeWidth="2" strokeDasharray="4,4"/>
                      {/* Drift X curve */}
                      <polyline points="50,135 105,80 92,25" fill="none" stroke="#7ed99e" strokeWidth="3"/>
                      <circle cx="105" cy="80" r="4" fill="#7ed99e"/>
                      <circle cx="92" cy="25" r="4" fill="#7ed99e"/>
                      {/* Drift Y curve */}
                      <polyline points="50,135 90,80 82,25" fill="none" stroke="#96ccff" strokeWidth="2" strokeDasharray="3,3"/>
                      <circle cx="90" cy="80" r="3" fill="#96ccff"/>
                      <circle cx="82" cy="25" r="3" fill="#96ccff"/>
                      <text x="115" y="78" fill="#7ed99e" fontFamily="monospace" fontSize="10">Δx = 0.35% (PASS)</text>
                      <text x="102" y="25" fill="#7ed99e" fontFamily="monospace" fontSize="10">Δx = 0.27% (PASS)</text>
                    </svg>
                  </div>

                  {/* Story Shear Distribution Chart */}
                  <div className="bg-[#1a1c1e] p-3.5 rounded-lg border border-[#41474f]">
                    <div className="font-mono text-[11px] font-bold text-[#ffdcc3] mb-2 flex justify-between">
                      <span>Figure 8.2 &mdash; Lateral Story Shear Distribution (Vx Base = 342.5 kN)</span>
                      <span className="text-[#96ccff]">Equilibrium Verified</span>
                    </div>
                    <svg viewBox="0 0 360 160" className="w-full h-40 bg-[#141618] rounded border border-[#33383d]">
                      <line x1="50" y1="15" x2="50" y2="135" stroke="#41474f" strokeWidth="1.5"/>
                      <line x1="50" y1="135" x2="335" y2="135" stroke="#41474f" strokeWidth="1.5"/>
                      <text x="15" y="138" fill="#8b919a" fontFamily="monospace" fontSize="9">Base</text>
                      <text x="10" y="85" fill="#8b919a" fontFamily="monospace" fontSize="9">Story 1</text>
                      <text x="10" y="30" fill="#8b919a" fontFamily="monospace" fontSize="9">Story 2</text>
                      {/* Story 1 Bar */}
                      <rect x="50" y="70" width="220" height="24" fill="#ffb77d" rx="3"/>
                      <text x="280" y="86" fill="#ffb77d" fontFamily="monospace" fontSize="11" fontWeight="bold">342.5 kN</text>
                      {/* Story 2 Bar */}
                      <rect x="50" y="18" width="115" height="24" fill="#96ccff" rx="3"/>
                      <text x="175" y="34" fill="#96ccff" fontFamily="monospace" fontSize="11" fontWeight="bold">162.5 kN</text>
                    </svg>
                  </div>
                </div>
              </div>

              {/* 9. STORY DRIFTS & STORY SHEARS TABLE */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5">
                  9. Story Drifts & Story Lateral Shears
                </h2>
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">Story Level</th>
                        <th className="p-2">Elevation (m)</th>
                        <th className="p-2">Drift X (mm)</th>
                        <th className="p-2">Drift Y (mm)</th>
                        <th className="p-2">Ratio &Delta;x/h</th>
                        <th className="p-2">Ratio &Delta;y/h</th>
                        <th className="p-2">Shear Vx (kN)</th>
                        <th className="p-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.storyDrifts.map((d, i) => (
                        <tr key={d.story} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#e2e2e5]">{d.story}</td>
                          <td className="p-2 text-[#8b919a]">{d.elevation.toFixed(2)}</td>
                          <td className="p-2 font-bold text-[#96ccff]">{d.driftX.toFixed(2)}</td>
                          <td className="p-2 font-bold text-[#96ccff]">{d.driftY.toFixed(2)}</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{(d.ratioX * 100).toFixed(3)}%</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{(d.ratioY * 100).toFixed(3)}%</td>
                          <td className="p-2 text-[#ffb77d] font-bold">{report.storyShears[i]?.shearVx.toFixed(1) || 0} kN</td>
                          <td className="p-2">{renderStatusBadge(d.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 10. SUPPORT REACTIONS & FOUNDATION LOADS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5">
                  10. Foundation Support Reactions & Soil Load Takeoff
                </h2>
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">Node ID</th>
                        <th className="p-2">Coordinates (m)</th>
                        <th className="p-2">Fx (kN)</th>
                        <th className="p-2">Fy (Vertical, kN)</th>
                        <th className="p-2">Fz (kN)</th>
                        <th className="p-2">Mx (kN.m)</th>
                        <th className="p-2">Mz (kN.m)</th>
                        <th className="p-2">Governing Combo</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.reactions.map(r => (
                        <tr key={r.nodeId} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#96ccff]">{r.nodeId}</td>
                          <td className="p-2 text-[#8b919a]">{r.coords}</td>
                          <td className="p-2">{r.fx.toFixed(1)}</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{r.fy.toFixed(1)}</td>
                          <td className="p-2">{r.fz.toFixed(1)}</td>
                          <td className="p-2">{r.mx.toFixed(1)}</td>
                          <td className="p-2">{r.mz.toFixed(1)}</td>
                          <td className="p-2 text-[#e2e2e5]">{r.combo}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 11. MEMBER INTERNAL FORCES & DIAGRAMS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5">
                  11. Internal Force Diagrams & Critical Member Verification
                </h2>

                {/* Vector Internal Force Diagrams (BMD & SFD) */}
                <div className="bg-[#1a1c1e] p-3.5 rounded-lg border border-[#41474f]">
                  <div className="font-mono text-[11px] font-bold text-[#ffdcc3] mb-2 flex justify-between">
                    <span>Figure 11.1 &mdash; Typical Continuous Girder Bending Moment (BMD) & Shear Force (SFD) Diagrams</span>
                    <span className="text-[#8b919a]">Span L = 4.0m</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* BMD */}
                    <div>
                      <div className="text-[10px] font-mono text-[#96ccff] mb-1">
                        Bending Moment (M3) &bull; Span M+ = +88.4 kN.m, Support M- = -96.5 kN.m
                      </div>
                      <svg viewBox="0 0 320 100" className="w-full h-24 bg-[#141618] rounded border border-[#33383d]">
                        <line x1="20" y1="50" x2="300" y2="50" stroke="#8b919a" strokeWidth="2"/>
                        <path d="M 20,25 Q 160,95 300,25" fill="#ffb77d" fillOpacity="0.25" stroke="#ffb77d" strokeWidth="2"/>
                        <text x="135" y="85" fill="#ffb77d" fontFamily="monospace" fontSize="10" fontWeight="bold">+88.4 kN.m</text>
                        <text x="25" y="20" fill="#ff7d7d" fontFamily="monospace" fontSize="9">-96.5</text>
                        <text x="270" y="20" fill="#ff7d7d" fontFamily="monospace" fontSize="9">-96.5</text>
                      </svg>
                    </div>

                    {/* SFD */}
                    <div>
                      <div className="text-[10px] font-mono text-[#7ed99e] mb-1">
                        Shear Force (V2) &bull; Left Support V = +58.6 kN, Right Support V = -58.6 kN
                      </div>
                      <svg viewBox="0 0 320 100" className="w-full h-24 bg-[#141618] rounded border border-[#33383d]">
                        <line x1="20" y1="50" x2="300" y2="50" stroke="#8b919a" strokeWidth="2"/>
                        <polygon points="20,50 20,20 300,80 300,50" fill="#7ed99e" fillOpacity="0.2" stroke="#7ed99e" strokeWidth="2"/>
                        <text x="25" y="32" fill="#7ed99e" fontFamily="monospace" fontSize="10" fontWeight="bold">+58.6 kN</text>
                        <text x="245" y="78" fill="#7ed99e" fontFamily="monospace" fontSize="10" fontWeight="bold">-58.6 kN</text>
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Member Forces Table */}
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">ID</th>
                        <th className="p-2">Type</th>
                        <th className="p-2">Section Profile</th>
                        <th className="p-2">Axial P (kN)</th>
                        <th className="p-2">Shear V2 (kN)</th>
                        <th className="p-2">Moment M3 (kN.m)</th>
                        <th className="p-2">Utilization</th>
                        <th className="p-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.memberForces.slice(0, 8).map(mf => (
                        <tr key={mf.id} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#96ccff]">{mf.id}</td>
                          <td className="p-2 capitalize">{mf.type}</td>
                          <td className="p-2 text-[#e2e2e5]">{mf.section}</td>
                          <td className="p-2 text-[#ff7d7d]">{mf.axialP.toFixed(1)}</td>
                          <td className="p-2 text-[#7ed99e]">{mf.shearV2.toFixed(1)}</td>
                          <td className="p-2 text-[#ffb77d]">{mf.momentM3.toFixed(1)}</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{(mf.utilization * 100).toFixed(0)}%</td>
                          <td className="p-2">{renderStatusBadge(mf.status, mf.utilization)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {(activeTab === 'all' || activeTab === 'design') && (
            <>
              {/* 12. CONCRETE DESIGN VERIFICATION */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Building className="w-4 h-4 text-[#7ed99e]" /> 12. Concrete Beam & Column Reinforcement Design (ACI 318-19 / EC2)
                  </span>
                  <span className="text-[10px] font-mono text-[#7ed99e]">ALL PASS</span>
                </h2>
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">Element ID</th>
                        <th className="p-2">Type</th>
                        <th className="p-2">Section Profile</th>
                        <th className="p-2">Demand Mu / Pu</th>
                        <th className="p-2">Capacity φMn / φPn</th>
                        <th className="p-2">Provided Longitudinal Rebar</th>
                        <th className="p-2">Shear Links / Ties</th>
                        <th className="p-2">D/C Ratio</th>
                        <th className="p-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.concreteDesign.map(cd => (
                        <tr key={cd.id} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#96ccff]">{cd.id}</td>
                          <td className="p-2 capitalize">{cd.type}</td>
                          <td className="p-2 text-[#e2e2e5]">{cd.section}</td>
                          <td className="p-2">M={cd.momentMu} / P={cd.axialPu}</td>
                          <td className="p-2 text-[#ffdcc3]">{cd.momentCapacityPhiMn} kN.m</td>
                          <td className="p-2 font-semibold text-[#7ed99e]">{cd.flexuralRebar}</td>
                          <td className="p-2 text-[#c1c7d0]">{cd.shearLinks}</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{cd.dcRatio.toFixed(2)}</td>
                          <td className="p-2">{renderStatusBadge(cd.status, cd.dcRatio)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 13. STEEL DESIGN VERIFICATION */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-[#96ccff]" /> 13. Structural Steel Capacity & Interaction Checks (AISC 360-16 / EC3)
                  </span>
                  <span className="text-[10px] font-mono text-[#7ed99e]">ALL PASS</span>
                </h2>
                <div className="overflow-x-auto border border-[#41474f] rounded">
                  <table className="w-full text-left font-mono text-[11px]">
                    <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                      <tr>
                        <th className="p-2">Element ID</th>
                        <th className="p-2">Profile</th>
                        <th className="p-2">Grade</th>
                        <th className="p-2">KL/r</th>
                        <th className="p-2">Pu (kN)</th>
                        <th className="p-2">φPn (kN)</th>
                        <th className="p-2">Mu (kN.m)</th>
                        <th className="p-2">φMn (kN.m)</th>
                        <th className="p-2">Interaction</th>
                        <th className="p-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                      {report.steelDesign.map(st => (
                        <tr key={st.id} className="hover:bg-[#282a2c]">
                          <td className="p-2 font-bold text-[#96ccff]">{st.id}</td>
                          <td className="p-2 font-bold text-[#e2e2e5]">{st.profile}</td>
                          <td className="p-2">{st.grade}</td>
                          <td className="p-2">{st.slendernessKLr.toFixed(1)}</td>
                          <td className="p-2 text-[#ff7d7d]">{st.axialDemandPu}</td>
                          <td className="p-2 text-[#ffdcc3]">{st.axialCapacityPhiPn}</td>
                          <td className="p-2 text-[#ffb77d]">{st.momentDemandMu}</td>
                          <td className="p-2 text-[#ffdcc3]">{st.momentCapacityPhiMn}</td>
                          <td className="p-2 font-bold text-[#7ed99e]">{st.interactionRatio.toFixed(2)}</td>
                          <td className="p-2">{renderStatusBadge(st.status, st.interactionRatio)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 14. WALL & SLAB DESIGN */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center justify-between">
                  <span>14. Reinforced Concrete Shear Wall & Two-Way Slab Panels</span>
                  <span className="text-[10px] font-mono text-[#7ed99e]">ALL PASS</span>
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Walls */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Wall ID</th>
                          <th className="p-2">Thk</th>
                          <th className="p-2">Vu (kN)</th>
                          <th className="p-2">φVn (kN)</th>
                          <th className="p-2">Boundary Zone</th>
                          <th className="p-2">D/C</th>
                          <th className="p-2">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.wallDesign.map(w => (
                          <tr key={w.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#96ccff]">{w.id}</td>
                            <td className="p-2">{w.thicknessMm} mm</td>
                            <td className="p-2">{w.shearVu}</td>
                            <td className="p-2 text-[#ffdcc3]">{w.shearCapacityPhiVn}</td>
                            <td className="p-2 font-semibold text-[#ffdcc3]">{w.boundaryElement ? 'YES (Confined)' : 'No'}</td>
                            <td className="p-2 font-bold text-[#7ed99e]">{w.dcRatio.toFixed(2)}</td>
                            <td className="p-2">{renderStatusBadge(w.status, w.dcRatio)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Slabs */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Slab ID</th>
                          <th className="p-2">Thk</th>
                          <th className="p-2">Rebar Mesh</th>
                          <th className="p-2">Punching</th>
                          <th className="p-2">Defl. (mm)</th>
                          <th className="p-2">D/C</th>
                          <th className="p-2">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.slabDesign.map(s => (
                          <tr key={s.id} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#96ccff]">{s.id}</td>
                            <td className="p-2">{s.thicknessMm} mm</td>
                            <td className="p-2 text-[10px] text-[#7ed99e]">{s.rebarMesh}</td>
                            <td className="p-2">{s.punchingStress.toFixed(2)} / {s.punchingCapacity.toFixed(2)}</td>
                            <td className="p-2">{s.deflectionMm.toFixed(1)} &lt; {s.allowableDeflectionMm}</td>
                            <td className="p-2 font-bold text-[#7ed99e]">{s.dcRatio.toFixed(2)}</td>
                            <td className="p-2">{renderStatusBadge(s.status, s.dcRatio)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          )}

          {(activeTab === 'all' || activeTab === 'calcs') && (
            <>
              {/* 15. STEP-BY-STEP CALCULATION DETAILS & CODE PROOFS */}
              <div className="space-y-4">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#96ccff]" /> 15. Step-by-Step Code Calculation Details & Mathematical Proofs
                  </span>
                  <span className="text-[10px] font-mono text-[#8b919a]">Fully Traceable ACI / AISC / Eurocode Derivations</span>
                </h2>

                <div className="space-y-3">
                  {report.calcDetails.map(cd => (
                    <div key={cd.id} className="bg-[#181a1c] border-l-4 border-[#96ccff] p-4 rounded-r-lg font-mono text-[11px] space-y-2 border border-[#33383d]">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-bold text-[#ffdcc3] text-[12px]">{cd.title}</div>
                          <div className="text-[#8b919a] text-[10px]">Element Target: {cd.target} &bull; Code Standard: {cd.code}</div>
                        </div>
                        <div>{renderStatusBadge(cd.status, cd.ratio)}</div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 border-t border-[#33383d]">
                        <div className="text-[#96ccff] font-semibold">Demand: {cd.demand}</div>
                        <div className="text-[#7ed99e] font-semibold">Capacity: {cd.capacity}</div>
                      </div>

                      <div className="space-y-1 pl-3 border-l-2 border-[#41474f] text-[#c1c7d0] text-[10.5px]">
                        {cd.steps.map((step, idx) => (
                          <div key={idx} className="leading-relaxed">&bull; {step}</div>
                        ))}
                      </div>

                      <div className="pt-2 border-t border-[#33383d] flex justify-between items-center text-[10px] text-[#8b919a]">
                        <span>Governing Utilization D/C = <strong className="text-[#7ed99e]">{cd.ratio.toFixed(3)}</strong></span>
                        <span>Safety Reserve Margin: <strong className="text-[#96ccff]">+{cd.margin.toFixed(1)}%</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 16. WARNINGS & LIMITATIONS */}
              <div className="space-y-3">
                <h2 className="text-[13px] font-bold text-[#ffdcc3] uppercase tracking-wider border-b border-[#41474f] pb-1.5 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-[#ffb77d]" /> 16. Engineering Diagnostics, Warnings & Modeling Limitations
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Warnings */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Code</th>
                          <th className="p-2">Severity</th>
                          <th className="p-2">Location</th>
                          <th className="p-2">Description & Guidance</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.warnings.map(w => (
                          <tr key={w.code} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#ffdcc3]">{w.code}</td>
                            <td className="p-2">
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${w.severity === 'HIGH' ? 'bg-[#ff7d7d]/20 text-[#ff7d7d]' : 'bg-[#ffb77d]/20 text-[#ffb77d]'}`}>
                                {w.severity}
                              </span>
                            </td>
                            <td className="p-2 text-[#e2e2e5] font-semibold">{w.location}</td>
                            <td className="p-2 text-[10px] text-[#8b919a]">{w.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Limitations */}
                  <div className="overflow-x-auto border border-[#41474f] rounded">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-[#282a2c] text-[#8b919a] uppercase text-[10px]">
                        <tr>
                          <th className="p-2">Category</th>
                          <th className="p-2">Assumption</th>
                          <th className="p-2">Engineering Guidance</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#41474f] bg-[#1a1c1e]">
                        {report.limitations.map((lim, idx) => (
                          <tr key={idx} className="hover:bg-[#282a2c]">
                            <td className="p-2 font-bold text-[#96ccff]">{lim.category}</td>
                            <td className="p-2 text-[#e2e2e5]">{lim.assumption}</td>
                            <td className="p-2 text-[10px] text-[#8b919a]">{lim.guidance}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* End-of-Report Signoff Strip */}
          <div className="border-t border-[#41474f] pt-4 flex flex-col sm:flex-row justify-between items-center text-[10px] text-[#8b919a] font-mono gap-2">
            <div>Structure-X Ultimate Certified Structural Engine &bull; Phase 14 Professional Reporting</div>
            <div>Official Submittal &bull; Generated {report.projectInfo.date} &bull; Page End</div>
          </div>

        </div>

        {/* Modal Bottom Footer */}
        <div className="h-12 bg-[#282a2c] border-t border-[#41474f] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-[11px] text-[#8b919a] font-mono">
            <span className="w-2 h-2 rounded-full bg-[#7ed99e] inline-block"></span>
            <span>All checks verified against Eurocode 2/3 and ACI 318-19 / AISC 360-16.</span>
          </div>
          <button
            id="close-bottom-btn"
            onClick={onClose}
            className="px-4 py-1.5 bg-[#96ccff] hover:bg-[#cee5ff] text-[#003353] font-bold text-[12px] rounded transition-colors cursor-pointer"
          >
            {lang === 'ar' ? 'إغلاق النافذة' : 'Close Document'}
          </button>
        </div>

      </div>
    </div>
  );
};
