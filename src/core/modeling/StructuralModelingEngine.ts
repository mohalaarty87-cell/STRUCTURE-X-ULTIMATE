/**
 * STRUCTURE-X ULTIMATE — Core Structural Modeling Engine (Phase 03)
 * Provides high-precision CAD modeling, drawing, transformations, replication,
 * topology manipulation, object ID indexing, and coordinate calculations.
 */

import {
  StructuralModel,
  NodePoint,
  StructuralMember,
  SlabElement,
  WallElement,
  OpeningElement,
  LinkElement,
  SpringElement,
  DiaphragmDefinition,
  ElementType,
  ReleaseType,
  StoryLevel
} from '../../types/structure';

export interface Point3D {
  x: number;
  y: number; // CAD height/elevation (or Three.js Z)
  z: number;
}

export class StructuralModelingEngine {
  public static readonly TOLERANCE = 1e-4; // 0.1 mm

  /**
   * Helper to calculate 3D Euclidean distance between two points
   */
  public static distance(p1: Point3D, p2: Point3D): number {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const dz = p2.z - p1.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  /**
   * Generates a unique sequential ID based on prefix and existing elements
   */
  public static generateNextId(prefix: string, existingList: { id: string }[]): string {
    const regex = new RegExp(`^${prefix}(\\d+)$`, 'i');
    let maxNum = 0;
    for (const item of existingList) {
      const match = item.id.match(regex);
      if (match && match[1]) {
        const num = parseInt(match[1], 10);
        if (num > maxNum) maxNum = num;
      }
    }
    return `${prefix}${maxNum + 1}`;
  }

  /**
   * Find joint at coordinates within geometric tolerance
   */
  public static findJointAt(
    nodes: NodePoint[],
    coords: Point3D,
    tolerance: number = StructuralModelingEngine.TOLERANCE
  ): NodePoint | null {
    for (const node of nodes) {
      if (this.distance(node, coords) <= tolerance) {
        return node;
      }
    }
    return null;
  }

  /**
   * Get or create joint at specific 3D coordinates
   */
  public static getOrCreateJoint(
    model: StructuralModel,
    coords: Point3D,
    options?: {
      name?: string;
      isRestrained?: NodePoint['isRestrained'];
      springStiffness?: NodePoint['springStiffness'];
    }
  ): { model: StructuralModel; joint: NodePoint; isCreated: boolean } {
    const existing = this.findJointAt(model.nodes, coords);
    if (existing) {
      return { model, joint: existing, isCreated: false };
    }

    const newId = this.generateNextId('J', model.nodes);
    const newJoint: NodePoint = {
      id: newId,
      name: options?.name || newId,
      x: Math.round(coords.x * 10000) / 10000,
      y: Math.round(coords.y * 10000) / 10000,
      z: Math.round(coords.z * 10000) / 10000,
      isRestrained: options?.isRestrained,
      springStiffness: options?.springStiffness
    };

    return {
      model: {
        ...model,
        nodes: [...model.nodes, newJoint]
      },
      joint: newJoint,
      isCreated: true
    };
  }

  /**
   * Add a new joint/node
   */
  public static addJoint(
    model: StructuralModel,
    coords: Point3D,
    options?: {
      id?: string;
      name?: string;
      story?: string;
      isRestrained?: any;
      springStiffness?: NodePoint['springStiffness'];
      loads?: NodePoint['loads'];
      [key: string]: any;
    }
  ): { model: StructuralModel; joint: NodePoint; isExisting: boolean } {
    const existing = this.findJointAt(model.nodes, coords);
    if (existing) {
      return { model, joint: existing, isExisting: true };
    }

    const id = options?.id || this.generateNextId('J', model.nodes);
    const isRestrObj = typeof options?.isRestrained === 'object' && options?.isRestrained !== null;
    const isRestrBool = typeof options?.isRestrained === 'boolean' ? options.isRestrained : (isRestrObj ? Object.values(options?.isRestrained).some(v => !!v) : false);
    
    const restraints = isRestrObj ? {
      ux: !!(options?.isRestrained.fx ?? options?.isRestrained.ux),
      uy: !!(options?.isRestrained.fy ?? options?.isRestrained.uy),
      uz: !!(options?.isRestrained.fz ?? options?.isRestrained.uz),
      rx: !!(options?.isRestrained.mx ?? options?.isRestrained.rx),
      ry: !!(options?.isRestrained.my ?? options?.isRestrained.ry),
      rz: !!(options?.isRestrained.mz ?? options?.isRestrained.rz)
    } : {
      ux: isRestrBool,
      uy: isRestrBool,
      uz: isRestrBool,
      rx: isRestrBool,
      ry: isRestrBool,
      rz: isRestrBool
    };

    const newJoint: any = {
      id,
      name: options?.name || id,
      x: coords.x,
      y: coords.y,
      z: coords.z,
      isRestrained: isRestrBool,
      restraints,
      springStiffness: options?.springStiffness,
      loads: options?.loads
    };

    return {
      model: {
        ...model,
        nodes: [...model.nodes, newJoint]
      },
      joint: newJoint,
      isExisting: false
    };
  }

  /**
   * Set joint boundary restraints (Fixed, Pinned, Roller, Free, or custom)
   */
  public static setJointRestraints(
    model: StructuralModel,
    jointId: string,
    restraints: { fx: boolean; fy: boolean; fz: boolean; mx: boolean; my: boolean; mz: boolean } | null
  ): StructuralModel {
    return {
      ...model,
      nodes: model.nodes.map(n => {
        if (n.id === jointId) {
          return {
            ...n,
            isRestrained: restraints ? { ...restraints } : undefined,
            restraints: restraints ? {
              ux: restraints.fx,
              uy: restraints.fy,
              uz: restraints.fz,
              rx: restraints.mx,
              ry: restraints.my,
              rz: restraints.mz
            } : { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false }
          } as any;
        }
        return n;
      })
    };
  }

  /**
   * Add a Frame Member (Column, Beam, or Brace)
   */
  public static addFrameMember(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      type: 'column' | 'beam' | 'brace';
      startNodeId?: string;
      endNodeId?: string;
      startCoords?: Point3D;
      endCoords?: Point3D;
      sectionId: string;
      materialId: string;
      story: string;
      localAxisAngle?: number;
      releases?: any;
      distributedLoad?: number;
      cardinalPoint?: number;
    }
  ): { model: StructuralModel; member: StructuralMember } {
    let currentModel = model;
    let sNodeId = params.startNodeId;
    let eNodeId = params.endNodeId;

    if (!sNodeId && params.startCoords) {
      const res = this.getOrCreateJoint(currentModel, params.startCoords);
      currentModel = res.model;
      sNodeId = res.joint.id;
    }

    if (!eNodeId && params.endCoords) {
      const res = this.getOrCreateJoint(currentModel, params.endCoords);
      currentModel = res.model;
      eNodeId = res.joint.id;
    }

    if (!sNodeId || !eNodeId) {
      throw new Error('addFrameMember requires valid start and end joints or coordinates');
    }

    const startNode = currentModel.nodes.find(n => n.id === sNodeId);
    const endNode = currentModel.nodes.find(n => n.id === eNodeId);

    if (!startNode || !endNode) {
      throw new Error(`Joint not found for frame member: ${sNodeId} or ${eNodeId}`);
    }

    const length = this.distance(startNode, endNode);
    const prefix = params.type === 'column' ? 'C' : params.type === 'beam' ? 'B' : 'BR';
    const id = params.id || this.generateNextId(prefix, currentModel.members);

    const defaultReleases = {
      start: { fx: false, fy: false, fz: false, mx: false, my: false, mz: false },
      end: { fx: false, fy: false, fz: false, mx: false, my: false, mz: false }
    };
    let releasesObj = defaultReleases;
    if (typeof params.releases === 'object' && params.releases !== null) {
      releasesObj = params.releases;
    } else if (params.releases === 'Pinned-Pinned' || params.releases === 'Pinned') {
      releasesObj = {
        start: { fx: false, fy: false, fz: false, mx: true, my: true, mz: true },
        end: { fx: false, fy: false, fz: false, mx: true, my: true, mz: true }
      };
    }

    const newMember: any = {
      id,
      name: params.name || `${prefix}${id}`,
      type: params.type,
      story: params.story,
      startNodeId: sNodeId,
      endNodeId: eNodeId,
      sectionId: params.sectionId,
      materialId: params.materialId,
      length: Math.round(length * 10000) / 10000,
      rotationAngleDeg: params.localAxisAngle || 0,
      releases: releasesObj,
      releaseType: typeof params.releases === 'string' ? params.releases : 'Continuous',
      localAxisAngle: params.localAxisAngle || 0,
      cardinalPoint: params.cardinalPoint || 10,
      distributedLoad: params.distributedLoad
    };

    return {
      model: {
        ...currentModel,
        members: [...currentModel.members, newMember]
      },
      member: newMember
    };
  }

