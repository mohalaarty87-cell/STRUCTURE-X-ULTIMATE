import { StructuralModel } from '../../types/domain';
import { EngineeringError, EngineeringErrorPayload } from '../errors/EngineeringError';
import { StructuralModelSchema } from '../schema/structuralModelSchema';

export interface ValidationReport {
  isValid: boolean;
  canAnalyze: boolean;
  totalErrors: number;
  totalWarnings: number;
  issues: EngineeringErrorPayload[];
}

export class ModelIntegrityValidator {
  public static validate(model: StructuralModel): ValidationReport {
    const issues: EngineeringErrorPayload[] = [];

    // 1. Schema-level validation (optional check)
    if (model.metadata && model.gridSystem) {
      const schemaResult = StructuralModelSchema.safeParse(model);
      if (!schemaResult.success) {
        const errorMsg = schemaResult.error.issues.map(i => `${i.path.join('.')}: ${i.message}`).join('; ');
        issues.push(
          new EngineeringError('E5001', {
            details: errorMsg,
            customMessage: `Model schema mismatch: ${errorMsg}`
          }).toJSON()
        );
      }
    }

    // 2. Index maps
    const nodeMap = new Map(model.nodes.map(n => [n.id, n]));
    const sectionMap = new Map(model.sections.map(s => [s.id, s]));
    const materialMap = new Map(model.materials.map(m => [m.id, m]));
    const connectedNodeIds = new Set<string>();

    // 3. Duplicate Joints Validation (tolerance = 1mm)
    for (let i = 0; i < model.nodes.length; i++) {
      const n1 = model.nodes[i];
      for (let j = i + 1; j < model.nodes.length; j++) {
        const n2 = model.nodes[j];
        const dx = n1.x - n2.x;
        const dy = n1.y - n2.y;
        const dz = n1.z - n2.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist < 1e-3) {
          issues.push(
            new EngineeringError('E1003', {
              objectId: n1.name || n1.id,
              targetId: n2.name || n2.id,
              customMessage: `Duplicate/Coincident joints detected: "${n1.id}" and "${n2.id}" at coordinates (${n1.x}, ${n1.y}, ${n1.z}).`
            }).toJSON()
          );
        }
      }
    }

    // 4. Section & Material checks
    for (const sec of model.sections) {
      if (!materialMap.has(sec.materialId)) {
        issues.push(
          new EngineeringError('E2002', {
            objectId: sec.name || sec.id,
            objectType: 'section',
            targetId: sec.materialId
          }).toJSON()
        );
      }
      if (sec.area <= 0 || sec.momentOfInertiaIxx <= 0) {
        issues.push(
          new EngineeringError('E2003', {
            objectId: sec.name || sec.id,
            objectType: 'section',
            context: { area: sec.area, Ixx: sec.momentOfInertiaIxx }
          }).toJSON()
        );
      }
    }

    // 5. Member Geometry, Duplicate Elements, Zero-Length, Section/Material Checks
    const memberPairMap = new Map<string, string>(); // key "nodeA_nodeB" -> memberId

    for (const member of model.members) {
      const startNode = nodeMap.get(member.startNodeId);
      const endNode = nodeMap.get(member.endNodeId);

      // Disconnected element / missing nodes
      if (!startNode || !endNode) {
        issues.push(
          new EngineeringError('E1006', {
            objectId: member.id,
            objectType: 'member',
            targetId: !startNode ? member.startNodeId : member.endNodeId,
            details: `Member references non-existent node (Start: ${member.startNodeId}, End: ${member.endNodeId})`
          }).toJSON()
        );
        continue;
      }

      connectedNodeIds.add(member.startNodeId);
      connectedNodeIds.add(member.endNodeId);

      // Check zero length
      const dx = endNode.x - startNode.x;
      const dy = endNode.y - startNode.y;
      const dz = endNode.z - startNode.z;
      const calculatedLength = Math.sqrt(dx * dx + dy * dy + dz * dz);

      if (calculatedLength < 1e-4) {
        issues.push(
          new EngineeringError('E1002', {
            objectId: member.id,
            objectType: 'member',
            customMessage: `Zero-length frame member "${member.id}" detected (Length = ${calculatedLength.toFixed(5)}m).`
          }).toJSON()
        );
      }

      // Check duplicate elements
      const pairKey = [member.startNodeId, member.endNodeId].sort().join('_');
      if (memberPairMap.has(pairKey)) {
        const existingMemberId = memberPairMap.get(pairKey)!;
        issues.push(
          new EngineeringError('E1005', {
            objectId: member.id,
            targetId: existingMemberId,
            customMessage: `Duplicate frame member detected: "${member.id}" shares identical joints with "${existingMemberId}".`
          }).toJSON()
        );
      } else {
        memberPairMap.set(pairKey, member.id);
      }

      // Check section assignment
      if (!sectionMap.has(member.sectionId)) {
        issues.push(
          new EngineeringError('E2001', {
            objectId: member.id,
            objectType: 'member',
            targetId: member.sectionId
          }).toJSON()
        );
      }

      // Check material assignment
      if (member.materialId && !materialMap.has(member.materialId)) {
        issues.push(
          new EngineeringError('E2002', {
            objectId: member.id,
            objectType: 'member',
            targetId: member.materialId
          }).toJSON()
        );
      }
    }

