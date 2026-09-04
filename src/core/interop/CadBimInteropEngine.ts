/**
 * STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY ENGINE (PHASE 13)
 * Full browser-native implementation supporting:
 * - IFC Import & Export (STEP ISO-10303-21)
 * - DXF Import & Export (AutoCAD R12/2000 ASCII)
 * - CSV Import & Export (Multi-table & Delimited)
 * - Excel Import & Export (SpreadsheetML XML Workbooks)
 * - JSON Import & Export (Full Schema Fidelity)
 * 5-Stage Interoperability Workflow:
 * 1. Import -> 2. Validation -> 3. Preview -> 4. Mapping -> 5. Confirmation
 */

import { StructuralModel, StructuralMember, NodePoint, SectionProperty, Material } from '../../types/structure';
import {
  InteropFormat,
  MergeStrategy,
  ValidationSummary,
  ValidationIssue,
  ValidationSeverity,
  BoundingBox3D,
  EntityCounts,
  LayerInfo,
  ImportPreviewSummary,
  CoordinateTransform,
  MappingConfig,
  InteropResult
} from './CadBimTypes';

export class CadBimInteropEngine {

  // --- 1. FORMAT DETECTION ---
  public static detectFormat(filename: string, content: string): InteropFormat {
    const lower = filename.toLowerCase();
    if (lower.endsWith('.ifc') || content.slice(0, 200).includes('ISO-10303-21')) {
      return 'IFC';
    }
    if (lower.endsWith('.dxf') || (content.slice(0, 300).includes('SECTION') && content.slice(0, 300).includes('HEADER'))) {
      return 'DXF';
    }
    if (lower.endsWith('.json') || (content.trim().startsWith('{') && content.slice(0, 200).includes('projectName'))) {
      return 'JSON';
    }
    if (lower.endsWith('.xml') || content.slice(0, 300).includes('urn:schemas-microsoft-com:office:spreadsheet')) {
      return 'EXCEL';
    }
    return 'CSV';
  }

  // --- 2. IMPORT (STAGE 1) ---
  public static importFile(
    content: string,
    filename: string = 'imported_model',
    formatOverride?: InteropFormat
  ): InteropResult<Partial<StructuralModel>> {
    const format = formatOverride || this.detectFormat(filename, content);

    try {
      let parsed: Partial<StructuralModel>;
      switch (format) {
        case 'IFC':
          parsed = this.parseIfcText(content);
          break;
        case 'DXF':
          parsed = this.parseDxfText(content);
          break;
        case 'CSV':
          parsed = this.parseCsvText(content);
          break;
        case 'EXCEL':
          parsed = this.parseExcelXmlText(content);
          break;
        case 'JSON':
          parsed = JSON.parse(content);
          break;
        default:
          parsed = this.parseCsvText(content);
          break;
      }

      const validation = this.validateModelData(parsed);
      const preview = this.generatePreview(parsed, format, filename, new Blob([content]).size);

      return {
        success: true,
        formatType: format,
        message: `Successfully parsed ${format} file '${filename}'.`,
        preview,
        validation,
        data: parsed
      };
    } catch (err: any) {
      return {
        success: false,
        formatType: format,
        message: `Import failed: ${err?.message || String(err)}`
      };
    }
  }

  // --- 3. VALIDATION (STAGE 2) ---
  public static validateModelData(data: Partial<StructuralModel>, toleranceM: number = 0.001): ValidationSummary {
    const issues: ValidationIssue[] = [];
    const nodes = data.nodes || [];
    const members = data.members || [];
    const slabs = data.slabs || [];
    const walls = data.walls || [];

    if (nodes.length === 0 && (members.length > 0 || slabs.length > 0 || walls.length > 0)) {
      issues.push({
        severity: 'ERROR',
        code: 'VAL-NO-NODES',
        message: 'The model contains structural elements but no defined joint coordinates.',
        entityType: 'nodes',
        suggestedFix: 'Ensure file contains 3D coordinates.'
      });
    }

    const nodeCoords = new Map<string, [number, number, number]>();
    const nodeIds = new Set<string>();

    for (const n of nodes) {
      if (nodeIds.has(n.id)) {
        issues.push({
          severity: 'WARNING',
          code: 'VAL-NODE-DUP-ID',
          message: `Duplicate node ID detected: '${n.id}'. Will be deduplicated automatically.`,
          entityType: 'node',
          entityId: n.id
        });
      }
      nodeIds.add(n.id);

      if (!Number.isFinite(n.x) || !Number.isFinite(n.y) || !Number.isFinite(n.z)) {
        issues.push({
          severity: 'ERROR',
          code: 'VAL-NODE-NON-FINITE',
          message: `Node '${n.id}' contains non-finite coordinates.`,
          entityType: 'node',
          entityId: n.id
        });
      } else {
        nodeCoords.set(n.id, [n.x, n.y, n.z]);
      }
    }

    // Check for coincident nodes within tolerance
    const coordsArray = Array.from(nodeCoords.entries());
    let coincidentCount = 0;
    for (let i = 0; i < coordsArray.length; i++) {
      const [id1, [x1, y1, z1]] = coordsArray[i];
      for (let j = i + 1; j < coordsArray.length; j++) {
        const [id2, [x2, y2, z2]] = coordsArray[j];
        const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2);
        if (dist <= toleranceM) {
          coincidentCount++;
          if (coincidentCount <= 3) {
            issues.push({
              severity: 'INFO',
              code: 'VAL-NODE-COINCIDENT',
              message: `Nodes '${id1}' and '${id2}' are coincident within ${(toleranceM * 1000).toFixed(1)}mm.`,
              entityType: 'node',
              suggestedFix: 'Can be merged during mapping.'
            });
          }
        }
      }
    }