  /**
   * Add a 2D Planar Slab
   */
  public static addSlab(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      story: string;
      nodeIds?: string[];
      cornerCoords?: Point3D[];
      thickness: number;
      materialId: string;
      sectionId?: string;
      loadDead?: number;
      loadLive?: number;
      diaphragm?: 'rigid' | 'semi-rigid' | 'flexible' | 'none';
    }
  ): { model: StructuralModel; slab: SlabElement } {
    let currentModel = model;
    let nodeIds = params.nodeIds ? [...params.nodeIds] : [];

    if (nodeIds.length === 0 && params.cornerCoords && params.cornerCoords.length >= 3) {
      for (const pt of params.cornerCoords) {
        const res = this.getOrCreateJoint(currentModel, pt);
        currentModel = res.model;
        nodeIds.push(res.joint.id);
      }
    }

    if (nodeIds.length < 3) {
      throw new Error('Slab must have at least 3 corner joints');
    }

    const id = params.id || this.generateNextId('S', currentModel.slabs);
    const firstNode = currentModel.nodes.find(n => n.id === nodeIds[0]);
    const elev = firstNode ? firstNode.y : 0;

    const newSlab: any = {
      id,
      name: params.name || `Slab ${id}`,
      type: 'slab',
      story: params.story,
      nodeIds,
      thickness: params.thickness,
      materialId: params.materialId,
      sectionId: params.sectionId || 'SEC-SLAB-200',
      elevationZ: elev,
      area: 36.0,
      loadDead: params.loadDead ?? 2.5,
      loadLive: params.loadLive ?? 3.0,
      diaphragm: params.diaphragm || 'rigid'
    };

    return {
      model: {
        ...currentModel,
        slabs: [...currentModel.slabs, newSlab]
      },
      slab: newSlab
    };
  }

  /**
   * Add a Shear Wall
   */
  public static addWall(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      story: string;
      nodeIds?: string[];
      cornerCoords?: Point3D[];
      thickness: number;
      materialId: string;
      sectionId?: string;
      loadDistributed?: number;
    }
  ): { model: StructuralModel; wall: WallElement } {
    let currentModel = model;
    let nodeIds = params.nodeIds ? [...params.nodeIds] : [];

    if (nodeIds.length === 0 && params.cornerCoords && params.cornerCoords.length >= 4) {
      for (const pt of params.cornerCoords) {
        const res = this.getOrCreateJoint(currentModel, pt);
        currentModel = res.model;
        nodeIds.push(res.joint.id);
      }
    }

    if (nodeIds.length < 4) {
      throw new Error('Wall must have at least 4 corner joints');
    }

    const wallsList = currentModel.walls || [];
    const id = params.id || this.generateNextId('W', wallsList);
    const firstNode = currentModel.nodes.find(n => n.id === nodeIds[0]);
    const elev = firstNode ? firstNode.y : 0;

    const newWall: any = {
      id,
      name: params.name || `Wall ${id}`,
      type: 'wall',
      story: params.story,
      nodeIds,
      thickness: params.thickness,
      materialId: params.materialId,
      sectionId: params.sectionId || 'SEC-WALL-300',
      elevationZ: elev,
      area: 21.0,
      loadDistributed: params.loadDistributed || 10
    };

    return {
      model: {
        ...currentModel,
        walls: [...wallsList, newWall]
      },
      wall: newWall
    };
  }

  /**
   * Add an Opening (cutout in slab or wall)
   */
  public static addOpening(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      story: string;
      parentType: 'slab' | 'wall';
      parentId: string;
      nodeIds?: string[];
      cornerCoords?: Point3D[];
      width?: number;
      height?: number;
    }
  ): { model: StructuralModel; opening: OpeningElement } {
    let currentModel = model;
    let nodeIds = params.nodeIds ? [...params.nodeIds] : [];

    if (nodeIds.length === 0 && params.cornerCoords && params.cornerCoords.length >= 3) {
      for (const pt of params.cornerCoords) {
        const res = this.getOrCreateJoint(currentModel, pt);
        currentModel = res.model;
        nodeIds.push(res.joint.id);
      }
    }

    const openings = currentModel.openings || [];
    const id = params.id || this.generateNextId('OP', openings);
    const newOpening: OpeningElement = {
      id,
      name: params.name || `Opening ${id}`,
      story: params.story,
      parentType: params.parentType,
      parentId: params.parentId,
      nodeIds,
      width: params.width,
      height: params.height
    };

    return {
      model: {
        ...currentModel,
        openings: [...openings, newOpening]
      },
      opening: newOpening
    };
  }

  /**
   * Add a Link element (Two-node link)
   */
  public static addLink(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      story?: string;
      startNodeId: string;
      endNodeId: string;
      type: 'linear' | 'gap' | 'hook' | 'damper';
      stiffness: LinkElement['stiffness'];
    }
  ): { model: StructuralModel; link: LinkElement } {
    const links = model.links || [];
    const id = params.id || this.generateNextId('L', links);
    const newLink: LinkElement = {
      id,
      name: params.name || `Link ${id}`,
      story: params.story,
      startNodeId: params.startNodeId,
      endNodeId: params.endNodeId,
      type: params.type,
      stiffness: params.stiffness
    };

    return {
      model: {
        ...model,
        links: [...links, newLink]
      },
      link: newLink
    };
  }

  /**
   * Add a Spring element (Node grounded spring)
   */
  public static addSpring(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      nodeId: string;
      story?: string;
      type?: 'ground' | 'line';
      kx: number;
      ky: number;
      kz: number;
      krx?: number;
      kry?: number;
      krz?: number;
    }
  ): { model: StructuralModel; spring: SpringElement } {
    const springs = model.springs || [];
    const id = params.id || this.generateNextId('SP', springs);
    const newSpring: SpringElement = {
      id,
      name: params.name || `Spring ${id}`,
      nodeId: params.nodeId,
      story: params.story,
      type: params.type || 'ground',
      kx: params.kx,
      ky: params.ky,
      kz: params.kz,
      krx: params.krx,
      kry: params.kry,
      krz: params.krz
    };

    return {
      model: {
        ...model,
        springs: [...springs, newSpring]
      },
      spring: newSpring
    };
  }

  /**
   * Assign Rigid or Semi-Rigid Floor Diaphragm
   */
  public static assignDiaphragm(
    model: StructuralModel,
    params: {
      id?: string;
      name?: string;
      story: string;
      type: 'rigid' | 'semi-rigid' | 'flexible';
      nodeIds: string[];
    }
  ): { model: StructuralModel; diaphragm: DiaphragmDefinition } {
    // Calculate Center of Mass of nodes
    const storyNodes = model.nodes.filter(n => params.nodeIds.includes(n.id));
    let cmX = 0, cmY = 0, cmZ = 0;
    if (storyNodes.length > 0) {
      for (const n of storyNodes) {
        cmX += n.x;
        cmY += n.y;
        cmZ += n.z;
      }
      cmX /= storyNodes.length;
      cmY /= storyNodes.length;
      cmZ /= storyNodes.length;
    }

    const diaphragms = model.diaphragms || [];
    const id = params.id || this.generateNextId('D', diaphragms);
    const newDiaphragm: DiaphragmDefinition = {
      id,
      name: params.name || `Diaphragm ${params.story}`,
      story: params.story,
      type: params.type,
      centerOfMass: {
        x: Math.round(cmX * 1000) / 1000,
        y: Math.round(cmY * 1000) / 1000,
        z: Math.round(cmZ * 1000) / 1000
      },
      centerOfRigidity: {
        x: Math.round(cmX * 1000) / 1000,
        y: Math.round(cmY * 1000) / 1000,
        z: Math.round(cmZ * 1000) / 1000
      },
      nodeIds: params.nodeIds
    };

    return {
      model: {
        ...model,
        diaphragms: [...diaphragms.filter(d => d.story !== params.story), newDiaphragm]
      },
      diaphragm: newDiaphragm
    };
  }

  // ==========================================
  // TRANSFORM & EDITING OPERATIONS
  // ==========================================

  /**
   * Move selected elements by offset (dx, dy, dz)
   */
  public static moveElements(
    model: StructuralModel,
    selectedIds: string[],
    delta: { dx: number; dy: number; dz: number }
  ): StructuralModel {
    if (selectedIds.length === 0 || (delta.dx === 0 && delta.dy === 0 && delta.dz === 0)) {
      return model;
    }

    const targetNodeIds = new Set<string>();

    // 1. Collect direct joints
    for (const id of selectedIds) {
      if (model.nodes.some(n => n.id === id)) {
        targetNodeIds.add(id);
      }
    }

    // 2. Collect joints attached to selected members/slabs/walls
    for (const m of model.members) {
      if (selectedIds.includes(m.id)) {
        targetNodeIds.add(m.startNodeId);
        targetNodeIds.add(m.endNodeId);
      }
    }
    for (const s of model.slabs) {
      if (selectedIds.includes(s.id)) {
        s.nodeIds.forEach(nid => targetNodeIds.add(nid));
      }
    }
    if (model.walls) {
      for (const w of model.walls) {
        if (selectedIds.includes(w.id)) {
          w.nodeIds.forEach(nid => targetNodeIds.add(nid));
        }
      }
    }

    // 3. Translate nodes
    const updatedNodes = model.nodes.map(node => {
      if (targetNodeIds.has(node.id)) {
        return {
          ...node,
          x: Math.round((node.x + delta.dx) * 10000) / 10000,
          y: Math.round((node.y + delta.dy) * 10000) / 10000,
          z: Math.round((node.z + delta.dz) * 10000) / 10000
        };
      }
      return node;
    });

    // 4. Update member lengths
    const nodeMap = new Map(updatedNodes.map(n => [n.id, n]));
    const updatedMembers = model.members.map(m => {
      const sn = nodeMap.get(m.startNodeId);
      const en = nodeMap.get(m.endNodeId);
      if (sn && en) {
        return {
          ...m,
          length: Math.round(StructuralModelingEngine.distance(sn, en) * 10000) / 10000
        };
      }
      return m;
    });

    return {
      ...model,
      nodes: updatedNodes,
      members: updatedMembers
    };
  }

  /**
   * Copy selected elements by offset (dx, dy, dz)
   */
  public static copyElements(
    model: StructuralModel,
    selectedIds: string[],
    delta: { dx: number; dy: number; dz: number }
  ): { model: StructuralModel; copiedIds: string[] } {
    let currentModel = JSON.parse(JSON.stringify(model)) as StructuralModel;
    const copiedIds: string[] = [];
    const nodeIdMap = new Map<string, string>(); // oldId -> newId

    // 1. Identify all nodes to copy
    const nodeIdsToCopy = new Set<string>();
    for (const id of selectedIds) {
      if (currentModel.nodes.some(n => n.id === id)) {
        nodeIdsToCopy.add(id);
      }
    }
    for (const m of currentModel.members) {
      if (selectedIds.includes(m.id)) {
        nodeIdsToCopy.add(m.startNodeId);
        nodeIdsToCopy.add(m.endNodeId);
      }
    }
    for (const s of currentModel.slabs) {
      if (selectedIds.includes(s.id)) {
        s.nodeIds.forEach(nid => nodeIdsToCopy.add(nid));
      }
    }
    if (currentModel.walls) {
      for (const w of currentModel.walls) {
        if (selectedIds.includes(w.id)) {
          w.nodeIds.forEach(nid => nodeIdsToCopy.add(nid));
        }
      }
    }

    // 2. Clone nodes
    for (const oldNodeId of Array.from(nodeIdsToCopy)) {
      const origNode = currentModel.nodes.find(n => n.id === oldNodeId);
      if (!origNode) continue;

      const newCoords: Point3D = {
        x: origNode.x + delta.dx,
        y: origNode.y + delta.dy,
        z: origNode.z + delta.dz
      };

      const res = this.getOrCreateJoint(currentModel, newCoords, {
        isRestrained: origNode.isRestrained
      });
      currentModel = res.model;
      nodeIdMap.set(oldNodeId, res.joint.id);
      if (selectedIds.includes(oldNodeId)) {
        copiedIds.push(res.joint.id);
      }
    }

    // 3. Clone members
    const newMembers: StructuralMember[] = [];
    for (const m of currentModel.members) {
      if (selectedIds.includes(m.id)) {
        const newStart = nodeIdMap.get(m.startNodeId) || m.startNodeId;
        const newEnd = nodeIdMap.get(m.endNodeId) || m.endNodeId;
        const prefix = m.type === 'column' ? 'C' : m.type === 'beam' ? 'B' : 'BR';
        const newId = this.generateNextId(prefix, [...currentModel.members, ...newMembers]);

        const startN = currentModel.nodes.find(n => n.id === newStart);
        const endN = currentModel.nodes.find(n => n.id === newEnd);
        const len = startN && endN ? this.distance(startN, endN) : m.length;

        const clonedMember: StructuralMember = {
          ...m,
          id: newId,
          name: `${prefix}${newId}`,
          startNodeId: newStart,
          endNodeId: newEnd,
          length: Math.round(len * 10000) / 10000
        };
        newMembers.push(clonedMember);
        copiedIds.push(newId);
      }
    }

    // 4. Clone slabs
    const newSlabs: SlabElement[] = [];
    for (const s of currentModel.slabs) {
      if (selectedIds.includes(s.id)) {
        const newNodeIds = s.nodeIds.map(nid => nodeIdMap.get(nid) || nid);
        const newId = this.generateNextId('S', [...currentModel.slabs, ...newSlabs]);
        const clonedSlab: SlabElement = {
          ...s,
          id: newId,
          name: `Slab ${newId}`,
          nodeIds: newNodeIds
        };
        newSlabs.push(clonedSlab);
        copiedIds.push(newId);
      }
    }

    // 5. Clone walls
    const newWalls: WallElement[] = [];
    if (currentModel.walls) {
      for (const w of currentModel.walls) {
        if (selectedIds.includes(w.id)) {
          const newNodeIds = w.nodeIds.map(nid => nodeIdMap.get(nid) || nid);
          const newId = this.generateNextId('W', [...currentModel.walls!, ...newWalls]);
          const clonedWall: WallElement = {
            ...w,
            id: newId,
            name: `Wall ${newId}`,
            nodeIds: newNodeIds
          };
          newWalls.push(clonedWall);
          copiedIds.push(newId);
        }
      }
    }

    return {
      model: {
        ...currentModel,
        members: [...currentModel.members, ...newMembers],
        slabs: [...currentModel.slabs, ...newSlabs],
        walls: currentModel.walls ? [...currentModel.walls, ...newWalls] : newWalls
      },
      copiedIds
    };
  }

  /**
   * Delete selected elements and cascade clean dependencies
   */
  public static deleteElements(
    model: StructuralModel,
    selectedIds: string[],
    options?: { deleteOrphanJoints?: boolean }
  ): StructuralModel {
    if (selectedIds.length === 0) return model;

    const delSet = new Set(selectedIds);

    // 1. Delete members, slabs, walls, openings, links, springs
    const remainingMembers = model.members.filter(m => !delSet.has(m.id));
    const remainingSlabs = model.slabs.filter(s => !delSet.has(s.id));
    const remainingWalls = (model.walls || []).filter(w => !delSet.has(w.id));
    const remainingOpenings = (model.openings || []).filter(o => !delSet.has(o.id));
    const remainingLinks = (model.links || []).filter(l => !delSet.has(l.id));
    const remainingSprings = (model.springs || []).filter(sp => !delSet.has(sp.id));

    // 2. Check if selected items include joints
    const deletedJointIds = new Set(model.nodes.filter(n => delSet.has(n.id)).map(n => n.id));

    // Remove any elements that depended on deleted joints
    const cleanMembers = remainingMembers.filter(
      m => !deletedJointIds.has(m.startNodeId) && !deletedJointIds.has(m.endNodeId)
    );
    const cleanSlabs = remainingSlabs.filter(
      s => !s.nodeIds.some(nid => deletedJointIds.has(nid))
    );
    const cleanWalls = remainingWalls.filter(
      w => !w.nodeIds.some(nid => deletedJointIds.has(nid))
    );

    // 3. Remove selected joints
    let remainingNodes = model.nodes.filter(n => !delSet.has(n.id));

    // 4. Optionally clean orphan joints (joints with no elements and no restraints)
    if (options?.deleteOrphanJoints) {
      const activeJoints = new Set<string>();
      cleanMembers.forEach(m => {
        activeJoints.add(m.startNodeId);
        activeJoints.add(m.endNodeId);
      });
      cleanSlabs.forEach(s => s.nodeIds.forEach(nid => activeJoints.add(nid)));
      cleanWalls.forEach(w => w.nodeIds.forEach(nid => activeJoints.add(nid)));
      remainingLinks.forEach(l => {
        activeJoints.add(l.startNodeId);
        activeJoints.add(l.endNodeId);
      });
      remainingSprings.forEach(sp => activeJoints.add(sp.nodeId));

      remainingNodes = remainingNodes.filter(n => activeJoints.has(n.id) || n.isRestrained);
    }

    return {
      ...model,
      nodes: remainingNodes,
      members: cleanMembers,
      slabs: cleanSlabs,
      walls: cleanWalls,
      openings: remainingOpenings,
      links: remainingLinks,
      springs: remainingSprings
    };
  }

  /**
   * Mirror selected elements across a coordinate plane (XY, XZ, YZ, or Custom)
   */
  public static mirrorElements(
    model: StructuralModel,
    selectedIds: string[],
    plane: {
      axis: 'XY' | 'XZ' | 'YZ';
      coordinate?: number;
    }
  ): { model: StructuralModel; createdIds: string[] } {
    let currentModel = JSON.parse(JSON.stringify(model)) as StructuralModel;
    const createdIds: string[] = [];
    const mirrorCoord = plane.coordinate ?? 0;
    const nodeIdMap = new Map<string, string>();

    // 1. Collect all joints
    const nodeIdsToMirror = new Set<string>();
    for (const id of selectedIds) {
      if (currentModel.nodes.some(n => n.id === id)) nodeIdsToMirror.add(id);
    }
    for (const m of currentModel.members) {
      if (selectedIds.includes(m.id)) {
        nodeIdsToMirror.add(m.startNodeId);
        nodeIdsToMirror.add(m.endNodeId);
      }
    }
    for (const s of currentModel.slabs) {
      if (selectedIds.includes(s.id)) s.nodeIds.forEach(nid => nodeIdsToMirror.add(nid));
    }
    if (currentModel.walls) {
      for (const w of currentModel.walls) {
        if (selectedIds.includes(w.id)) w.nodeIds.forEach(nid => nodeIdsToMirror.add(nid));
      }
    }

    // 2. Mirror nodes
    for (const oldNodeId of Array.from(nodeIdsToMirror)) {
      const origNode = currentModel.nodes.find(n => n.id === oldNodeId);
      if (!origNode) continue;

      let mx = origNode.x;
      let my = origNode.y;
      let mz = origNode.z;

      if (plane.axis === 'YZ') {
        mx = 2 * mirrorCoord - origNode.x;
      } else if (plane.axis === 'XZ') {
        my = 2 * mirrorCoord - origNode.y;
      } else if (plane.axis === 'XY') {
        mz = 2 * mirrorCoord - origNode.z;
      }

      const res = this.getOrCreateJoint(currentModel, { x: mx, y: my, z: mz }, {
        isRestrained: origNode.isRestrained
      });
      currentModel = res.model;
      nodeIdMap.set(oldNodeId, res.joint.id);
      if (selectedIds.includes(oldNodeId)) createdIds.push(res.joint.id);
    }

    // 3. Mirror members
    const newMembers: StructuralMember[] = [];
    for (const m of currentModel.members) {
      if (selectedIds.includes(m.id)) {
        const newStart = nodeIdMap.get(m.startNodeId) || m.startNodeId;
        const newEnd = nodeIdMap.get(m.endNodeId) || m.endNodeId;
        const prefix = m.type === 'column' ? 'C' : m.type === 'beam' ? 'B' : 'BR';
        const newId = this.generateNextId(prefix, [...currentModel.members, ...newMembers]);

        const startN = currentModel.nodes.find(n => n.id === newStart);
        const endN = currentModel.nodes.find(n => n.id === newEnd);
        const len = startN && endN ? this.distance(startN, endN) : m.length;

        const clonedMember: StructuralMember = {
          ...m,
          id: newId,
          name: `${prefix}${newId}`,
          startNodeId: newStart,
          endNodeId: newEnd,
          length: Math.round(len * 10000) / 10000
        };
        newMembers.push(clonedMember);
        createdIds.push(newId);
      }
    }

    // 4. Mirror slabs (reverse vertex order to preserve outward normal)
    const newSlabs: SlabElement[] = [];
    for (const s of currentModel.slabs) {
      if (selectedIds.includes(s.id)) {
        const mirroredNodeIds = s.nodeIds.map(nid => nodeIdMap.get(nid) || nid).reverse();
        const newId = this.generateNextId('S', [...currentModel.slabs, ...newSlabs]);
        const clonedSlab: SlabElement = {
          ...s,
          id: newId,
          name: `Slab ${newId}`,
          nodeIds: mirroredNodeIds
        };
        newSlabs.push(clonedSlab);
        createdIds.push(newId);
      }
    }

    return {
      model: {
        ...currentModel,
        members: [...currentModel.members, ...newMembers],
        slabs: [...currentModel.slabs, ...newSlabs]
      },
      createdIds
    };
  }

  /**
   * Linear Array Replicate
   */
  public static linearArray(
    model: StructuralModel,
    selectedIds: string[],
    count: number,
    offset: { dx: number; dy: number; dz: number }
  ): { model: StructuralModel; createdIds: string[] } {
    let currentModel = model;
    const allCreatedIds: string[] = [];

    for (let step = 1; step <= count; step++) {
      const delta = {
        dx: offset.dx * step,
        dy: offset.dy * step,
        dz: offset.dz * step
      };
      const res = this.copyElements(currentModel, selectedIds, delta);
      currentModel = res.model;
      allCreatedIds.push(...res.copiedIds);
    }

    return {
      model: currentModel,
      createdIds: allCreatedIds
    };
  }

  /**
   * Radial Array Replicate
   */
  public static radialArray(
    model: StructuralModel,
    selectedIds: string[],
    count: number,
    center: Point3D,
    axis: 'X' | 'Y' | 'Z',
    angleDeg: number
  ): { model: StructuralModel; createdIds: string[] } {
    let currentModel = JSON.parse(JSON.stringify(model)) as StructuralModel;
    const allCreatedIds: string[] = [];
    const radStep = (angleDeg * Math.PI) / 180;

    // Collect joints
    const nodeIds = new Set<string>();
    for (const id of selectedIds) {
      if (currentModel.nodes.some(n => n.id === id)) nodeIds.add(id);
    }
    for (const m of currentModel.members) {
      if (selectedIds.includes(m.id)) {
        nodeIds.add(m.startNodeId);
        nodeIds.add(m.endNodeId);
      }
    }
    for (const s of currentModel.slabs) {
      if (selectedIds.includes(s.id)) s.nodeIds.forEach(nid => nodeIds.add(nid));
    }

    for (let step = 1; step <= count; step++) {
      const currentAngle = radStep * step;
      const cosA = Math.cos(currentAngle);
      const sinA = Math.sin(currentAngle);
      const stepNodeMap = new Map<string, string>();

      // Rotate nodes
      for (const oldId of Array.from(nodeIds)) {
        const origNode = currentModel.nodes.find(n => n.id === oldId);
        if (!origNode) continue;

        let rx = origNode.x;
        let ry = origNode.y;
        let rz = origNode.z;

        if (axis === 'Y') {
          // Rotate around Y axis (Z in standard Three.js)
          const dx = origNode.x - center.x;
          const dz = origNode.z - center.z;
          rx = center.x + (dx * cosA - dz * sinA);
          rz = center.z + (dx * sinA + dz * cosA);
        } else if (axis === 'Z') {
          // Rotate around Z axis (XY plane)
          const dx = origNode.x - center.x;
          const dy = origNode.y - center.y;
          rx = center.x + (dx * cosA - dy * sinA);
          ry = center.y + (dx * sinA + dy * cosA);
        }

        const res = this.getOrCreateJoint(currentModel, { x: rx, y: ry, z: rz }, {
          isRestrained: origNode.isRestrained
        });
        currentModel = res.model;
        stepNodeMap.set(oldId, res.joint.id);
        if (selectedIds.includes(oldId)) allCreatedIds.push(res.joint.id);
      }

      // Recreate members
      const newMembers: StructuralMember[] = [];
      for (const m of currentModel.members) {
        if (selectedIds.includes(m.id)) {
          const newStart = stepNodeMap.get(m.startNodeId) || m.startNodeId;
          const newEnd = stepNodeMap.get(m.endNodeId) || m.endNodeId;
          const prefix = m.type === 'column' ? 'C' : m.type === 'beam' ? 'B' : 'BR';
          const newId = this.generateNextId(prefix, [...currentModel.members, ...newMembers]);

          const startN = currentModel.nodes.find(n => n.id === newStart);
          const endN = currentModel.nodes.find(n => n.id === newEnd);
          const len = startN && endN ? this.distance(startN, endN) : m.length;

          const clonedMember: StructuralMember = {
            ...m,
            id: newId,
            name: `${prefix}${newId}`,
            startNodeId: newStart,
            endNodeId: newEnd,
            length: Math.round(len * 10000) / 10000
          };
          newMembers.push(clonedMember);
          allCreatedIds.push(newId);
        }
      }

      currentModel = {
        ...currentModel,
        members: [...currentModel.members, ...newMembers]
      };
    }

    return {
      model: currentModel,
      createdIds: allCreatedIds
    };
  }

  /**
   * Divide a frame member into N equal segments
   */
  public static divideMember(
    model: StructuralModel,
    memberId: string,
    segments: number = 2
  ): { model: StructuralModel; newMemberIds: string[]; newJointIds: string[] } {
    if (segments < 2) return { model, newMemberIds: [memberId], newJointIds: [] };

    const member = model.members.find(m => m.id === memberId);
    if (!member) throw new Error(`Member not found: ${memberId}`);

    const startNode = model.nodes.find(n => n.id === member.startNodeId);
    const endNode = model.nodes.find(n => n.id === member.endNodeId);
    if (!startNode || !endNode) throw new Error('Start or end joint missing for divide');

    let currentModel = model;
    const jointSequence: string[] = [startNode.id];
    const newJointIds: string[] = [];

    // Create intermediate nodes
    for (let i = 1; i < segments; i++) {
      const frac = i / segments;
      const interpCoords: Point3D = {
        x: startNode.x + (endNode.x - startNode.x) * frac,
        y: startNode.y + (endNode.y - startNode.y) * frac,
        z: startNode.z + (endNode.z - startNode.z) * frac
      };

      const res = this.getOrCreateJoint(currentModel, interpCoords);
      currentModel = res.model;
      jointSequence.push(res.joint.id);
      newJointIds.push(res.joint.id);
    }
    jointSequence.push(endNode.id);

    // Create sub-members
    const prefix = member.type === 'column' ? 'C' : member.type === 'beam' ? 'B' : 'BR';
    const remainingMembers = currentModel.members.filter(m => m.id !== memberId);
    const newMembers: StructuralMember[] = [];
    const newMemberIds: string[] = [];

    for (let i = 0; i < segments; i++) {
      const sId = jointSequence[i];
      const eId = jointSequence[i + 1];
      const sNode = currentModel.nodes.find(n => n.id === sId)!;
      const eNode = currentModel.nodes.find(n => n.id === eId)!;
      const len = this.distance(sNode, eNode);

      const subId = this.generateNextId(prefix, [...remainingMembers, ...newMembers]);
      const subMember: StructuralMember = {
        ...member,
        id: subId,
        name: `${prefix}${subId}`,
        startNodeId: sId,
        endNodeId: eId,
        length: Math.round(len * 10000) / 10000
      };
      newMembers.push(subMember);
      newMemberIds.push(subId);
    }

    return {
      model: {
        ...currentModel,
        members: [...remainingMembers, ...newMembers]
      },
      newMemberIds,
      newJointIds
    };
  }

  /**
   * Merge collinear members sharing a common node
   */
  public static mergeCollinearMembers(
    model: StructuralModel,
    memberIds: string[]
  ): { model: StructuralModel; mergedMemberId: string | null } {
    if (memberIds.length < 2) return { model, mergedMemberId: null };

    const selectedMembers = model.members.filter(m => memberIds.includes(m.id));
    if (selectedMembers.length < 2) return { model, mergedMemberId: null };

    // Find connectivity
    const m1 = selectedMembers[0];
    const m2 = selectedMembers[1];

    let commonNodeId: string | null = null;
    let startNodeId: string | null = null;
    let endNodeId: string | null = null;

    if (m1.endNodeId === m2.startNodeId) {
      commonNodeId = m1.endNodeId;
      startNodeId = m1.startNodeId;
      endNodeId = m2.endNodeId;
    } else if (m1.startNodeId === m2.endNodeId) {
      commonNodeId = m1.startNodeId;
      startNodeId = m2.startNodeId;
      endNodeId = m1.endNodeId;
    } else if (m1.startNodeId === m2.startNodeId) {
      commonNodeId = m1.startNodeId;
      startNodeId = m1.endNodeId;
      endNodeId = m2.endNodeId;
    } else if (m1.endNodeId === m2.endNodeId) {
      commonNodeId = m1.endNodeId;
      startNodeId = m1.startNodeId;
      endNodeId = m2.startNodeId;
    }

    if (!commonNodeId || !startNodeId || !endNodeId) {
      throw new Error('Members do not share a common junction node');
    }

    const sNode = model.nodes.find(n => n.id === startNodeId)!;
    const eNode = model.nodes.find(n => n.id === endNodeId)!;
    const totalLen = this.distance(sNode, eNode);

    const prefix = m1.type === 'column' ? 'C' : m1.type === 'beam' ? 'B' : 'BR';
    const remainingMembers = model.members.filter(m => !memberIds.includes(m.id));
    const mergedId = this.generateNextId(prefix, remainingMembers);

    const mergedMember: StructuralMember = {
      ...m1,
      id: mergedId,
      name: `${prefix}${mergedId}`,
      startNodeId,
      endNodeId,
      length: Math.round(totalLen * 10000) / 10000
    };

    return {
      model: {
        ...model,
        members: [...remainingMembers, mergedMember]
      },
      mergedMemberId: mergedId
    };
  }

  /**
   * Merge duplicate/coincident joints within specified geometric tolerance
   */
  public static mergeDuplicateJoints(
    model: StructuralModel,
    tolerance: number = 0.005
  ): { model: StructuralModel; mergedCount: number } {
    const nodeReplacementMap = new Map<string, string>(); // duplicateId -> masterId
    const uniqueNodes: NodePoint[] = [];

    for (const node of model.nodes) {
      let master: NodePoint | null = null;
      for (const u of uniqueNodes) {
        if (this.distance(node, u) <= tolerance) {
          master = u;
          break;
        }
      }

      if (master) {
        nodeReplacementMap.set(node.id, master.id);
        // Retain restraint if duplicate had it
        if (node.isRestrained && !master.isRestrained) {
          master.isRestrained = { ...node.isRestrained };
        }
      } else {
        uniqueNodes.push({ ...node });
      }
    }

    const mergedCount = nodeReplacementMap.size;
    if (mergedCount === 0) return { model, mergedCount: 0 };

    // Update all referencing elements
    const updatedMembers = model.members.map(m => ({
      ...m,
      startNodeId: nodeReplacementMap.get(m.startNodeId) || m.startNodeId,
      endNodeId: nodeReplacementMap.get(m.endNodeId) || m.endNodeId
    }));

    const updatedSlabs = model.slabs.map(s => ({
      ...s,
      nodeIds: s.nodeIds.map(nid => nodeReplacementMap.get(nid) || nid)
    }));

    const updatedWalls = model.walls?.map(w => ({
      ...w,
      nodeIds: w.nodeIds.map(nid => nodeReplacementMap.get(nid) || nid)
    }));

    return {
      model: {
        ...model,
        nodes: uniqueNodes,
        members: updatedMembers,
        slabs: updatedSlabs,
        walls: updatedWalls
      },
      mergedCount
    };
  }

  /**
   * Align selected joints along an axis to a target value or min/max/mean
   */
  public static alignElements(
    model: StructuralModel,
    selectedIds: string[],
    axis: 'X' | 'Y' | 'Z',
    target: number | 'min' | 'max' | 'mean'
  ): StructuralModel {
    const targetNodes = model.nodes.filter(n => selectedIds.includes(n.id));
    if (targetNodes.length === 0) return model;

    let targetCoord: number;
    const prop = axis.toLowerCase() as 'x' | 'y' | 'z';

    if (typeof target === 'number') {
      targetCoord = target;
    } else {
      const values = targetNodes.map(n => n[prop]);
      if (target === 'min') targetCoord = Math.min(...values);
      else if (target === 'max') targetCoord = Math.max(...values);
      else targetCoord = values.reduce((a, b) => a + b, 0) / values.length;
    }

    const updatedNodes = model.nodes.map(node => {
      if (selectedIds.includes(node.id)) {
        return {
          ...node,
          [prop]: Math.round(targetCoord * 10000) / 10000
        };
      }
      return node;
    });

    return {
      ...model,
      nodes: updatedNodes
    };
  }

  /**
   * Replicate elements to target stories (Story Replicate)
   */
  public static replicateToStories(
    model: StructuralModel,
    selectedIds: string[],
    sourceStoryName: string,
    targetStoryNames: string[]
  ): { model: StructuralModel; createdIds: string[] } {
    let currentModel = JSON.parse(JSON.stringify(model)) as StructuralModel;
    const createdIds: string[] = [];

    const sourceStory = currentModel.stories.find(s => s.name === sourceStoryName || s.id === sourceStoryName);
    if (!sourceStory) throw new Error(`Source story "${sourceStoryName}" not found`);

    for (const targetName of targetStoryNames) {
      const targetStory = currentModel.stories.find(s => s.name === targetName || s.id === targetName);
      if (!targetStory || targetStory.name === sourceStory.name) continue;

      const deltaElevation = targetStory.elevation - sourceStory.elevation;
      const res = this.copyElements(currentModel, selectedIds, {
        dx: 0,
        dy: deltaElevation, // Three.js Y / elevation
        dz: 0
      });

      currentModel = res.model;
      createdIds.push(...res.copiedIds);

      // Update story tag on copied members/slabs
      const copiedSet = new Set(res.copiedIds);
      currentModel.members = currentModel.members.map(m => {
        if (copiedSet.has(m.id)) {
          return { ...m, story: targetStory.name };
        }
        return m;
      });
      currentModel.slabs = currentModel.slabs.map(s => {
        if (copiedSet.has(s.id)) {
          return { ...s, story: targetStory.name };
        }
        return s;
      });
      if (currentModel.walls) {
        currentModel.walls = currentModel.walls.map(w => {
          if (copiedSet.has(w.id)) {
            return { ...w, story: targetStory.name };
          }
          return w;
        });
      }
    }

    return {
      model: currentModel,
      createdIds
    };
  }
}