    // 6. Slab & Wall Geometry Checks (Collinear, polygon vertices, zero area)
    for (const slab of model.slabs) {
      if (slab.nodeIds.length < 3) {
        issues.push(
          new EngineeringError('E1004', {
            objectId: slab.id,
            objectType: 'slab',
            details: 'Slab polygon must contain at least 3 vertices.'
          }).toJSON()
        );
      }

      let hasMissingVertex = false;
      const polygonPoints: { x: number; y: number; z: number }[] = [];

      for (const nid of slab.nodeIds) {
        const node = nodeMap.get(nid);
        if (!node) {
          hasMissingVertex = true;
          issues.push(
            new EngineeringError('E1006', {
              objectId: slab.id,
              objectType: 'slab',
              targetId: nid,
              details: `Slab references missing boundary vertex ${nid}`
            }).toJSON()
          );
        } else {
          connectedNodeIds.add(nid);
          polygonPoints.push(node);
        }
      }

      // Check for collinearity or degenerate zero area if all vertices exist
      if (!hasMissingVertex && polygonPoints.length >= 3) {
        // Compute 3D polygon area using cross product summation
        let ax = 0, ay = 0, az = 0;
        const n = polygonPoints.length;
        for (let i = 0; i < n; i++) {
          const p1 = polygonPoints[i];
          const p2 = polygonPoints[(i + 1) % n];
          ax += p1.y * p2.z - p1.z * p2.y;
          ay += p1.z * p2.x - p1.x * p2.z;
          az += p1.x * p2.y - p1.y * p2.x;
        }
        const polyArea = 0.5 * Math.sqrt(ax * ax + ay * ay + az * az);

        if (polyArea < 1e-5) {
          issues.push(
            new EngineeringError('E1007', {
              objectId: slab.id,
              objectType: 'slab',
              details: `Slab polygon has degenerate/collinear geometry with near-zero area (${polyArea.toFixed(6)} m²)`
            }).toJSON()
          );
        }
      }

      // Check material assignment
      if (slab.materialId && !materialMap.has(slab.materialId)) {
        issues.push(
          new EngineeringError('E2002', {
            objectId: slab.id,
            objectType: 'slab',
            targetId: slab.materialId
          }).toJSON()
        );
      }
    }

    // 7. Orphan node check (warning)
    for (const node of model.nodes) {
      if (!connectedNodeIds.has(node.id) && !node.isRestrained) {
        issues.push(
          new EngineeringError('E1001', {
            objectId: node.name || node.id,
            objectType: 'node'
          }).toJSON()
        );
      }
    }

    // 8. Base support restraint check
    const restrainedNodes = model.nodes.filter(n => n.isRestrained);
    if (restrainedNodes.length === 0) {
      issues.push(
        new EngineeringError('E3001', {
          objectType: 'node'
        }).toJSON()
      );
    }

    // 9. Load pattern check
    if (model.loadPatterns && model.loadPatterns.length === 0) {
      issues.push(
        new EngineeringError('E4001', {
          objectType: 'load_pattern'
        }).toJSON()
      );
    }

    const totalErrors = issues.filter(i => i.severity === 'ERROR' || i.severity === 'CRITICAL').length;
    const totalWarnings = issues.filter(i => i.severity === 'WARNING').length;

    return {
      isValid: totalErrors === 0,
      canAnalyze: totalErrors === 0 && restrainedNodes.length > 0,
      totalErrors,
      totalWarnings,
      issues
    };
  }
}