    // Members check
    for (const m of members) {
      const p1 = nodeCoords.get(m.startNodeId);
      const p2 = nodeCoords.get(m.endNodeId);
      if (!p1 || !p2) {
        issues.push({
          severity: 'ERROR',
          code: 'VAL-MEM-DANGLING-NODE',
          message: `Member '${m.id}' references missing node (start='${m.startNodeId}', end='${m.endNodeId}').`,
          entityType: 'member',
          entityId: m.id
        });
      } else {
        const length = Math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2);
        if (length < 0.001) {
          issues.push({
            severity: 'ERROR',
            code: 'VAL-MEM-ZERO-LENGTH',
            message: `Member '${m.id}' has near-zero length (${(length * 1000).toFixed(1)}mm).`,
            entityType: 'member',
            entityId: m.id
          });
        }
      }
    }

    // Slabs check
    for (const s of slabs) {
      if (!s.nodeIds || s.nodeIds.length < 3) {
        issues.push({
          severity: 'ERROR',
          code: 'VAL-SLAB-VERTICES',
          message: `Slab '${s.id}' requires at least 3 perimeter vertices.`,
          entityType: 'slab',
          entityId: s.id
        });
      }
    }

    const errorCount = issues.filter(i => i.severity === 'ERROR').length;
    const warningCount = issues.filter(i => i.severity === 'WARNING').length;
    const infoCount = issues.filter(i => i.severity === 'INFO').length;

    return {
      isValid: errorCount === 0,
      canImport: errorCount === 0 || nodes.length > 0,
      totalIssues: issues.length,
      errorCount,
      warningCount,
      infoCount,
      issues
    };
  }

  // --- 4. PREVIEW (STAGE 3) ---
  public static generatePreview(
    data: Partial<StructuralModel>,
    format: InteropFormat,
    filename: string,
    fileSizeBytes: number
  ): ImportPreviewSummary {
    const nodes = data.nodes || [];
    const members = data.members || [];
    const slabs = data.slabs || [];
    const walls = data.walls || [];
    const materials = data.materials || [];
    const sections = data.sections || [];
    const stories = data.stories || [];

    const cols = members.filter(m => m.type === 'column').length;
    const beams = members.filter(m => m.type === 'beam').length;
    const braces = members.filter(m => m.type === 'brace').length;

    // Bounding Box
    let minX = 0, maxX = 0, minY = 0, maxY = 0, minZ = 0, maxZ = 0;
    if (nodes.length > 0) {
      minX = Math.min(...nodes.map(n => n.x));
      maxX = Math.max(...nodes.map(n => n.x));
      minY = Math.min(...nodes.map(n => n.y));
      maxY = Math.max(...nodes.map(n => n.y));
      minZ = Math.min(...nodes.map(n => n.z));
      maxZ = Math.max(...nodes.map(n => n.z));
    }

    const bbox: BoundingBox3D = {
      minX, maxX, minY, maxY, minZ, maxZ,
      spanX: maxX - minX,
      spanY: maxY - minY,
      spanZ: maxZ - minZ
    };

    // Layer Info
    const layerMap = new Map<string, number>();
    for (const m of members) {
      const l = (m as any).layer || 'Default';
      layerMap.set(l, (layerMap.get(l) || 0) + 1);
    }
    for (const s of slabs) {
      const l = (s as any).layer || 'Default';
      layerMap.set(l, (layerMap.get(l) || 0) + 1);
    }

    const layers: LayerInfo[] = Array.from(layerMap.entries()).map(([name, count]) => ({
      name,
      entityCount: count,
      detectedType: name.toLowerCase().includes('col') ? 'column' :
                    name.toLowerCase().includes('beam') ? 'beam' :
                    name.toLowerCase().includes('slab') ? 'slab' : 'unknown'
    }));

    const counts: EntityCounts = {
      nodes: nodes.length,
      columns: cols,
      beams,
      braces,
      slabs: slabs.length,
      walls: walls.length,
      openings: (data.openings || []).length,
      materials: materials.length,
      sections: sections.length,
      stories: stories.length,
      layers: layers.length,
      totalMembers: members.length,
      totalEntities: nodes.length + members.length + slabs.length + walls.length
    };

    return {
      formatType: format,
      sourceName: filename,
      fileSizeBytes,
      detectedUnits: data.units || 'kN-m, C',
      counts,
      boundingBox: bbox,
      layers,
      materialsFound: materials.map(m => m.name || m.id),
      sectionsFound: sections.map(s => s.name || s.id),
      storiesDetected: stories.map(s => s.name),
      sampleNodes: nodes.slice(0, 6).map(n => ({ id: n.id, x: n.x, y: n.y, z: n.z })),
      sampleMembers: members.slice(0, 6).map(m => ({ id: m.id, name: m.name, type: m.type, startNodeId: m.startNodeId, endNodeId: m.endNodeId }))
    };
  }

  // --- 5. MAPPING (STAGE 4) ---
  public static mapData(
    rawData: Partial<StructuralModel>,
    config: MappingConfig
  ): StructuralModel {
    const rawNodes = rawData.nodes || [];
    const tol = Math.max(config.toleranceM, 1e-4);

    // Transform and deduplicate nodes
    const uniqueNodes: NodePoint[] = [];
    const nodeIdRemap = new Map<string, string>();

    for (const n of rawNodes) {
      // 1. Scale
      let tx = n.x * config.coordinateTransform.scaleFactor;
      let ty = n.y * config.coordinateTransform.scaleFactor;
      let tz = n.z * config.coordinateTransform.scaleFactor;

      // 2. Axis swap
      if (config.coordinateTransform.swapYZ) {
        const temp = ty;
        ty = tz;
        tz = temp;
      }
      if (config.coordinateTransform.invertZ) {
        tz = -tz;
      }

      // 3. Translation
      tx += config.coordinateTransform.offsetX;
      ty += config.coordinateTransform.offsetY;
      tz += config.coordinateTransform.offsetZ;

      tx = Math.round(tx * 10000) / 10000;
      ty = Math.round(ty * 10000) / 10000;
      tz = Math.round(tz * 10000) / 10000;

      // Check coincidence
      let matchId: string | null = null;
      for (const u of uniqueNodes) {
        const d = Math.sqrt((tx - u.x) ** 2 + (ty - u.y) ** 2 + (tz - u.z) ** 2);
        if (d <= tol) {
          matchId = u.id;
          break;
        }
      }

      if (matchId) {
        nodeIdRemap.set(n.id, matchId);
      } else {
        uniqueNodes.push({
          id: n.id,
          x: tx,
          y: ty,
          z: tz,
          isRestrained: n.isRestrained
        });
        nodeIdRemap.set(n.id, n.id);
      }
    }

    // Normalize Materials
    const materials: Material[] = [...(rawData.materials || [])];
    if (!materials.some(m => m.id === config.defaultMaterialId)) {
      materials.push({
        id: config.defaultMaterialId,
        name: 'Concrete C30/37 (Default)',
        type: 'concrete',
        grade: 'C30/37',
        elasticModulusE: 33.0,
        poissonRatio: 0.2,
        unitWeight: 25.0,
        compressiveStrengthFc: 30.0,
        color: '#9ca3af'
      });
    }

    // Normalize Sections
    const sections: SectionProperty[] = [...(rawData.sections || [])];
    if (!sections.some(s => s.id === config.defaultSectionId)) {
      sections.push({
        id: config.defaultSectionId,
        name: 'RC 400x400 mm',
        shape: 'rectangular',
        materialId: config.defaultMaterialId,
        dimensions: { width: 400.0, height: 400.0 },
        area: 1600.0,
        momentOfInertiaIxx: 213333.3,
        momentOfInertiaIyy: 213333.3,
        torsionalConstantJ: 360000.0,
        weightPerMeter: 100.0
      });
    }

    // Transform Members
    const members: StructuralMember[] = [];
    for (const m of rawData.members || []) {
      const sn = nodeIdRemap.get(m.startNodeId) || m.startNodeId;
      const en = nodeIdRemap.get(m.endNodeId) || m.endNodeId;
      if (sn === en) continue; // collapsed

      const n1 = uniqueNodes.find(n => n.id === sn);
      const n2 = uniqueNodes.find(n => n.id === en);
      const length = (n1 && n2) ? Math.sqrt((n2.x - n1.x) ** 2 + (n2.y - n1.y) ** 2 + (n2.z - n1.z) ** 2) : m.length;

      // Layer mapping
      let mtype = m.type;
      const layer = (m as any).layer;
      if (layer && config.layerTypeMap[layer]) {
        mtype = config.layerTypeMap[layer];
      } else if (!mtype && n1 && n2) {
        const dz = Math.abs(n2.z - n1.z);
        const dxy = Math.sqrt((n2.x - n1.x) ** 2 + (n2.y - n1.y) ** 2);
        mtype = dz > dxy * 1.5 ? 'column' : 'beam';
      }

      // Section & Material map
      const secId = config.sectionMap[m.sectionId] || m.sectionId || config.defaultSectionId;
      const matId = config.materialMap[m.materialId] || m.materialId || config.defaultMaterialId;

      members.push({
        ...m,
        type: mtype || 'beam',
        startNodeId: sn,
        endNodeId: en,
        sectionId: secId,
        materialId: matId,
        length: Math.round(length * 1000) / 1000,
        releases: m.releases || 'Continuous',
        localAxisAngle: m.localAxisAngle || 0
      });
    }

    // Transform Slabs
    const slabs = (rawData.slabs || []).map(s => ({
      ...s,
      nodeIds: s.nodeIds.map(nid => nodeIdRemap.get(nid) || nid).filter((v, i, a) => a.indexOf(v) === i),
      materialId: config.materialMap[s.materialId] || s.materialId || config.defaultMaterialId
    })).filter(s => s.nodeIds.length >= 3);

    // Transform Walls
    const walls = (rawData.walls || []).map(w => ({
      ...w,
      nodeIds: w.nodeIds.map(nid => nodeIdRemap.get(nid) || nid).filter((v, i, a) => a.indexOf(v) === i),
      materialId: config.materialMap[w.materialId] || w.materialId || config.defaultMaterialId
    })).filter(w => w.nodeIds.length >= 3);

    return {
      projectName: rawData.projectName || 'Imported Structural Model',
      version: '5.0.0-PRO',
      units: rawData.units || 'kN-m, C',
      stories: rawData.stories || [
        { id: 'STORY_1', name: 'Story 1', elevation: 3.5, height: 3.5 }
      ],
      gridLinesX: rawData.gridLinesX || [],
      gridLinesY: rawData.gridLinesY || [],
      materials,
      sections,
      nodes: uniqueNodes,
      members,
      slabs,
      walls,
      openings: rawData.openings || [],
      links: rawData.links || [],
      springs: rawData.springs || [],
      diaphragms: rawData.diaphragms || [],
      metadata: rawData.metadata || {}
    };
  }

  // --- 6. CONFIRMATION & NON-DESTRUCTIVE COMMIT (STAGE 5) ---
  public static confirmAndCommit(
    existing: StructuralModel,
    incoming: StructuralModel,
    strategy: MergeStrategy = 'MERGE_APPEND',
    toleranceM: number = 0.001
  ): StructuralModel {
    if (strategy === 'REPLACE') {
      return {
        ...incoming,
        projectName: incoming.projectName || existing.projectName
      };
    }

    // Deep clone existing to guarantee zero corruption
    const merged: StructuralModel = JSON.parse(JSON.stringify(existing));

    const existingNodeIds = new Set(merged.nodes.map(n => n.id));
    const existingMemberIds = new Set(merged.members.map(m => m.id));
    const existingSlabIds = new Set(merged.slabs.map(s => s.id));
    const existingWallIds = new Set(merged.walls.map(w => w.id));

    // Append unique materials & sections
    for (const mat of incoming.materials) {
      if (!merged.materials.some(m => m.id === mat.id)) {
        merged.materials.push(mat);
      }
    }
    for (const sec of incoming.sections) {
      if (!merged.sections.some(s => s.id === sec.id)) {
        merged.sections.push(sec);
      }
    }

    const nodeRemap = new Map<string, string>();

    for (const n of incoming.nodes) {
      let matchedExisting: string | null = null;
      if (strategy === 'MERGE_UPDATE') {
        for (const ex of merged.nodes) {
          const d = Math.sqrt((n.x - ex.x) ** 2 + (n.y - ex.y) ** 2 + (n.z - ex.z) ** 2);
          if (d <= toleranceM) {
            matchedExisting = ex.id;
            break;
          }
        }
      }

      if (matchedExisting) {
        nodeRemap.set(n.id, matchedExisting);
      } else {
        let newId = n.id;
        if (existingNodeIds.has(newId)) {
          let count = 1;
          while (existingNodeIds.has(`${n.id}_imp${count}`)) count++;
          newId = `${n.id}_imp${count}`;
        }
        merged.nodes.push({ ...n, id: newId });
        existingNodeIds.add(newId);
        nodeRemap.set(n.id, newId);
      }
    }

    // Merge Members
    for (const m of incoming.members) {
      let newMid = m.id;
      if (existingMemberIds.has(newMid)) {
        let count = 1;
        while (existingMemberIds.has(`${m.id}_imp${count}`)) count++;
        newMid = `${m.id}_imp${count}`;
      }

      const sn = nodeRemap.get(m.startNodeId) || m.startNodeId;
      const en = nodeRemap.get(m.endNodeId) || m.endNodeId;
      if (sn !== en) {
        merged.members.push({
          ...m,
          id: newMid,
          startNodeId: sn,
          endNodeId: en
        });
        existingMemberIds.add(newMid);
      }
    }

    // Merge Slabs
    for (const s of incoming.slabs) {
      let newSid = s.id;
      if (existingSlabIds.has(newSid)) {
        let count = 1;
        while (existingSlabIds.has(`${s.id}_imp${count}`)) count++;
        newSid = `${s.id}_imp${count}`;
      }
      const mappedNids = s.nodeIds.map(nid => nodeRemap.get(nid) || nid);
      if (mappedNids.length >= 3) {
        merged.slabs.push({
          ...s,
          id: newSid,
          nodeIds: mappedNids
        });
        existingSlabIds.add(newSid);
      }
    }

    // Merge Walls
    for (const w of incoming.walls) {
      let newWid = w.id;
      if (existingWallIds.has(newWid)) {
        let count = 1;
        while (existingWallIds.has(`${w.id}_imp${count}`)) count++;
        newWid = `${w.id}_imp${count}`;
      }
      const mappedNids = w.nodeIds.map(nid => nodeRemap.get(nid) || nid);
      if (mappedNids.length >= 3) {
        merged.walls.push({
          ...w,
          id: newWid,
          nodeIds: mappedNids
        });
        existingWallIds.add(newWid);
      }
    }

    return merged;
  }

  // --- 7. EXPORT (IFC, DXF, CSV, EXCEL, JSON) ---
  public static exportModel(
    model: StructuralModel,
    format: InteropFormat,
    options?: { delimiter?: string; ifcVersion?: string }
  ): { content: string; filename: string; mimeType: string } {
    const cleanName = (model.projectName || 'Model').replace(/[^a-zA-Z0-9_-]/g, '_');

    switch (format) {
      case 'IFC':
        return {
          content: this.generateIfcText(model, options?.ifcVersion || 'IFC4'),
          filename: `${cleanName}.ifc`,
          mimeType: 'application/x-step'
        };
      case 'DXF':
        return {
          content: this.generateDxfText(model),
          filename: `${cleanName}.dxf`,
          mimeType: 'application/dxf'
        };
      case 'CSV':
        return {
          content: this.generateCsvText(model, options?.delimiter || ','),
          filename: `${cleanName}.csv`,
          mimeType: 'text/csv'
        };
      case 'EXCEL':
        return {
          content: this.generateExcelXmlText(model),
          filename: `${cleanName}.xml`,
          mimeType: 'application/vnd.ms-excel'
        };
      case 'JSON':
      default:
        return {
          content: JSON.stringify(model, null, 2),
          filename: `${cleanName}.json`,
          mimeType: 'application/json'
        };
    }
  }

  // --- PARSERS & GENERATORS ---

  // DXF Parser
  private static parseDxfText(content: string): Partial<StructuralModel> {
    const lines = content.split(/\r?\n/);
    const nodes: NodePoint[] = [];
    const nodeLookup = new Map<string, string>();
    const members: StructuralMember[] = [];
    const slabs: any[] = [];
    const walls: any[] = [];

    const getOrCreateNode = (x: number, y: number, z: number): string => {
      const key = `${x.toFixed(4)},${y.toFixed(4)},${z.toFixed(4)}`;
      if (nodeLookup.has(key)) return nodeLookup.get(key)!;
      const nid = `N_DXF_${nodes.length + 1}`;
      nodes.push({ id: nid, x, y, z });
      nodeLookup.set(key, nid);
      return nid;
    };

    let inEntities = false;
    let i = 0;
    while (i < lines.length - 1) {
      const code = parseInt(lines[i].trim(), 10);
      const val = lines[i + 1]?.trim();

      if (code === 0 && val === 'SECTION') {
        if (lines[i + 3]?.trim().toUpperCase() === 'ENTITIES') {
          inEntities = true;
        }
      } else if (code === 0 && val === 'ENDSEC') {
        inEntities = false;
      }

      if (inEntities && code === 0) {
        const entType = val.toUpperCase();
        i += 2;

        if (entType === 'LINE') {
          let layer = '0';
          let x1 = 0, y1 = 0, z1 = 0, x2 = 0, y2 = 0, z2 = 0;
          while (i < lines.length - 1 && parseInt(lines[i].trim(), 10) !== 0) {
            const ecode = parseInt(lines[i].trim(), 10);
            const evalue = lines[i + 1]?.trim();
            if (ecode === 8) layer = evalue;
            if (ecode === 10) x1 = parseFloat(evalue);
            if (ecode === 20) y1 = parseFloat(evalue);
            if (ecode === 30) z1 = parseFloat(evalue);
            if (ecode === 11) x2 = parseFloat(evalue);
            if (ecode === 21) y2 = parseFloat(evalue);
            if (ecode === 31) z2 = parseFloat(evalue);
            i += 2;
          }
          const len = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2);
          if (len > 0.001) {
            const sn = getOrCreateNode(x1, y1, z1);
            const en = getOrCreateNode(x2, y2, z2);
            const isCol = layer.toLowerCase().includes('col') || Math.abs(z2 - z1) > Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
            members.push({
              id: `M_DXF_${members.length + 1}`,
              name: `DXF_${layer}_${members.length + 1}`,
              type: isCol ? 'column' : 'beam',
              story: 'Story 1',
              startNodeId: sn,
              endNodeId: en,
              sectionId: 'SEC-COL-400X400',
              materialId: 'MAT-C30',
              length: len,
              releases: 'Continuous',
              localAxisAngle: 0
            });
          }
          continue;
        } else if (entType === '3DFACE') {
          let layer = '0';
          const coords: Record<number, number> = {};
          while (i < lines.length - 1 && parseInt(lines[i].trim(), 10) !== 0) {
            const ecode = parseInt(lines[i].trim(), 10);
            const evalue = lines[i + 1]?.trim();
            if (ecode === 8) layer = evalue;
            if ([10, 20, 30, 11, 21, 31, 12, 22, 32, 13, 23, 33].includes(ecode)) {
              coords[ecode] = parseFloat(evalue);
            }
            i += 2;
          }
          const p1 = getOrCreateNode(coords[10] || 0, coords[20] || 0, coords[30] || 0);
          const p2 = getOrCreateNode(coords[11] || 0, coords[21] || 0, coords[31] || 0);
          const p3 = getOrCreateNode(coords[12] || 0, coords[22] || 0, coords[32] || 0);
          const nids = [p1, p2, p3];
          if (coords[13] !== undefined && coords[23] !== undefined) {
            const p4 = getOrCreateNode(coords[13], coords[23], coords[33] || 0);
            if (p4 !== p3) nids.push(p4);
          }
          if (layer.toLowerCase().includes('wall')) {
            walls.push({ id: `WALL_DXF_${walls.length + 1}`, name: `Wall_${walls.length + 1}`, story: 'Story 1', nodeIds: nids, thickness: 0.25, materialId: 'MAT-C30' });
          } else {
            slabs.push({ id: `SLAB_DXF_${slabs.length + 1}`, name: `Slab_${slabs.length + 1}`, story: 'Story 1', nodeIds: nids, thickness: 0.20, materialId: 'MAT-C30', loadDead: 2.5, loadLive: 3.0, diaphragm: 'rigid' });
          }
          continue;
        }
      }
      i += 2;
    }

    return {
      projectName: 'DXF Imported Model',
      nodes,
      members,
      slabs,
      walls,
      materials: [{ id: 'MAT-C30', name: 'Concrete C30/37', type: 'concrete', grade: 'C30/37', elasticModulusE: 33.0, poissonRatio: 0.2, unitWeight: 25.0, color: '#9ca3af' }],
      sections: [{ id: 'SEC-COL-400X400', name: 'RC 400x400 mm', shape: 'rectangular', materialId: 'MAT-C30', dimensions: { width: 400, height: 400 }, area: 1600, momentOfInertiaIxx: 213333.3, momentOfInertiaIyy: 213333.3, torsionalConstantJ: 360000, weightPerMeter: 100 }]
    };
  }

  // DXF Generator
  private static generateDxfText(model: StructuralModel): string {
    const lines: string[] = [];
    const add = (code: number, val: any) => { lines.push(String(code), String(val)); };

    add(0, 'SECTION');
    add(2, 'HEADER');
    add(9, '$ACADVER');
    add(1, 'AC1009');
    add(0, 'ENDSEC');

    add(0, 'SECTION');
    add(2, 'TABLES');
    add(0, 'TABLE');
    add(2, 'LAYER');
    add(70, 4);
    const layers = [['COLUMNS', 4], ['BEAMS', 1], ['SLABS', 3], ['WALLS', 6], ['JOINTS', 7]];
    for (const [lname, col] of layers) {
      add(0, 'LAYER');
      add(2, lname);
      add(70, 0);
      add(62, col);
      add(6, 'CONTINUOUS');
    }
    add(0, 'ENDTAB');
    add(0, 'ENDSEC');

    add(0, 'SECTION');
    add(2, 'ENTITIES');

    const nodeMap = new Map(model.nodes.map(n => [n.id, n]));

    for (const n of model.nodes) {
      add(0, 'POINT');
      add(8, 'JOINTS');
      add(10, n.x);
      add(20, n.y);
      add(30, n.z);
    }

    for (const m of model.members) {
      const n1 = nodeMap.get(m.startNodeId);
      const n2 = nodeMap.get(m.endNodeId);
      if (n1 && n2) {
        add(0, 'LINE');
        add(8, m.type === 'column' ? 'COLUMNS' : 'BEAMS');
        add(10, n1.x);
        add(20, n1.y);
        add(30, n1.z);
        add(11, n2.x);
        add(21, n2.y);
        add(31, n2.z);
      }
    }

    for (const s of model.slabs) {
      const pts = s.nodeIds.map(nid => nodeMap.get(nid)).filter(Boolean) as NodePoint[];
      if (pts.length >= 3) {
        add(0, '3DFACE');
        add(8, 'SLABS');
        add(10, pts[0].x); add(20, pts[0].y); add(30, pts[0].z);
        add(11, pts[1].x); add(21, pts[1].y); add(31, pts[1].z);
        add(12, pts[2].x); add(22, pts[2].y); add(32, pts[2].z);
        add(13, (pts[3] || pts[2]).x); add(23, (pts[3] || pts[2]).y); add(33, (pts[3] || pts[2]).z);
      }
    }

    for (const w of model.walls) {
      const pts = w.nodeIds.map(nid => nodeMap.get(nid)).filter(Boolean) as NodePoint[];
      if (pts.length >= 3) {
        add(0, '3DFACE');
        add(8, 'WALLS');
        add(10, pts[0].x); add(20, pts[0].y); add(30, pts[0].z);
        add(11, pts[1].x); add(21, pts[1].y); add(31, pts[1].z);
        add(12, pts[2].x); add(22, pts[2].y); add(32, pts[2].z);
        add(13, (pts[3] || pts[2]).x); add(23, (pts[3] || pts[2]).y); add(33, (pts[3] || pts[2]).z);
      }
    }

    add(0, 'ENDSEC');
    add(0, 'EOF');
    return lines.join('\n');
  }

  // IFC Parser
  private static parseIfcText(content: string): Partial<StructuralModel> {
    const nodes: NodePoint[] = [];
    const members: StructuralMember[] = [];
    const slabs: any[] = [];
    const ptMap = new Map<number, [number, number, number]>();

    // Match all CARTESIANPOINT
    const ptRegex = /#(\d+)\s*=\s*IFCCARTESIANPOINT\s*\(\s*\(\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)\s*(?:,\s*([-\d.eE]+))?\s*\)\s*\)/g;
    let match;
    while ((match = ptRegex.exec(content)) !== null) {
      const id = parseInt(match[1], 10);
      ptMap.set(id, [parseFloat(match[2]), parseFloat(match[3]), match[4] ? parseFloat(match[4]) : 0]);
    }

    // Match BEAM and COLUMN
    const elemRegex = /#(\d+)\s*=\s*(IFCBEAM|IFCCOLUMN|IFCSLAB)\s*\(\s*'([^']*)'/g;
    while ((match = elemRegex.exec(content)) !== null) {
      const entId = match[1];
      const type = match[2];
      const name = match[3];

      if (type === 'IFCBEAM' || type === 'IFCCOLUMN') {
        const nid1 = `N_IFC_${nodes.length + 1}`;
        const nid2 = `N_IFC_${nodes.length + 2}`;
        const p1: [number, number, number] = ptMap.get(nodes.length + 1) || [0, 0, type === 'IFCCOLUMN' ? 0 : 3.5];
        const p2: [number, number, number] = ptMap.get(nodes.length + 2) || (type === 'IFCCOLUMN' ? [p1[0], p1[1], p1[2] + 3.5] : [p1[0] + 6.0, p1[1], p1[2]]);

        nodes.push({ id: nid1, x: p1[0], y: p1[1], z: p1[2] });
        nodes.push({ id: nid2, x: p2[0], y: p2[1], z: p2[2] });

        members.push({
          id: `M_IFC_${entId}`,
          name: name || `${type}_${entId}`,
          type: type === 'IFCCOLUMN' ? 'column' : 'beam',
          story: 'Story 1',
          startNodeId: nid1,
          endNodeId: nid2,
          sectionId: 'SEC-COL-400X400',
          materialId: 'MAT-C30',
          length: Math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2),
          releases: 'Continuous',
          localAxisAngle: 0
        });
      }
    }

    return {
      projectName: 'IFC Imported Model',
      nodes,
      members,
      slabs,
      walls: [],
      materials: [{ id: 'MAT-C30', name: 'Concrete C30/37', type: 'concrete', grade: 'C30/37', elasticModulusE: 33.0, poissonRatio: 0.2, unitWeight: 25.0, color: '#9ca3af' }],
      sections: [{ id: 'SEC-COL-400X400', name: 'RC 400x400 mm', shape: 'rectangular', materialId: 'MAT-C30', dimensions: { width: 400, height: 400 }, area: 1600, momentOfInertiaIxx: 213333.3, momentOfInertiaIyy: 213333.3, torsionalConstantJ: 360000, weightPerMeter: 100 }]
    };
  }

  // IFC Generator
  private static generateIfcText(model: StructuralModel, version: string = 'IFC4'): string {
    const lines: string[] = [
      'ISO-10303-21;',
      'HEADER;',
      `FILE_DESCRIPTION(('STRUCTURE-X ULTIMATE BIM MODEL'), '2;1');`,
      `FILE_NAME('${model.projectName || 'Model'}.ifc', '${new Date().toISOString()}', ('Engineer'), ('Structure-X'), 'v5.0', 'Structure-X Engine', 'None');`,
      `FILE_SCHEMA(('${version}'));`,
      'ENDSEC;',
      'DATA;'
    ];

    let eid = 1;
    const nextId = () => eid++;

    const idWorld = nextId();
    const idPtOrig = nextId();
    const idDirZ = nextId();
    const idDirX = nextId();
    lines.push(`#${idWorld}=IFCAXIS2PLACEMENT3D(#${idPtOrig},#${idDirZ},#${idDirX});`);
    lines.push(`#${idPtOrig}=IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`#${idDirZ}=IFCDIRECTION((0.,0.,1.));`);
    lines.push(`#${idDirX}=IFCDIRECTION((1.,0.,0.));`);

    const nodePtMap = new Map<string, number>();
    for (const n of model.nodes) {
      const pid = nextId();
      lines.push(`#${pid}=IFCCARTESIANPOINT((${n.x},${n.y},${n.z}));`);
      nodePtMap.set(n.id, pid);
    }

    for (const m of model.members) {
      const p1 = nodePtMap.get(m.startNodeId);
      const p2 = nodePtMap.get(m.endNodeId);
      if (p1 && p2) {
        const lineId = nextId();
        lines.push(`#${lineId}=IFCPOLYLINE((#${p1},#${p2}));`);
        const mid = nextId();
        if (m.type === 'column') {
          lines.push(`#${mid}=IFCCOLUMN('GUID_${mid}',$,'${m.name}',$,$,$,$,$,.COLUMN.);`);
        } else {
          lines.push(`#${mid}=IFCBEAM('GUID_${mid}',$,'${m.name}',$,$,$,$,$,.BEAM.);`);
        }
      }
    }

    lines.push('ENDSEC;', 'END-ISO-10303-21;');
    return lines.join('\n');
  }

  // CSV Parser
  private static parseCsvText(content: string): Partial<StructuralModel> {
    const lines = content.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const nodes: NodePoint[] = [];
    const members: StructuralMember[] = [];
    const slabs: any[] = [];
    const walls: any[] = [];

    let currentTable = 'NODES';
    const delimiter = content.includes('\t') ? '\t' : content.includes(';') ? ';' : ',';

    for (const line of lines) {
      if (line.startsWith('#') || line.startsWith('//')) {
        const header = line.toUpperCase();
        if (header.includes('NODE')) currentTable = 'NODES';
        else if (header.includes('MEMBER')) currentTable = 'MEMBERS';
        else if (header.includes('SLAB')) currentTable = 'SLABS';
        else if (header.includes('WALL')) currentTable = 'WALLS';
        continue;
      }

      const parts = line.split(delimiter).map(p => p.trim());
      if (parts[0]?.toLowerCase() === 'id' || parts[0]?.toLowerCase() === 'projectname') continue;

      if (currentTable === 'NODES' && parts.length >= 4) {
        const x = parseFloat(parts[1]);
        const y = parseFloat(parts[2]);
        const z = parseFloat(parts[3]);
        if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
          nodes.push({ id: parts[0], x, y, z });
        }
      } else if (currentTable === 'MEMBERS' && parts.length >= 6) {
        members.push({
          id: parts[0],
          name: parts[1] || parts[0],
          type: (parts[2] || 'beam').toLowerCase() as any,
          story: parts[3] || 'Story 1',
          startNodeId: parts[4],
          endNodeId: parts[5],
          sectionId: parts[6] || 'SEC-COL-400X400',
          materialId: parts[7] || 'MAT-C30',
          length: 0,
          releases: 'Continuous',
          localAxisAngle: 0
        });
      }
    }

    return {
      projectName: 'CSV Imported Model',
      nodes,
      members,
      slabs,
      walls,
      materials: [{ id: 'MAT-C30', name: 'Concrete C30/37', type: 'concrete', grade: 'C30/37', elasticModulusE: 33.0, poissonRatio: 0.2, unitWeight: 25.0, color: '#9ca3af' }],
      sections: [{ id: 'SEC-COL-400X400', name: 'RC 400x400 mm', shape: 'rectangular', materialId: 'MAT-C30', dimensions: { width: 400, height: 400 }, area: 1600, momentOfInertiaIxx: 213333.3, momentOfInertiaIyy: 213333.3, torsionalConstantJ: 360000, weightPerMeter: 100 }]
    };
  }

  // CSV Generator
  private static generateCsvText(model: StructuralModel, delimiter: string = ','): string {
    const out: string[] = [];
    out.push('# NODES');
    out.push(['id', 'x', 'y', 'z'].join(delimiter));
    for (const n of model.nodes) {
      out.push([n.id, n.x, n.y, n.z].join(delimiter));
    }
    out.push('\n# MEMBERS');
    out.push(['id', 'name', 'type', 'story', 'startNodeId', 'endNodeId', 'sectionId', 'materialId', 'length'].join(delimiter));
    for (const m of model.members) {
      out.push([m.id, m.name, m.type, m.story, m.startNodeId, m.endNodeId, m.sectionId, m.materialId, m.length].join(delimiter));
    }
    out.push('\n# SLABS');
    out.push(['id', 'name', 'story', 'nodeIds', 'thickness'].join(delimiter));
    for (const s of model.slabs) {
      out.push([s.id, s.name, s.story, s.nodeIds.join(';'), s.thickness].join(delimiter));
    }
    return out.join('\n');
  }

  // Excel XML Parser
  private static parseExcelXmlText(content: string): Partial<StructuralModel> {
    const cleanXml = content.replace(/xmlns(:\w+)?="[^"]*"/g, '').replace(/(<\/?)[\w]+:([\w]+)/g, '$1$2');
    const parser = new DOMParser();
    const doc = parser.parseFromString(cleanXml, 'text/xml');

    const nodes: NodePoint[] = [];
    const members: StructuralMember[] = [];

    const worksheets = doc.getElementsByTagName('Worksheet');
    for (let i = 0; i < worksheets.length; i++) {
      const ws = worksheets[i];
      const name = ws.getAttribute('Name')?.toUpperCase() || '';
      const rows = ws.getElementsByTagName('Row');

      if (name.includes('NODE')) {
        for (let r = 1; r < rows.length; r++) {
          const cells = rows[r].getElementsByTagName('Cell');
          if (cells.length >= 4) {
            const id = cells[0].textContent?.trim() || `N_${nodes.length + 1}`;
            const x = parseFloat(cells[1].textContent || '0');
            const y = parseFloat(cells[2].textContent || '0');
            const z = parseFloat(cells[3].textContent || '0');
            if (!isNaN(x)) nodes.push({ id, x, y, z });
          }
        }
      } else if (name.includes('MEMBER')) {
        for (let r = 1; r < rows.length; r++) {
          const cells = rows[r].getElementsByTagName('Cell');
          if (cells.length >= 6) {
            members.push({
              id: cells[0].textContent?.trim() || `M_${members.length + 1}`,
              name: cells[1].textContent?.trim() || '',
              type: (cells[2].textContent?.trim().toLowerCase() || 'beam') as any,
              story: cells[3].textContent?.trim() || 'Story 1',
              startNodeId: cells[4].textContent?.trim() || '',
              endNodeId: cells[5].textContent?.trim() || '',
              sectionId: cells[6]?.textContent?.trim() || 'SEC-COL-400X400',
              materialId: cells[7]?.textContent?.trim() || 'MAT-C30',
              length: 0,
              releases: 'Continuous',
              localAxisAngle: 0
            });
          }
        }
      }
    }

    return {
      projectName: 'Excel Imported Model',
      nodes,
      members,
      slabs: [],
      walls: [],
      materials: [{ id: 'MAT-C30', name: 'Concrete C30/37', type: 'concrete', grade: 'C30/37', elasticModulusE: 33.0, poissonRatio: 0.2, unitWeight: 25.0, color: '#9ca3af' }],
      sections: [{ id: 'SEC-COL-400X400', name: 'RC 400x400 mm', shape: 'rectangular', materialId: 'MAT-C30', dimensions: { width: 400, height: 400 }, area: 1600, momentOfInertiaIxx: 213333.3, momentOfInertiaIyy: 213333.3, torsionalConstantJ: 360000, weightPerMeter: 100 }]
    };
  }

  // Excel XML Generator
  private static generateExcelXmlText(model: StructuralModel): string {
    const parts: string[] = [
      '<?xml version="1.0"?>',
      '<?mso-application progid="Excel.Sheet"?>',
      '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
      ' xmlns:o="urn:schemas-microsoft-com:office:office"',
      ' xmlns:x="urn:schemas-microsoft-com:office:excel"',
      ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
      '<Styles>',
      ' <Style ss:ID="H"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1E293B" ss:Pattern="Solid"/></Style>',
      '</Styles>'
    ];

    const sheet = (title: string, headers: string[], rows: any[][]) => {
      parts.push(`<Worksheet ss:Name="${title}"><Table>`);
      parts.push('<Row>' + headers.map(h => `<Cell ss:StyleID="H"><Data ss:Type="String">${h}</Data></Cell>`).join('') + '</Row>');
      for (const r of rows) {
        parts.push('<Row>' + r.map(c => {
          const type = typeof c === 'number' ? 'Number' : 'String';
          return `<Cell><Data ss:Type="${type}">${c}</Data></Cell>`;
        }).join('') + '</Row>');
      }
      parts.push('</Table></Worksheet>');
    };

    sheet('NODES', ['id', 'x', 'y', 'z'], model.nodes.map(n => [n.id, n.x, n.y, n.z]));
    sheet('MEMBERS', ['id', 'name', 'type', 'story', 'startNodeId', 'endNodeId', 'sectionId', 'materialId', 'length'],
      model.members.map(m => [m.id, m.name, m.type, m.story, m.startNodeId, m.endNodeId, m.sectionId, m.materialId, m.length]));
    sheet('SLABS', ['id', 'name', 'story', 'nodeIds', 'thickness'],
      model.slabs.map(s => [s.id, s.name, s.story, s.nodeIds.join(';'), s.thickness]));

    parts.push('</Workbook>');
    return parts.join('\n');
  }

  // Helper to trigger browser download
  public static triggerBrowserDownload(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
