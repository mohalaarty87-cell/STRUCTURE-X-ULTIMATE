import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Layers,
  ArrowRight,
  Database,
  Download,
  Settings2,
  Eye,
  FileSpreadsheet,
  Box,
  RefreshCw,
  Sparkles,
  Info
} from 'lucide-react';
import { StructuralModel } from '../types/structure';
import {
  InteropFormat,
  MergeStrategy,
  ValidationSummary,
  ImportPreviewSummary,
  MappingConfig
} from '../core/interop/CadBimTypes';
import { CadBimInteropEngine } from '../core/interop/CadBimInteropEngine';

interface CadBimModalProps {
  currentModel: StructuralModel;
  onCommitModel: (newModel: StructuralModel, actionDescription: string) => void;
  onClose: () => void;
  lang: 'en' | 'ar';
}

type WizardStep = 'import' | 'validation' | 'preview' | 'mapping' | 'confirm' | 'export';

export const CadBimModal: React.FC<CadBimModalProps> = ({
  currentModel,
  onCommitModel,
  onClose,
  lang
}) => {
  const [activeStep, setActiveStep] = useState<WizardStep>('import');
  const [selectedFormat, setSelectedFormat] = useState<InteropFormat>('IFC');
  const [fileName, setFileName] = useState<string>('');
  const [fileContent, setFileContent] = useState<string>('');
  const [parsedData, setParsedData] = useState<Partial<StructuralModel> | null>(null);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);
  const [preview, setPreview] = useState<ImportPreviewSummary | null>(null);

  // Mapping configurations
  const [scaleFactor, setScaleFactor] = useState<number>(1.0);
  const [swapYZ, setSwapYZ] = useState<boolean>(false);
  const [mergeStrategy, setMergeStrategy] = useState<MergeStrategy>('MERGE_APPEND');
  const [layerMap, setLayerMap] = useState<Record<string, 'column' | 'beam' | 'brace' | 'slab' | 'wall'>>({});

  const [activePreviewSubtab, setActivePreviewSubtab] = useState<'nodes' | 'members' | 'layers' | 'properties'>('nodes');
  const [commitSuccess, setCommitSuccess] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sample models for instant testing
  const loadSampleModel = (format: InteropFormat) => {
    setSelectedFormat(format);
    setFileName(`sample_structure.${format.toLowerCase()}`);
    let content = '';

    if (format === 'IFC') {
      content = CadBimInteropEngine.exportModel(currentModel, 'IFC').content;
    } else if (format === 'DXF') {
      content = CadBimInteropEngine.exportModel(currentModel, 'DXF').content;
    } else if (format === 'CSV') {
      content = CadBimInteropEngine.exportModel(currentModel, 'CSV').content;
    } else if (format === 'EXCEL') {
      content = CadBimInteropEngine.exportModel(currentModel, 'EXCEL').content;
    } else {
      content = JSON.stringify(currentModel, null, 2);
    }

    setFileContent(content);
    processFileContent(content, `sample_structure.${format.toLowerCase()}`, format);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setFileContent(text);
      processFileContent(text, file.name);
    };
    reader.readAsText(file);
  };

  const processFileContent = (content: string, name: string, formatOverride?: InteropFormat) => {
    const res = CadBimInteropEngine.importFile(content, name, formatOverride);
    if (res.success && res.data) {
      setParsedData(res.data);
      setValidation(res.validation || null);
      setPreview(res.preview || null);
      setSelectedFormat(res.formatType);

      // Initialize layer mapping defaults
      const initialLayerMap: Record<string, 'column' | 'beam' | 'brace' | 'slab' | 'wall'> = {};
      res.preview?.layers.forEach(l => {
        initialLayerMap[l.name] = l.detectedType === 'column' ? 'column' :
                                  l.detectedType === 'slab' ? 'slab' : 'beam';
      });
      setLayerMap(initialLayerMap);
      setActiveStep('validation');
    } else {
      alert(`Import error: ${res.message}`);
    }
  };

  const handleApplyMappingAndCommit = () => {
    if (!parsedData) return;

    const mappingConfig: MappingConfig = {
      coordinateTransform: {
        scaleFactor,
        offsetX: 0,
        offsetY: 0,
        offsetZ: 0,
        swapYZ,
        invertZ: false
      },
      layerTypeMap: layerMap,
      materialMap: {},
      sectionMap: {},
      defaultMaterialId: 'MAT-C30',
      defaultSectionId: 'SEC-COL-400X400',
      mergeStrategy,
      toleranceM: 0.001
    };

    const mapped = CadBimInteropEngine.mapData(parsedData, mappingConfig);
    const committed = CadBimInteropEngine.confirmAndCommit(currentModel, mapped, mergeStrategy, 0.001);

    onCommitModel(
      committed,
      `Imported CAD/BIM model '${fileName}' via ${selectedFormat} (${mergeStrategy})`
    );

    setCommitSuccess(true);
    setTimeout(() => {
      onClose();
    }, 1200);
  };

  const handleExport = (format: InteropFormat) => {
    const res = CadBimInteropEngine.exportModel(currentModel, format);
    CadBimInteropEngine.triggerBrowserDownload(res.content, res.filename, res.mimeType);
  };

  const steps: { id: WizardStep; label: string; number: number }[] = [
    { id: 'import', label: lang === 'ar' ? '1. استيراد' : '1. Import', number: 1 },
    { id: 'validation', label: lang === 'ar' ? '2. التحقق' : '2. Validation', number: 2 },
    { id: 'preview', label: lang === 'ar' ? '3. المعاينة' : '3. Preview', number: 3 },
    { id: 'mapping', label: lang === 'ar' ? '4. المطابقة' : '4. Mapping', number: 4 },
    { id: 'confirm', label: lang === 'ar' ? '5. التأكيد' : '5. Confirm', number: 5 },
    { id: 'export', label: lang === 'ar' ? 'تصدير' : 'Export', number: 6 },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in-50 select-none">
      <div className="bg-[#181a1c] border border-[#3e444c] rounded-xl w-full max-w-5xl h-[650px] flex flex-col shadow-2xl overflow-hidden font-sans text-[#e2e2e5]">

        {/* Modal Top Header */}
        <div className="h-12 bg-[#222528] border-b border-[#3e444c] px-5 flex items-center justify-between">
          <div className="flex items-center space-x-3 rtl:space-x-reverse">
            <div className="w-7 h-7 rounded bg-[#96ccff]/10 border border-[#96ccff]/30 flex items-center justify-center text-[#96ccff]">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                <span className="font-semibold text-[14px] text-[#f0f2f5]">
                  {lang === 'ar' ? 'تبادل بيانات CAD و BIM الإنشائية' : 'CAD & BIM Interoperability Engine'}
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono bg-[#96ccff]/15 text-[#96ccff] border border-[#96ccff]/30 rounded">
                  PHASE 13 PRO
                </span>
              </div>
            </div>
          </div>

          {/* Supported format badges */}
          <div className="hidden md:flex items-center space-x-1.5 text-[11px] font-mono text-[#a0a6af]">
            <span className="px-1.5 py-0.5 bg-[#2a2e33] border border-[#444a53] rounded text-[#96ccff]">IFC4</span>
            <span className="px-1.5 py-0.5 bg-[#2a2e33] border border-[#444a53] rounded text-[#7ed99e]">DXF R12/2000</span>
            <span className="px-1.5 py-0.5 bg-[#2a2e33] border border-[#444a53] rounded text-[#f8b449]">CSV</span>
            <span className="px-1.5 py-0.5 bg-[#2a2e33] border border-[#444a53] rounded text-[#4ade80]">Excel</span>
            <span className="px-1.5 py-0.5 bg-[#2a2e33] border border-[#444a53] rounded text-[#c084fc]">JSON</span>
          </div>

          <button
            id="close-cad-bim-modal"
            onClick={onClose}
            className="p-1.5 text-[#a0a6af] hover:text-[#ffffff] hover:bg-[#30353c] rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Wizard Step Navigation Bar */}
        <div className="h-11 bg-[#1c1f22] border-b border-[#3e444c] px-4 flex items-center justify-between">
          <div className="flex items-center space-x-1 rtl:space-x-reverse overflow-x-auto py-1">
            {steps.map((step) => {
              const isActive = activeStep === step.id;
              const isPassed = parsedData && (step.id === 'import' || step.id === 'validation');

              return (
                <button
                  key={step.id}
                  id={`btn-step-${step.id}`}
                  onClick={() => {
                    if (step.id === 'export' || parsedData || step.id === 'import') {
                      setActiveStep(step.id);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-all flex items-center space-x-1.5 rtl:space-x-reverse ${
                    isActive
                      ? 'bg-[#96ccff] text-[#0f1113] shadow font-semibold'
                      : isPassed
                      ? 'text-[#96ccff] hover:bg-[#282d33]'
                      : 'text-[#8c929c] hover:bg-[#25282c]'
                  }`}
                >
                  <span>{step.label}</span>
                </button>
              );
            })}
          </div>

          {preview && (
            <div className="text-[11px] font-mono text-[#96ccff] hidden sm:block">
              {preview.counts.nodes} Nodes | {preview.counts.totalMembers} Members | {preview.counts.slabs} Slabs
            </div>
          )}
        </div>

        {/* Main Content Body */}
        <div className="flex-1 p-6 overflow-y-auto bg-[#181a1c]">

          {/* STEP 1: IMPORT & UPLOAD */}
          {activeStep === 'import' && (
            <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in-30">
              <div>
                <h3 className="text-[16px] font-semibold text-[#f0f2f5]">
                  {lang === 'ar' ? 'استيراد ملف BIM أو CAD إلكتروني' : 'Import BIM, CAD, or Tabular Structural Data'}
                </h3>
                <p className="text-[13px] text-[#9ca3af] mt-1">
                  {lang === 'ar'
                    ? 'يدعم النظام معايير IFC 2x3/4، ملفات AutoCAD DXF ثلاثية الأبعاد، جداول Excel متعددة الصفحات، CSV، و JSON.'
                    : 'Universal parser for Industry Foundation Classes (IFC), AutoCAD 3D DXF, multi-sheet Excel, CSV, and JSON.'}
                </p>
              </div>

              {/* Format selection chips */}
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                {(['IFC', 'DXF', 'CSV', 'EXCEL', 'JSON'] as InteropFormat[]).map((fmt) => (
                  <button
                    key={fmt}
                    id={`format-select-${fmt.toLowerCase()}`}
                    onClick={() => setSelectedFormat(fmt)}
                    className={`px-3 py-1.5 rounded-md text-[12px] font-mono transition-all border ${
                      selectedFormat === fmt
                        ? 'bg-[#96ccff]/20 border-[#96ccff] text-[#96ccff] font-bold'
                        : 'bg-[#22262a] border-[#3e444c] text-[#a0a6af] hover:border-[#525a65]'
                    }`}
                  >
                    {fmt}
                  </button>
                ))}
              </div>

              {/* Dropzone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-[#444a53] hover:border-[#96ccff] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer bg-[#1c2024]/50 hover:bg-[#20252b] transition-all group"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".ifc,.dxf,.csv,.xml,.xlsx,.json,.txt"
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-full bg-[#2a2f36] flex items-center justify-center text-[#96ccff] group-hover:scale-110 transition-transform">
                  <Upload className="w-6 h-6" />
                </div>
                <span className="text-[14px] font-semibold text-[#f0f2f5] mt-3">
                  {lang === 'ar' ? 'اسحب وأفلت الملف هنا أو انقر للاختيار' : 'Click to select or drag and drop your structural file'}
                </span>
                <span className="text-[12px] text-[#8c929c] mt-1">
                  Supports .ifc, .dxf, .csv, .xml (Excel), and .json
                </span>
              </div>

              {/* Quick load sample models */}
              <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-4">
                <div className="flex items-center space-x-2 text-[12px] font-semibold text-[#96ccff] mb-2">
                  <Sparkles className="w-4 h-4" />
                  <span>{lang === 'ar' ? 'أو حمّل نموذجاً تجريبياً فوراً:' : 'Or test immediately with a generated benchmark model:'}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {(['IFC', 'DXF', 'CSV', 'EXCEL', 'JSON'] as InteropFormat[]).map((fmt) => (
                    <button
                      key={`sample-${fmt}`}
                      id={`load-sample-${fmt.toLowerCase()}`}
                      onClick={() => loadSampleModel(fmt)}
                      className="px-3 py-2 bg-[#282d33] hover:bg-[#323840] border border-[#444a53] rounded text-[12px] text-[#e2e2e5] flex items-center justify-center space-x-1.5 transition-colors"
                    >
                      <FileCode className="w-3.5 h-3.5 text-[#96ccff]" />
                      <span>Load {fmt}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: VALIDATION */}
          {activeStep === 'validation' && validation && (
            <div className="space-y-4 max-w-4xl mx-auto animate-in fade-in-30">
              <div className="flex items-center justify-between bg-[#202428] border border-[#3e444c] rounded-lg p-4">
                <div className="flex items-center space-x-3 rtl:space-x-reverse">
                  {validation.isValid ? (
                    <div className="w-9 h-9 rounded-full bg-[#7ed99e]/20 border border-[#7ed99e] flex items-center justify-center text-[#7ed99e]">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  ) : validation.canImport ? (
                    <div className="w-9 h-9 rounded-full bg-[#f8b449]/20 border border-[#f8b449] flex items-center justify-center text-[#f8b449]">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-9 h-9 rounded-full bg-[#f87171]/20 border border-[#f87171] flex items-center justify-center text-[#f87171]">
                      <AlertOctagon className="w-5 h-5" />
                    </div>
                  )}
                  <div>
                    <h4 className="text-[14px] font-semibold text-[#f0f2f5]">
                      {validation.isValid
                        ? 'Validation Passed: Zero Critical Geometric Errors'
                        : `${validation.errorCount} Errors & ${validation.warningCount} Warnings Detected`}
                    </h4>
                    <p className="text-[12px] text-[#9ca3af]">
                      {validation.canImport
                        ? 'The model geometry is topologically viable for automatic mapping and workspace import.'
                        : 'Critical errors must be resolved before structural analysis.'}
                    </p>
                  </div>
                </div>

                <button
                  id="btn-proceed-to-preview"
                  onClick={() => setActiveStep('preview')}
                  className="px-4 py-2 bg-[#96ccff] hover:bg-[#80beff] text-[#0f1113] rounded-md text-[13px] font-semibold flex items-center space-x-1.5 transition-colors shadow"
                >
                  <span>Proceed to Preview</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {/* Validation Issues Table */}
              <div className="bg-[#1e2226] border border-[#3e444c] rounded-lg overflow-hidden">
                <div className="h-9 bg-[#262b30] border-b border-[#3e444c] px-4 flex items-center justify-between text-[12px] font-medium text-[#c1c7d0]">
                  <span>Validation Diagnostic Checks ({validation.totalIssues} events)</span>
                  <span className="font-mono text-[11px] text-[#7ed99e]">Tolerance: 1.0 mm</span>
                </div>
                <div className="max-h-[300px] overflow-y-auto divide-y divide-[#2a3036] text-[12px]">
                  {validation.issues.length === 0 ? (
                    <div className="p-6 text-center text-[#7ed99e] flex flex-col items-center justify-center">
                      <CheckCircle2 className="w-6 h-6 mb-2" />
                      <span>All geometric coordinates, members, and boundaries verified valid!</span>
                    </div>
                  ) : (
                    validation.issues.map((iss, idx) => (
                      <div key={idx} className="p-3 flex items-start space-x-3 rtl:space-x-reverse hover:bg-[#252a30]">
                        {iss.severity === 'ERROR' && <AlertOctagon className="w-4 h-4 text-[#f87171] shrink-0 mt-0.5" />}
                        {iss.severity === 'WARNING' && <AlertTriangle className="w-4 h-4 text-[#f8b449] shrink-0 mt-0.5" />}
                        {iss.severity === 'INFO' && <Info className="w-4 h-4 text-[#96ccff] shrink-0 mt-0.5" />}
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-[11px] text-[#e2e2e5]">{iss.code}</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#30363d] text-[#a0a6af]">
                              {iss.entityType} {iss.entityId ? `[${iss.entityId}]` : ''}
                            </span>
                          </div>
                          <p className="text-[#c1c7d0] mt-0.5">{iss.message}</p>
                          {iss.suggestedFix && (
                            <p className="text-[11px] text-[#7ed99e] mt-1 font-mono">
                              💡 Auto-Fix: {iss.suggestedFix}
                            </p>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: PREVIEW */}
          {activeStep === 'preview' && preview && (
            <div className="space-y-4 max-w-4xl mx-auto animate-in fade-in-30">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-3">
                  <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider font-mono">Bounding Box</span>
                  <div className="text-[14px] font-bold text-[#f0f2f5] mt-1">
                    {preview.boundingBox.spanX.toFixed(1)}m × {preview.boundingBox.spanY.toFixed(1)}m × {preview.boundingBox.spanZ.toFixed(1)}m
                  </div>
                  <div className="text-[10px] text-[#8c929c] font-mono mt-0.5">
                    Z: {preview.boundingBox.minZ.toFixed(1)} to {preview.boundingBox.maxZ.toFixed(1)}m
                  </div>
                </div>

                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-3">
                  <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider font-mono">Frame Members</span>
                  <div className="text-[16px] font-bold text-[#96ccff] mt-1">
                    {preview.counts.totalMembers}
                  </div>
                  <div className="text-[10px] text-[#8c929c] font-mono mt-0.5">
                    {preview.counts.columns} Cols, {preview.counts.beams} Beams
                  </div>
                </div>

                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-3">
                  <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider font-mono">Area Elements</span>
                  <div className="text-[16px] font-bold text-[#7ed99e] mt-1">
                    {preview.counts.slabs + preview.counts.walls}
                  </div>
                  <div className="text-[10px] text-[#8c929c] font-mono mt-0.5">
                    {preview.counts.slabs} Slabs, {preview.counts.walls} Walls
                  </div>
                </div>

                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-3">
                  <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider font-mono">Total Joints</span>
                  <div className="text-[16px] font-bold text-[#c084fc] mt-1">
                    {preview.counts.nodes}
                  </div>
                  <div className="text-[10px] text-[#8c929c] font-mono mt-0.5">
                    {preview.layers.length} CAD Layers
                  </div>
                </div>
              </div>

              {/* Subtabs for data inspection */}
              <div className="bg-[#1e2226] border border-[#3e444c] rounded-lg overflow-hidden">
                <div className="h-9 bg-[#262b30] border-b border-[#3e444c] px-3 flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    {(['nodes', 'members', 'layers', 'properties'] as const).map(tab => (
                      <button
                        key={tab}
                        id={`preview-tab-${tab}`}
                        onClick={() => setActivePreviewSubtab(tab)}
                        className={`px-3 py-1 rounded text-[11px] font-medium transition-colors ${
                          activePreviewSubtab === tab ? 'bg-[#96ccff] text-[#0f1113] font-bold' : 'text-[#a0a6af] hover:text-[#fff]'
                        }`}
                      >
                        {tab.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  <button
                    id="btn-proceed-to-mapping"
                    onClick={() => setActiveStep('mapping')}
                    className="px-3 py-1 bg-[#96ccff] hover:bg-[#80beff] text-[#0f1113] rounded text-[11px] font-semibold flex items-center space-x-1 transition-colors"
                  >
                    <span>Configure Mapping</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Tab content */}
                <div className="max-h-[220px] overflow-y-auto p-3 text-[12px] font-mono">
                  {activePreviewSubtab === 'nodes' && (
                    <table className="w-full text-left">
                      <thead>
                        <tr className="text-[#8c929c] border-b border-[#2d333a]">
                          <th className="pb-1">Node ID</th>
                          <th className="pb-1">X (m)</th>
                          <th className="pb-1">Y (m)</th>
                          <th className="pb-1">Z (m)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.sampleNodes.map(n => (
                          <tr key={n.id} className="border-b border-[#262b30] hover:bg-[#252a30]">
                            <td className="py-1 text-[#96ccff] font-bold">{n.id}</td>
                            <td className="py-1">{n.x.toFixed(3)}</td>
                            <td className="py-1">{n.y.toFixed(3)}</td>
                            <td className="py-1">{n.z.toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {activePreviewSubtab === 'members' && (
                    <table className="w-full text-left">
                      <thead>
                        <tr className="text-[#8c929c] border-b border-[#2d333a]">
                          <th className="pb-1">Member</th>
                          <th className="pb-1">Type</th>
                          <th className="pb-1">Start Node</th>
                          <th className="pb-1">End Node</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.sampleMembers.map(m => (
                          <tr key={m.id} className="border-b border-[#262b30] hover:bg-[#252a30]">
                            <td className="py-1 text-[#7ed99e] font-bold">{m.name || m.id}</td>
                            <td className="py-1 capitalize">{m.type}</td>
                            <td className="py-1 text-[#96ccff]">{m.startNodeId}</td>
                            <td className="py-1 text-[#96ccff]">{m.endNodeId}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {activePreviewSubtab === 'layers' && (
                    <div className="space-y-1">
                      {preview.layers.map(l => (
                        <div key={l.name} className="flex items-center justify-between p-1.5 bg-[#252a30] rounded">
                          <span className="text-[#f0f2f5]">{l.name}</span>
                          <span className="text-[#9ca3af]">{l.entityCount} entities ({l.detectedType})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {activePreviewSubtab === 'properties' && (
                    <div className="space-y-2 text-[#c1c7d0]">
                      <div><strong>Format:</strong> {preview.formatType}</div>
                      <div><strong>Units:</strong> {preview.detectedUnits}</div>
                      <div><strong>Materials Found:</strong> {preview.materialsFound.join(', ') || 'Default Concrete C30'}</div>
                      <div><strong>Sections Found:</strong> {preview.sectionsFound.join(', ') || 'RC 400x400 mm'}</div>
                      <div><strong>Stories:</strong> {preview.storiesDetected.join(', ') || 'Auto-generated'}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: MAPPING */}
          {activeStep === 'mapping' && (
            <div className="space-y-5 max-w-4xl mx-auto animate-in fade-in-30">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Coordinate Transform Options */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-4 space-y-3">
                  <div className="flex items-center space-x-2 text-[13px] font-semibold text-[#96ccff]">
                    <Settings2 className="w-4 h-4" />
                    <span>Coordinate Scale & Axis Systems</span>
                  </div>

                  <div>
                    <label className="text-[11px] text-[#9ca3af] block mb-1">Unit Scale Factor</label>
                    <select
                      id="select-scale-factor"
                      value={scaleFactor}
                      onChange={(e) => setScaleFactor(parseFloat(e.target.value))}
                      className="w-full bg-[#181a1c] border border-[#444a53] rounded px-3 py-1.5 text-[12px] text-[#f0f2f5] focus:outline-none focus:border-[#96ccff]"
                    >
                      <option value={1.0}>1.0 (File already in Meters)</option>
                      <option value={0.001}>0.001 (Millimeters to Meters: mm → m)</option>
                      <option value={0.0254}>0.0254 (Inches to Meters: in → m)</option>
                      <option value={0.3048}>0.3048 (Feet to Meters: ft → m)</option>
                    </select>
                  </div>

                  <div className="flex items-center space-x-2 pt-1">
                    <input
                      type="checkbox"
                      id="checkbox-swap-yz"
                      checked={swapYZ}
                      onChange={(e) => setSwapYZ(e.target.checked)}
                      className="rounded border-[#444a53] text-[#96ccff] focus:ring-0 cursor-pointer"
                    />
                    <label htmlFor="checkbox-swap-yz" className="text-[12px] text-[#c1c7d0] cursor-pointer">
                      Swap Y and Z Axes (Convert 2D/3D Y-up CAD to Z-up Structural)
                    </label>
                  </div>
                </div>

                {/* Project Integration Strategy */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-4 space-y-3">
                  <div className="flex items-center space-x-2 text-[13px] font-semibold text-[#7ed99e]">
                    <Database className="w-4 h-4" />
                    <span>Non-Destructive Project Integration</span>
                  </div>

                  <div>
                    <label className="text-[11px] text-[#9ca3af] block mb-1">Merge Strategy</label>
                    <div className="space-y-1.5">
                      <label className="flex items-center space-x-2 p-2 rounded bg-[#181a1c] border border-[#3e444c] cursor-pointer hover:border-[#96ccff]">
                        <input
                          type="radio"
                          name="mergeStrategy"
                          value="MERGE_APPEND"
                          checked={mergeStrategy === 'MERGE_APPEND'}
                          onChange={() => setMergeStrategy('MERGE_APPEND')}
                          className="text-[#96ccff]"
                        />
                        <span className="text-[12px]">
                          <strong>Merge & Append:</strong> Preserve all current elements, assign unique IDs to incoming elements.
                        </span>
                      </label>

                      <label className="flex items-center space-x-2 p-2 rounded bg-[#181a1c] border border-[#3e444c] cursor-pointer hover:border-[#96ccff]">
                        <input
                          type="radio"
                          name="mergeStrategy"
                          value="MERGE_UPDATE"
                          checked={mergeStrategy === 'MERGE_UPDATE'}
                          onChange={() => setMergeStrategy('MERGE_UPDATE')}
                          className="text-[#96ccff]"
                        />
                        <span className="text-[12px]">
                          <strong>Merge & Deduplicate:</strong> Merge coincident joints within 1mm, connect to existing frame.
                        </span>
                      </label>

                      <label className="flex items-center space-x-2 p-2 rounded bg-[#181a1c] border border-[#3e444c] cursor-pointer hover:border-[#f87171]">
                        <input
                          type="radio"
                          name="mergeStrategy"
                          value="REPLACE"
                          checked={mergeStrategy === 'REPLACE'}
                          onChange={() => setMergeStrategy('REPLACE')}
                          className="text-[#f87171]"
                        />
                        <span className="text-[12px] text-[#f87171]">
                          <strong>Replace Workspace:</strong> Replace current project entirely (creates undo snapshot).
                        </span>
                      </label>
                    </div>
                  </div>
                </div>

              </div>

              {/* Layer to Structural Type Mapping */}
              {preview && preview.layers.length > 0 && (
                <div className="bg-[#202428] border border-[#3e444c] rounded-lg p-4">
                  <h4 className="text-[13px] font-semibold text-[#f0f2f5] mb-2">
                    CAD Layer → Structural Element Mapping
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-[140px] overflow-y-auto">
                    {preview.layers.map(l => (
                      <div key={l.name} className="flex items-center justify-between bg-[#181a1c] p-2 rounded border border-[#3e444c]">
                        <span className="text-[11px] font-mono text-[#c1c7d0] truncate max-w-[120px]">{l.name}</span>
                        <select
                          value={layerMap[l.name] || 'beam'}
                          onChange={(e) => setLayerMap({ ...layerMap, [l.name]: e.target.value as any })}
                          className="bg-[#24292e] text-[#96ccff] text-[11px] rounded px-1.5 py-0.5 border border-[#444a53]"
                        >
                          <option value="column">Column</option>
                          <option value="beam">Beam</option>
                          <option value="brace">Brace</option>
                          <option value="slab">Slab</option>
                          <option value="wall">Wall</option>
                        </select>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  id="btn-proceed-to-confirm"
                  onClick={() => setActiveStep('confirm')}
                  className="px-5 py-2.5 bg-[#96ccff] hover:bg-[#80beff] text-[#0f1113] rounded-md text-[13px] font-bold flex items-center space-x-2 transition-colors shadow-lg"
                >
                  <span>Review & Confirm Import</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: CONFIRMATION */}
          {activeStep === 'confirm' && (
            <div className="space-y-5 max-w-2xl mx-auto text-center animate-in fade-in-30 pt-4">
              <div className="w-14 h-14 rounded-full bg-[#7ed99e]/15 border border-[#7ed99e]/40 flex items-center justify-center text-[#7ed99e] mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-[18px] font-bold text-[#f0f2f5]">
                  Ready to Commit Structural Data to Workspace
                </h3>
                <p className="text-[13px] text-[#9ca3af] mt-1">
                  Guaranteed preservation of 3D coordinates, cross-sections, materials, and metadata.
                </p>
              </div>

              {/* Preservation checklist */}
              <div className="bg-[#202428] border border-[#3e444c] rounded-xl p-4 text-left space-y-2.5 text-[12px]">
                <div className="flex items-center space-x-2 text-[#7ed99e]">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span><strong>Coordinates:</strong> 3D Cartesian points transformed with 0.0001m precision.</span>
                </div>
                <div className="flex items-center space-x-2 text-[#7ed99e]">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span><strong>Objects:</strong> Frame members, area slabs, shear walls, and releases intact.</span>
                </div>
                <div className="flex items-center space-x-2 text-[#7ed99e]">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span><strong>Materials & Sections:</strong> Physical moduli ($E, \nu, \rho$), dimensions, and inertial moments preserved.</span>
                </div>
                <div className="flex items-center space-x-2 text-[#7ed99e]">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span><strong>Safety:</strong> Undo snapshot registered automatically in ProjectStore history.</span>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-center space-x-3">
                <button
                  id="btn-back-to-mapping"
                  onClick={() => setActiveStep('mapping')}
                  className="px-4 py-2.5 bg-[#2a2e33] hover:bg-[#343a42] text-[#c1c7d0] rounded-md text-[13px] font-medium"
                >
                  Adjust Parameters
                </button>

                <button
                  id="btn-commit-to-workspace"
                  onClick={handleApplyMappingAndCommit}
                  disabled={commitSuccess}
                  className="px-6 py-2.5 bg-[#7ed99e] hover:bg-[#6ec98e] text-[#0f1113] rounded-md text-[13px] font-bold flex items-center space-x-2 transition-all shadow-lg hover:scale-105"
                >
                  {commitSuccess ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Committed Successfully!</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Commit to Active Project</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* EXPORT TAB */}
          {activeStep === 'export' && (
            <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in-30">
              <div>
                <h3 className="text-[16px] font-semibold text-[#f0f2f5]">
                  {lang === 'ar' ? 'تصدير النموذج الإنشائي النشط' : 'Export Active Structural Model'}
                </h3>
                <p className="text-[13px] text-[#9ca3af] mt-1">
                  Download industry-standard BIM files (IFC4), AutoCAD DXF, multi-sheet Excel workbooks, CSV tables, or JSON.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* IFC Export */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-xl p-4 flex flex-col justify-between hover:border-[#96ccff] transition-colors">
                  <div>
                    <div className="flex items-center space-x-2 text-[#96ccff] font-bold text-[14px]">
                      <Box className="w-5 h-5" />
                      <span>IFC 4.0 / 2x3 BIM Model</span>
                    </div>
                    <p className="text-[12px] text-[#9ca3af] mt-2">
                      Standard ISO-10303-21 STEP BIM file with full geometry, materials, profile definitions, and stories.
                    </p>
                  </div>
                  <button
                    id="export-ifc-button"
                    onClick={() => handleExport('IFC')}
                    className="mt-4 w-full py-2 bg-[#96ccff]/15 hover:bg-[#96ccff]/25 border border-[#96ccff]/40 text-[#96ccff] rounded font-semibold text-[12px] flex items-center justify-center space-x-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download .IFC File</span>
                  </button>
                </div>

                {/* DXF Export */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-xl p-4 flex flex-col justify-between hover:border-[#7ed99e] transition-colors">
                  <div>
                    <div className="flex items-center space-x-2 text-[#7ed99e] font-bold text-[14px]">
                      <Layers className="w-5 h-5" />
                      <span>AutoCAD 3D DXF (R12/2000)</span>
                    </div>
                    <p className="text-[12px] text-[#9ca3af] mt-2">
                      Universal CAD drawing with distinct COLUMNS, BEAMS, SLABS, WALLS, and JOINTS layers.
                    </p>
                  </div>
                  <button
                    id="export-dxf-button"
                    onClick={() => handleExport('DXF')}
                    className="mt-4 w-full py-2 bg-[#7ed99e]/15 hover:bg-[#7ed99e]/25 border border-[#7ed99e]/40 text-[#7ed99e] rounded font-semibold text-[12px] flex items-center justify-center space-x-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download .DXF File</span>
                  </button>
                </div>

                {/* Excel Export */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-xl p-4 flex flex-col justify-between hover:border-[#4ade80] transition-colors">
                  <div>
                    <div className="flex items-center space-x-2 text-[#4ade80] font-bold text-[14px]">
                      <FileSpreadsheet className="w-5 h-5" />
                      <span>Microsoft Excel XML Workbook</span>
                    </div>
                    <p className="text-[12px] text-[#9ca3af] mt-2">
                      Multi-sheet spreadsheet (Nodes, Members, Slabs, Walls, Materials, Sections) ready for estimation & review.
                    </p>
                  </div>
                  <button
                    id="export-excel-button"
                    onClick={() => handleExport('EXCEL')}
                    className="mt-4 w-full py-2 bg-[#4ade80]/15 hover:bg-[#4ade80]/25 border border-[#4ade80]/40 text-[#4ade80] rounded font-semibold text-[12px] flex items-center justify-center space-x-2"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download .XML Workbook</span>
                  </button>
                </div>

                {/* CSV & JSON Export */}
                <div className="bg-[#202428] border border-[#3e444c] rounded-xl p-4 flex flex-col justify-between hover:border-[#c084fc] transition-colors">
                  <div>
                    <div className="flex items-center space-x-2 text-[#c084fc] font-bold text-[14px]">
                      <FileCode className="w-5 h-5" />
                      <span>JSON & CSV Structured Formats</span>
                    </div>
                    <p className="text-[12px] text-[#9ca3af] mt-2">
                      Full programmatic schemas for computational engineering, Python solvers, and cloud integration.
                    </p>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <button
                      id="export-csv-button"
                      onClick={() => handleExport('CSV')}
                      className="py-2 bg-[#2a2f36] hover:bg-[#343a42] border border-[#444a53] text-[#e2e2e5] rounded font-semibold text-[12px] flex items-center justify-center space-x-1.5"
                    >
                      <Download className="w-3.5 h-3.5 text-[#f8b449]" />
                      <span>CSV</span>
                    </button>
                    <button
                      id="export-json-button"
                      onClick={() => handleExport('JSON')}
                      className="py-2 bg-[#2a2f36] hover:bg-[#343a42] border border-[#444a53] text-[#e2e2e5] rounded font-semibold text-[12px] flex items-center justify-center space-x-1.5"
                    >
                      <Download className="w-3.5 h-3.5 text-[#c084fc]" />
                      <span>JSON</span>
                    </button>
                  </div>
                </div>

              </div>
            </div>
          )}

        </div>

        {/* Modal Bottom Footer */}
        <div className="h-11 bg-[#1a1c1e] border-t border-[#3e444c] px-5 flex items-center justify-between text-[11px] text-[#8c929c] font-mono">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[#7ed99e] inline-block"></span>
            <span>STRUCTURE-X ULTIMATE v5.0 INTEROP ENGINE ACTIVE</span>
          </div>
          <div>
            ISO 10303-21 • DXF R12 • OpenXML • RFC 8259
          </div>
        </div>

      </div>
    </div>
  );
};
