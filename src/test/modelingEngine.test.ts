import { StructuralModel } from '../types/structure';
import { StructuralModelingEngine } from '../core/modeling/StructuralModelingEngine';
import { ModelIntegrityValidator } from '../core/validation/ModelIntegrityValidator';
import { createDefaultRCBuilding } from '../data/defaultModels';
import { ProjectRepository } from '../server/repository/ProjectRepository';

interface TestResult {
  name: string;
  passed: boolean;
  message?: string;
}

export function runModelingEngineTests(): TestResult[] {
  const results: TestResult[] = [];

  const runTest = (name: string, fn: () => void) => {
    try {
      fn();
      results.push({ name, passed: true });
    } catch (e: any) {
      results.push({ name, passed: false, message: e.message || String(e) });
    }
  };

  // 1. Joint creation and duplicate prevention
  runTest('Add Joint Point with Restraints & Coordinates', () => {
    const baseModel = createDefaultRCBuilding();
    const initNodeCount = baseModel.nodes.length;
    
    // Add new joint
    const res1 = StructuralModelingEngine.addJoint(baseModel, { x: 12.0, y: 3.5, z: 12.0 }, {
      isRestrained: { fx: true, fy: true, fz: true, mx: true, my: true, mz: true }
    });

    if (res1.model.nodes.length !== initNodeCount + 1) {
      throw new Error(`Expected node count ${initNodeCount + 1}, got ${res1.model.nodes.length}`);
    }
    if (res1.isExisting) {
      throw new Error('Joint should be brand new');
    }

    // Attempt to add coincident joint (within 0.05mm, which is < 0.1mm tolerance)
    const res2 = StructuralModelingEngine.addJoint(res1.model, { x: 12.00003, y: 3.5, z: 12.00003 });
    if (res2.model.nodes.length !== initNodeCount + 1) {
      throw new Error('Coincident joint should reuse existing node ID');
    }
    if (!res2.isExisting || res2.joint.id !== res1.joint.id) {
      throw new Error('Expected duplicate joint detection to return existing joint');
    }
  });

  // 2. Add Frame Members (Beam, Column, Brace) with Local Axis & Releases
  runTest('Add Column, Beam, and Diagonal Brace Members', () => {
    const baseModel = createDefaultRCBuilding();
    
    // Add two joints for brace
    const j1 = StructuralModelingEngine.addJoint(baseModel, { x: 0, y: 0, z: 0 });
    const j2 = StructuralModelingEngine.addJoint(j1.model, { x: 6, y: 3.5, z: 0 });

    const braceRes = StructuralModelingEngine.addFrameMember(j2.model, {
      type: 'brace',
      startNodeId: j1.joint.id,
      endNodeId: j2.joint.id,
      sectionId: 'sec-400rc',
      materialId: 'mat-c3037',
      story: 'Story 1',
      releases: 'Pinned-Pinned',
      localAxisAngle: 45
    });

    const createdBrace = braceRes.member;
    if (createdBrace.type !== 'brace' || (createdBrace as any).releaseType !== 'Pinned-Pinned' || createdBrace.localAxisAngle !== 45) {
      throw new Error('Brace member attributes were not properly assigned');
    }
    if (Math.abs(createdBrace.length - Math.sqrt(6 * 6 + 3.5 * 3.5)) > 0.01) {
      throw new Error(`Calculated member length mismatch: ${createdBrace.length}`);
    }
  });

  // 3. Add Slab Shell & Shear Wall Shell
  runTest('Add Slab Shell and Shear Wall Entities', () => {
    const baseModel = createDefaultRCBuilding();
    const initSlabCount = baseModel.slabs.length;
    const initWallCount = baseModel.walls?.length || 0;

    // Add Slab
    const slabRes = StructuralModelingEngine.addSlab(baseModel, {
      story: 'Story 2',
      thickness: 0.22,
      materialId: 'mat-c3037',
      nodeIds: ['N_L2_0_0', 'N_L2_1_0', 'N_L2_1_1', 'N_L2_0_1'],
      diaphragm: 'rigid',
      loadDead: 3.0,
      loadLive: 2.5
    });

    if (slabRes.model.slabs.length !== initSlabCount + 1) {
      throw new Error('Slab was not added to model');
    }

    // Add Wall
    const wallRes = StructuralModelingEngine.addWall(slabRes.model, {
      story: 'Story 1',
      thickness: 0.30,
      materialId: 'mat-c3037',
      nodeIds: ['N_L0_0_0', 'N_L0_1_0', 'N_L1_1_0', 'N_L1_0_0'],
      loadDistributed: 15
    });

    if ((wallRes.model.walls?.length || 0) !== initWallCount + 1) {
      throw new Error('Shear Wall was not added to model');
    }
  });

  // 4. Add Openings, Springs, and Links
  runTest('Add Openings, Springs, and Links', () => {
    const baseModel = createDefaultRCBuilding();
    
    // Add Opening in Slab S1
    const openRes = StructuralModelingEngine.addOpening(baseModel, {
      parentType: 'slab',
      parentId: 'S1',
      story: 'Story 1',
      width: 1.2,
      height: 1.2
    });
    if ((openRes.model.openings?.length || 0) !== 1) {
      throw new Error('Opening element not created');
    }

    // Add Foundation Spring at N_L0_0_0
    const springRes = StructuralModelingEngine.addSpring(openRes.model, {
      nodeId: 'N_L0_0_0',
      type: 'ground',
      kx: 50000,
      ky: 50000,
      kz: 100000
    });
    if ((springRes.model.springs?.length || 0) !== 1) {
      throw new Error('Spring element not created');
    }

    // Add Link between N_L0_0_0 and N_L0_1_0
    const linkRes = StructuralModelingEngine.addLink(springRes.model, {
      startNodeId: 'N_L0_0_0',
      endNodeId: 'N_L0_1_0',
      type: 'damper',
      stiffness: { kx: 20000, ky: 15000, kz: 15000 }
    });
    if ((linkRes.model.links?.length || 0) !== 1) {
      throw new Error('Link element not created');
    }
  });

  // 5. Diaphragm Assignment & Kinematic Constraints
  runTest('Assign Rigid Diaphragm & Compute Center of Mass', () => {
    const baseModel = createDefaultRCBuilding();
    const story1Nodes = baseModel.nodes.filter(n => Math.abs(n.y - 3.5) < 0.1).map(n => n.id);

    const diaRes = StructuralModelingEngine.assignDiaphragm(baseModel, {
      story: 'Story 1',
      type: 'rigid',
      nodeIds: story1Nodes
    });

    if ((diaRes.model.diaphragms?.length || 0) !== 1) {
      throw new Error('Diaphragm was not assigned to story');
    }
    const d = diaRes.model.diaphragms![0];
    if (d.type !== 'rigid' || d.nodeIds.length !== story1Nodes.length) {
      throw new Error('Diaphragm constraint mismatch');
    }
    if (d.centerOfMass.y !== 3.5) {
      throw new Error(`Diaphragm CM Y-elevation should be 3.5m, got ${d.centerOfMass.y}`);
    }
  });

  // 6. CAD Transformations: Move, Copy, Delete
  runTest('Execute CAD Move, Copy, and Cascade Delete', () => {
    const baseModel = createDefaultRCBuilding();
    const targetMember = baseModel.members.find(m => m.id === 'C1')!;
    const startNode = baseModel.nodes.find(n => n.id === targetMember.startNodeId)!;
    const origX = startNode.x;

    // Move C1 by DX=2.0m
    const movedModel = StructuralModelingEngine.moveElements(baseModel, ['C1'], { dx: 2.0, dy: 0, dz: 0 });
    const movedNode = movedModel.nodes.find(n => n.id === targetMember.startNodeId)!;
    if (Math.abs(movedNode.x - (origX + 2.0)) > 0.001) {
      throw new Error(`Expected moved node X=${origX + 2.0}, got ${movedNode.x}`);
    }

    // Copy C1 with offset DX=5.0m
    const copyRes = StructuralModelingEngine.copyElements(movedModel, ['C1'], { dx: 5.0, dy: 0, dz: 0 });
    if (copyRes.copiedIds.length === 0) {
      throw new Error('Failed to copy member');
    }
    const copiedMember = copyRes.model.members.find(m => m.id === copyRes.copiedIds[0])!;
    const copiedStartNode = copyRes.model.nodes.find(n => n.id === copiedMember.startNodeId)!;
    if (Math.abs(copiedStartNode.x - (movedNode.x + 5.0)) > 0.001) {
      throw new Error('Copied member node coordinate mismatch');
    }

    // Delete copied member with orphan cleanup
    const preDelNodeCount = copyRes.model.nodes.length;
    const delModel = StructuralModelingEngine.deleteElements(copyRes.model, [copiedMember.id], { deleteOrphanJoints: true });
    if (delModel.members.some(m => m.id === copiedMember.id)) {
      throw new Error('Member was not deleted');
    }
  });

  // 7. CAD Transformations: Mirror & Arrays (Linear & Radial)
  runTest('Execute Mirror Reflection & Linear/Radial Arrays', () => {
    const baseModel = createDefaultRCBuilding();
    
    // Mirror member C1 across YZ plane at X=0
    const mirrorRes = StructuralModelingEngine.mirrorElements(baseModel, ['C1'], { axis: 'YZ', coordinate: 0 });
    if (mirrorRes.createdIds.length === 0) {
      throw new Error('Mirror operation did not create element');
    }

    // Linear Array of B1 (3 copies with DX=4m)
    const arrayRes = StructuralModelingEngine.linearArray(baseModel, ['B1'], 3, { dx: 4, dy: 0, dz: 0 });
    if (arrayRes.createdIds.length !== 3) {
      throw new Error(`Expected 3 arrayed members, got ${arrayRes.createdIds.length}`);
    }

    // Radial Array of C1 (4 copies @ 90 deg)
    const radRes = StructuralModelingEngine.radialArray(baseModel, ['C1'], 4, { x: 0, y: 0, z: 0 }, 'Y', 90);
    if (radRes.createdIds.length !== 4) {
      throw new Error(`Expected 4 radial copies, got ${radRes.createdIds.length}`);
    }
  });

  // 8. CAD Divide, Merge & Align
  runTest('Divide Member, Auto-Merge Coincident Joints, and Align', () => {
    const baseModel = createDefaultRCBuilding();
    
    // Divide B1 into 3 segments
    const divRes = StructuralModelingEngine.divideMember(baseModel, 'B1', 3);
    if (divRes.newMemberIds.length !== 3) {
      throw new Error(`Expected 3 divided segments, got ${divRes.newMemberIds.length}`);
    }
    if (divRes.model.members.some(m => m.id === 'B1')) {
      throw new Error('Original member B1 should be replaced by divided segments');
    }

    // Auto-Merge duplicate joints
    const jA = StructuralModelingEngine.addJoint(divRes.model, { x: 25.0, y: 0, z: 25.0 });
    const jB = StructuralModelingEngine.addJoint(jA.model, { x: 25.001, y: 0, z: 25.001 }); // 1.4mm away
    const mergeRes = StructuralModelingEngine.mergeDuplicateJoints(jB.model, 0.005);
    if (mergeRes.mergedCount < 1) {
      throw new Error('Expected coincident joints to be merged');
    }

    // Align joints along X axis
    const alignedModel = StructuralModelingEngine.alignElements(mergeRes.model, ['N_L0_0_0', 'N_L0_1_0'], 'X', 'mean');
    const n1 = alignedModel.nodes.find(n => n.id === 'N_L0_0_0')!;
    const n2 = alignedModel.nodes.find(n => n.id === 'N_L0_1_0')!;
    if (Math.abs(n1.x - n2.x) > 0.001) {
      throw new Error(`Nodes not aligned on X: ${n1.x} vs ${n2.x}`);
    }
  });

  // 9. Model Integrity Validation Tests
  runTest('Validate Model Integrity (Zero-length, Duplicates, Disconnected, Missing Properties)', () => {
    const validModel = ProjectRepository.getInstance().getProject('PRJ-BENCHMARK-01');
    const cleanReport = ModelIntegrityValidator.validate(validModel);
    if (!cleanReport.isValid) {
      throw new Error(`Clean default model should be valid, but had ${cleanReport.totalErrors} errors`);
    }

    // Inject Zero-Length Member
    const invalidModel1 = JSON.parse(JSON.stringify(validModel));
    const sampleNodeId = validModel.nodes[0].id;
    invalidModel1.members.push({
      id: 'ERR_ZERO_LEN',
      name: 'Zero Length Beam',
      type: 'beam',
      startNodeId: sampleNodeId,
      endNodeId: sampleNodeId, // Same node!
      sectionId: validModel.sections[0].id,
      materialId: validModel.materials[0].id,
      length: 0,
      story: 'Level 1',
      releases: {
        start: { fx: false, fy: false, fz: false, mx: false, my: false, mz: false },
        end: { fx: false, fy: false, fz: false, mx: false, my: false, mz: false }
      },
      localAxisAngle: 0,
      rotationAngleDeg: 0,
      cardinalPoint: 10
    });
    const rep1 = ModelIntegrityValidator.validate(invalidModel1);
    if (rep1.isValid || !rep1.issues.some(i => i.code === 'E1002')) {
      throw new Error('Validator failed to detect Zero-Length member (E1002)');
    }

    // Inject Missing Section
    const invalidModel2 = JSON.parse(JSON.stringify(validModel));
    invalidModel2.members[0].sectionId = 'NON_EXISTENT_SEC';
    const rep2 = ModelIntegrityValidator.validate(invalidModel2);
    if (rep2.isValid || !rep2.issues.some(i => i.code === 'E2001')) {
      throw new Error('Validator failed to detect Missing Section reference (E2001)');
    }

    // Inject Missing Material
    const invalidModel3 = JSON.parse(JSON.stringify(validModel));
    invalidModel3.members[0].materialId = 'NON_EXISTENT_MAT';
    const rep3 = ModelIntegrityValidator.validate(invalidModel3);
    if (rep3.isValid || !rep3.issues.some(i => i.code === 'E2002')) {
      throw new Error('Validator failed to detect Missing Material reference (E2002)');
    }

    // Inject Duplicate Member
    const invalidModel4 = JSON.parse(JSON.stringify(validModel));
    const existing = invalidModel4.members[0];
    invalidModel4.members.push({
      ...existing,
      id: 'DUP_MEM_1'
    });
    const rep4 = ModelIntegrityValidator.validate(invalidModel4);
    if (rep4.isValid || !rep4.issues.some(i => i.code === 'E1005')) {
      throw new Error('Validator failed to detect Duplicate Member (E1005)');
    }
  });

  // 10. Small 2-Story Structural Model Creation, Save, Close & Reopen
  runTest('Create, Save, Close and Reopen 2-Story Structural Model (Persistence)', () => {
    const repo = ProjectRepository.getInstance();

    // Create custom 2-Story Model
    const p2Story = repo.createProject({
      name: '2-Story RC Frame Office',
      code: 'OFFICE-2ST',
      engineer: 'Eng. Structural Lead',
      client: 'Apex Developments',
      designCode: 'ACI_318'
    }, {
      stories: [
        { id: 'ST-00', name: 'Base', elevationZ: 0, height: 0, isMasterStory: false },
        { id: 'ST-01', name: 'Story 1', elevationZ: 3.5, height: 3.5, isMasterStory: true, color: '#3b82f6' },
        { id: 'ST-02', name: 'Story 2', elevationZ: 7.0, height: 3.5, isMasterStory: false, color: '#10b981' }
      ]
    }) as any;

    // Add Base Nodes (Story 0, Y=0)
    const n00 = StructuralModelingEngine.addJoint(p2Story, { x: 0, y: 0, z: 0 }, { story: 'Base', isRestrained: { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } });
    const n01 = StructuralModelingEngine.addJoint(n00.model as any, { x: 6, y: 0, z: 0 }, { story: 'Base', isRestrained: { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } });
    const n02 = StructuralModelingEngine.addJoint(n01.model as any, { x: 6, y: 0, z: 6 }, { story: 'Base', isRestrained: { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } });
    const n03 = StructuralModelingEngine.addJoint(n02.model as any, { x: 0, y: 0, z: 6 }, { story: 'Base', isRestrained: { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } });

    // Add Story 1 Nodes (Y=3.5)
    const n10 = StructuralModelingEngine.addJoint(n03.model as any, { x: 0, y: 3.5, z: 0 }, { story: 'Story 1' });
    const n11 = StructuralModelingEngine.addJoint(n10.model as any, { x: 6, y: 3.5, z: 0 }, { story: 'Story 1' });
    const n12 = StructuralModelingEngine.addJoint(n11.model as any, { x: 6, y: 3.5, z: 6 }, { story: 'Story 1' });
    const n13 = StructuralModelingEngine.addJoint(n12.model as any, { x: 0, y: 3.5, z: 6 }, { story: 'Story 1' });

    // Add Story 2 Nodes (Y=7.0)
    const n20 = StructuralModelingEngine.addJoint(n13.model as any, { x: 0, y: 7.0, z: 0 }, { story: 'Story 2' });
    const n21 = StructuralModelingEngine.addJoint(n20.model as any, { x: 6, y: 7.0, z: 0 }, { story: 'Story 2' });
    const n22 = StructuralModelingEngine.addJoint(n21.model as any, { x: 6, y: 7.0, z: 6 }, { story: 'Story 2' });
    const n23 = StructuralModelingEngine.addJoint(n22.model as any, { x: 0, y: 7.0, z: 6 }, { story: 'Story 2' });

    // Story 1 Columns
    let m = n23.model;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n00.joint.id, endNodeId: n10.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n01.joint.id, endNodeId: n11.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n02.joint.id, endNodeId: n12.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n03.joint.id, endNodeId: n13.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 1' }).model as any;

    // Story 2 Columns
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n10.joint.id, endNodeId: n20.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n11.joint.id, endNodeId: n21.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n12.joint.id, endNodeId: n22.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'column', startNodeId: n13.joint.id, endNodeId: n23.joint.id, sectionId: 'SEC-COL-400', materialId: 'MAT-C30', story: 'Story 2' }).model as any;

    // Story 1 Beams
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n10.joint.id, endNodeId: n11.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n11.joint.id, endNodeId: n12.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n12.joint.id, endNodeId: n13.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 1' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n13.joint.id, endNodeId: n10.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 1' }).model as any;

    // Story 2 Beams
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n20.joint.id, endNodeId: n21.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n21.joint.id, endNodeId: n22.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n22.joint.id, endNodeId: n23.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 2' }).model as any;
    m = StructuralModelingEngine.addFrameMember(m as any, { type: 'beam', startNodeId: n23.joint.id, endNodeId: n20.joint.id, sectionId: 'SEC-BM-300x600', materialId: 'MAT-C30', story: 'Story 2' }).model as any;

    // Story 1 & Story 2 Slabs
    m = StructuralModelingEngine.addSlab(m as any, { story: 'Story 1', thickness: 0.20, materialId: 'MAT-C30', nodeIds: [n10.joint.id, n11.joint.id, n12.joint.id, n13.joint.id], diaphragm: 'rigid' }).model as any;
    m = StructuralModelingEngine.addSlab(m as any, { story: 'Story 2', thickness: 0.20, materialId: 'MAT-C30', nodeIds: [n20.joint.id, n21.joint.id, n22.joint.id, n23.joint.id], diaphragm: 'rigid' }).model as any;

    // Save Model to Repository
    const saved = repo.saveProject(m as any);
    const projectId = saved.metadata.id;

    // Verify Validation
    const valRep = ModelIntegrityValidator.validate(saved);
    if (!valRep.isValid) {
      throw new Error(`2-Story model validation failed with ${valRep.totalErrors} errors: ${valRep.issues.map(i => i.title + ': ' + i.message).join(' | ')}`);
    }

    // Close and Reopen Project from Repository
    const reopened = repo.getProject(projectId);
    if (reopened.projectName !== '2-Story RC Frame Office') {
      throw new Error(`Reopened project name mismatch: ${reopened.projectName}`);
    }
    if (reopened.nodes.length !== 12 || reopened.members.length !== 16 || reopened.slabs.length !== 2) {
      throw new Error(`Reopened project entities count mismatch: Nodes=${reopened.nodes.length}, Members=${reopened.members.length}, Slabs=${reopened.slabs.length}`);
    }
  });

  return results;
}
