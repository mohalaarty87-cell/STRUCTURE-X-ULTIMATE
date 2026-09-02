import { StructuralModel, Material, SectionProperty, NodePoint, StructuralMember, SlabElement } from '../types/structure';

export const defaultMaterials: Material[] = [
  {
    id: 'mat-c3037',
    name: 'C30/37',
    type: 'concrete',
    grade: 'C30/37',
    elasticModulusE: 33, // GPa
    poissonRatio: 0.2,
    unitWeight: 25, // kN/m3
    compressiveStrengthFc: 30, // MPa
    color: '#7ed99e'
  },
  {
    id: 'mat-s355',
    name: 'S355',
    type: 'steel',
    grade: 'S355 Structural Steel',
    elasticModulusE: 210, // GPa
    poissonRatio: 0.3,
    unitWeight: 78.5, // kN/m3
    yieldStrengthFy: 355, // MPa
    color: '#96ccff'
  },
  {
    id: 'mat-c2530',
    name: 'C25/30',
    type: 'concrete',
    grade: 'C25/30',
    elasticModulusE: 31,
    poissonRatio: 0.2,
    unitWeight: 25,
    compressiveStrengthFc: 25,
    color: '#a3e635'
  },
  {
    id: 'mat-s275',
    name: 'S275',
    type: 'steel',
    grade: 'S275 Structural Steel',
    elasticModulusE: 205,
    poissonRatio: 0.3,
    unitWeight: 78.5,
    yieldStrengthFy: 275,
    color: '#60a5fa'
  }
];

export const defaultSections: SectionProperty[] = [
  {
    id: 'sec-400rc',
    name: '400x400 RC',
    shape: 'rectangular',
    materialId: 'mat-c3037',
    dimensions: {
      width: 400,
      height: 400
    },
    area: 1600, // cm2
    momentOfInertiaIxx: 213333, // cm4
    momentOfInertiaIyy: 213333,
    torsionalConstantJ: 360000,
    weightPerMeter: 100 // kg/m (concrete 0.4*0.4*2500)
  },
  {
    id: 'sec-300x500rc',
    name: '300x500 RC Beam',
    shape: 'rectangular',
    materialId: 'mat-c3037',
    dimensions: {
      width: 300,
      height: 500
    },
    area: 1500,
    momentOfInertiaIxx: 312500,
    momentOfInertiaIyy: 112500,
    torsionalConstantJ: 280000,
    weightPerMeter: 93.75
  },
  {
    id: 'sec-heb300',
    name: 'HEB 300 Steel Column',
    shape: 'i_beam',
    materialId: 'mat-s355',
    dimensions: {
      width: 300,
      height: 300,
      flangeThickness: 19,
      webThickness: 11
    },
    area: 149.1,
    momentOfInertiaIxx: 25170,
    momentOfInertiaIyy: 8563,
    torsionalConstantJ: 185,
    weightPerMeter: 117
  },
  {
    id: 'sec-ipe400',
    name: 'IPE 400 Steel Beam',
    shape: 'i_beam',
    materialId: 'mat-s355',
    dimensions: {
      width: 180,
      height: 400,
      flangeThickness: 13.5,
      webThickness: 8.6
    },
    area: 84.5,
    momentOfInertiaIxx: 23130,
    momentOfInertiaIyy: 1318,
    torsionalConstantJ: 51.1,
    weightPerMeter: 66.3
  }
];

/**
 * Creates the standard 2-Story RC Building Model matching the screenshot
 * Grid: 4x3 bays in X & Y, with columns (24), beams (42), and slabs (12)
 */
export function createDefaultRCBuilding(): StructuralModel {
  const stories = [
    { id: 'story-base', name: 'Base / Foundation', elevation: 0.0, height: 0.0 },
    { id: 'story-1', name: 'Story 1', elevation: 3.5, height: 3.5 },
    { id: 'story-2', name: 'Story 2', elevation: 7.0, height: 3.5 }
  ];

  const gridLinesX = [
    { id: 'grid-x1', label: '1', axis: 'X' as const, coordinate: -6.0 },
    { id: 'grid-x2', label: '2', axis: 'X' as const, coordinate: -2.0 },
    { id: 'grid-x3', label: '3', axis: 'X' as const, coordinate: 2.0 },
    { id: 'grid-x4', label: '4', axis: 'X' as const, coordinate: 6.0 }
  ];

  const gridLinesY = [
    { id: 'grid-yA', label: 'A', axis: 'Y' as const, coordinate: -4.0 },
    { id: 'grid-yB', label: 'B', axis: 'Y' as const, coordinate: 0.0 },
    { id: 'grid-yC', label: 'C', axis: 'Y' as const, coordinate: 4.0 }
  ];

  const nodes: NodePoint[] = [];
  const members: StructuralMember[] = [];
  const slabs: SlabElement[] = [];

  // Generate nodes at each grid intersection for Base (y=0), Story 1 (y=3.5), Story 2 (y=7.0)
  // CAD coordinates: x = X, y = Elevation (Z in math, Y in Three), z = Y
  const elevations = [0.0, 3.5, 7.0];

  elevations.forEach((elev, lvlIdx) => {
    gridLinesX.forEach((gx, ix) => {
      gridLinesY.forEach((gy, iy) => {
        const nodeId = `N_L${lvlIdx}_${ix}_${iy}`;
        const isBase = lvlIdx === 0;
        nodes.push({
          id: nodeId,
          x: gx.coordinate,
          y: elev, // elevation in meters
          z: gy.coordinate,
          isRestrained: isBase ? { fx: true, fy: true, fz: true, mx: true, my: true, mz: true } : undefined,
          loads: lvlIdx === 2 ? { fx: 12.5, fy: -45.0, fz: 8.0 } : (lvlIdx === 1 ? { fx: 8.0, fy: -65.0, fz: 4.0 } : undefined)
        });
      });
    });
  });

  // Generate Columns (24 total: 12 on story 1, 12 on story 2)
  let colCounter = 1;
  [1, 2].forEach((storyNum) => {
    const bottomLvl = storyNum - 1;
    const topLvl = storyNum;
    gridLinesX.forEach((gx, ix) => {
      gridLinesY.forEach((gy, iy) => {
        const bottomNodeId = `N_L${bottomLvl}_${ix}_${iy}`;
        const topNodeId = `N_L${topLvl}_${ix}_${iy}`;
        const isSelected = colCounter === 1; // C1 is selected by default in screenshot

        // Realistic structural forces
        const axial = -(450 + (3 - storyNum) * 380 + Math.random() * 40);
        const moment = 42.5 + Math.random() * 15;
        const shear = 28.0 + Math.random() * 8;
        const util = Math.min(0.85, 0.45 + (colCounter % 5) * 0.08);

        members.push({
          id: `C${colCounter}`,
          name: `Column C${colCounter}`,
          type: 'column',
          story: `Story ${storyNum}`,
          startNodeId: bottomNodeId,
          endNodeId: topNodeId,
          sectionId: 'sec-400rc',
          materialId: 'mat-c3037',
          length: 3.5,
          releases: 'Continuous',
          localAxisAngle: 0.0,
          forces: {
            axialP: Math.round(axial * 10) / 10,
            shearV2: Math.round(shear * 10) / 10,
            shearV3: Math.round((shear * 0.4) * 10) / 10,
            torsionT: 4.2,
            momentM2: Math.round((moment * 0.35) * 10) / 10,
            momentM3: Math.round(moment * 10) / 10,
            maxDeflection: Math.round((1.8 + storyNum * 1.4) * 10) / 10,
            utilizationRatio: Math.round(util * 100) / 100,
            designStatus: util > 0.9 ? 'WARNING' : 'PASS'
          }
        });
        colCounter++;
      });
    });
  });

  // Generate Beams (42 total: 21 per story)
  // X-direction beams: 3 segments * 3 gridlines = 9 per story -> 18 total
  // Y-direction beams: 2 segments * 4 gridlines = 8 per story -> 16 total + diagonals / edge = 42 total
  let beamCounter = 1;
  [1, 2].forEach((storyNum) => {
    // X-dir beams
    gridLinesY.forEach((gy, iy) => {
      for (let ix = 0; ix < gridLinesX.length - 1; ix++) {
        const startNodeId = `N_L${storyNum}_${ix}_${iy}`;
        const endNodeId = `N_L${storyNum}_${ix + 1}_${iy}`;
        const span = Math.abs(gridLinesX[ix + 1].coordinate - gridLinesX[ix].coordinate);
        const moment = 68.4 + Math.random() * 20;
        const shear = 52.1 + Math.random() * 12;
        const util = 0.52 + (beamCounter % 6) * 0.06;

        members.push({
          id: `B${beamCounter}`,
          name: `Beam B${beamCounter}`,
          type: 'beam',
          story: `Story ${storyNum}`,
          startNodeId,
          endNodeId,
          sectionId: 'sec-300x500rc',
          materialId: 'mat-c3037',
          length: span,
          releases: 'Continuous',
          localAxisAngle: 0.0,
          distributedLoad: 24.0, // kN/m
          forces: {
            axialP: -12.4,
            shearV2: Math.round(shear * 10) / 10,
            shearV3: 2.1,
            torsionT: 6.8,
            momentM2: 8.5,
            momentM3: Math.round(moment * 10) / 10,
            maxDeflection: Math.round((2.4 + storyNum * 1.1) * 10) / 10,
            utilizationRatio: Math.round(util * 100) / 100,
            designStatus: 'PASS'
          }
        });
        beamCounter++;
      }
    });

    // Y-dir beams
    gridLinesX.forEach((gx, ix) => {
      for (let iy = 0; iy < gridLinesY.length - 1; iy++) {
        const startNodeId = `N_L${storyNum}_${ix}_${iy}`;
        const endNodeId = `N_L${storyNum}_${ix}_${iy + 1}`;
        const span = Math.abs(gridLinesY[iy + 1].coordinate - gridLinesY[iy].coordinate);
        const moment = 54.2 + Math.random() * 18;
        const shear = 41.0 + Math.random() * 10;
        const util = 0.48 + (beamCounter % 5) * 0.07;

        members.push({
          id: `B${beamCounter}`,
          name: `Beam B${beamCounter}`,
          type: 'beam',
          story: `Story ${storyNum}`,
          startNodeId,
          endNodeId,
          sectionId: 'sec-300x500rc',
          materialId: 'mat-c3037',
          length: span,
          releases: 'Continuous',
          localAxisAngle: 0.0,
          distributedLoad: 18.5,
          forces: {
            axialP: -8.6,
            shearV2: Math.round(shear * 10) / 10,
            shearV3: 1.8,
            torsionT: 4.5,
            momentM2: 6.2,
            momentM3: Math.round(moment * 10) / 10,
            maxDeflection: Math.round((2.1 + storyNum * 0.9) * 10) / 10,
            utilizationRatio: Math.round(util * 100) / 100,
            designStatus: 'PASS'
          }
        });
        beamCounter++;
      }
    });

    // Additional perimeter/secondary beams to make exactly 42 beams (21 per story)
    // 9 (X) + 8 (Y) = 17, add 4 secondary spans
    const sec1Start = `N_L${storyNum}_0_0`;
    const sec1End = `N_L${storyNum}_1_1`;
    members.push({
      id: `B${beamCounter}`,
      name: `Secondary Beam B${beamCounter}`,
      type: 'beam',
      story: `Story ${storyNum}`,
      startNodeId: sec1Start,
      endNodeId: sec1End,
      sectionId: 'sec-300x500rc',
      materialId: 'mat-c3037',
      length: 5.66,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0.0,
      distributedLoad: 12.0,
      forces: {
        axialP: -15.0,
        shearV2: 26.5,
        shearV3: 1.2,
        torsionT: 1.1,
        momentM2: 2.0,
        momentM3: 38.0,
        maxDeflection: 3.2,
        utilizationRatio: 0.62,
        designStatus: 'PASS'
      }
    });
    beamCounter++;

    const sec2Start = `N_L${storyNum}_2_1`;
    const sec2End = `N_L${storyNum}_3_2`;
    members.push({
      id: `B${beamCounter}`,
      name: `Secondary Beam B${beamCounter}`,
      type: 'beam',
      story: `Story ${storyNum}`,
      startNodeId: sec2Start,
      endNodeId: sec2End,
      sectionId: 'sec-300x500rc',
      materialId: 'mat-c3037',
      length: 5.66,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0.0,
      distributedLoad: 12.0,
      forces: {
        axialP: -14.2,
        shearV2: 25.1,
        shearV3: 1.0,
        torsionT: 0.9,
        momentM2: 1.8,
        momentM3: 36.4,
        maxDeflection: 3.0,
        utilizationRatio: 0.58,
        designStatus: 'PASS'
      }
    });
    beamCounter++;

    const sec3Start = `N_L${storyNum}_1_0`;
    const sec3End = `N_L${storyNum}_2_1`;
    members.push({
      id: `B${beamCounter}`,
      name: `Secondary Beam B${beamCounter}`,
      type: 'beam',
      story: `Story ${storyNum}`,
      startNodeId: sec3Start,
      endNodeId: sec3End,
      sectionId: 'sec-300x500rc',
      materialId: 'mat-c3037',
      length: 5.66,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0.0,
      distributedLoad: 12.0,
      forces: {
        axialP: -13.8,
        shearV2: 24.3,
        shearV3: 1.1,
        torsionT: 1.0,
        momentM2: 1.9,
        momentM3: 35.1,
        maxDeflection: 2.9,
        utilizationRatio: 0.55,
        designStatus: 'PASS'
      }
    });
    beamCounter++;

    const sec4Start = `N_L${storyNum}_0_1`;
    const sec4End = `N_L${storyNum}_1_2`;
    members.push({
      id: `B${beamCounter}`,
      name: `Secondary Beam B${beamCounter}`,
      type: 'beam',
      story: `Story ${storyNum}`,
      startNodeId: sec4Start,
      endNodeId: sec4End,
      sectionId: 'sec-300x500rc',
      materialId: 'mat-c3037',
      length: 5.66,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0.0,
      distributedLoad: 12.0,
      forces: {
        axialP: -13.0,
        shearV2: 23.8,
        shearV3: 1.0,
        torsionT: 0.8,
        momentM2: 1.7,
        momentM3: 34.0,
        maxDeflection: 2.8,
        utilizationRatio: 0.54,
        designStatus: 'PASS'
      }
    });
    beamCounter++;
  });

  // Generate Slabs (12 total: 6 on Story 1, 6 on Story 2; 3 bays X * 2 bays Y = 6 bays per story)
  let slabCounter = 1;
  [1, 2].forEach((storyNum) => {
    for (let ix = 0; ix < gridLinesX.length - 1; ix++) {
      for (let iy = 0; iy < gridLinesY.length - 1; iy++) {
        const n1 = `N_L${storyNum}_${ix}_${iy}`;
        const n2 = `N_L${storyNum}_${ix + 1}_${iy}`;
        const n3 = `N_L${storyNum}_${ix + 1}_${iy + 1}`;
        const n4 = `N_L${storyNum}_${ix}_${iy + 1}`;

        slabs.push({
          id: `S${slabCounter}`,
          name: `Slab Panel S${slabCounter}`,
          story: `Story ${storyNum}`,
          nodeIds: [n1, n2, n3, n4],
          thickness: 0.2, // 200mm RC slab
          materialId: 'mat-c3037',
          loadDead: 5.0, // kN/m2
          loadLive: 3.0, // kN/m2
          forces: {
            mxx: 24.5,
            myy: 18.2,
            vmax: 42.0,
            deflection: 4.2 + storyNum * 1.2,
            status: 'PASS'
          }
        });
        slabCounter++;
      }
    }
  });

  // Generate Shear Core Walls (e.g. W1, W2 between grid lines for core lateral stability)
  const walls = [
    {
      id: 'W1',
      name: 'Shear Wall W1 (Elev Core)',
      story: 'Story 1',
      nodeIds: ['N_L0_1_1', 'N_L0_2_1', 'N_L1_2_1', 'N_L1_1_1'],
      thickness: 0.25, // 250mm reinforced concrete shear wall
      materialId: 'mat-c3037',
      loadDistributed: 45.0,
      forces: {
        axialP: -850.0,
        shearV: 125.0,
        momentM: 340.0,
        status: 'PASS' as const
      }
    },
    {
      id: 'W2',
      name: 'Shear Wall W2 (Elev Core)',
      story: 'Story 2',
      nodeIds: ['N_L1_1_1', 'N_L1_2_1', 'N_L2_2_1', 'N_L2_1_1'],
      thickness: 0.25,
      materialId: 'mat-c3037',
      loadDistributed: 30.0,
      forces: {
        axialP: -420.0,
        shearV: 95.0,
        momentM: 180.0,
        status: 'PASS' as const
      }
    }
  ];

  return {
    projectName: 'STRUCTURE-X ULTIMATE',
    version: 'v1.0',
    units: 'kN-m, C',
    stories,
    gridLinesX,
    gridLinesY,
    materials: defaultMaterials,
    sections: defaultSections,
    nodes,
    members,
    slabs,
    walls
  };
}

export function createSteelPortalFrameModel(): StructuralModel {
  const stories = [
    { id: 'story-base', name: 'Base', elevation: 0.0, height: 0.0 },
    { id: 'story-eaves', name: 'Eaves Level', elevation: 6.0, height: 6.0 },
    { id: 'story-ridge', name: 'Apex / Ridge', elevation: 8.5, height: 2.5 }
  ];

  const gridLinesX = [
    { id: 'grid-x1', label: '1', axis: 'X' as const, coordinate: -12.0 },
    { id: 'grid-x2', label: '2', axis: 'X' as const, coordinate: -6.0 },
    { id: 'grid-x3', label: '3', axis: 'X' as const, coordinate: 0.0 },
    { id: 'grid-x4', label: '4', axis: 'X' as const, coordinate: 6.0 },
    { id: 'grid-x5', label: '5', axis: 'X' as const, coordinate: 12.0 }
  ];

  const gridLinesY = [
    { id: 'grid-yA', label: 'A', axis: 'Y' as const, coordinate: -10.0 },
    { id: 'grid-yB', label: 'B', axis: 'Y' as const, coordinate: 0.0 },
    { id: 'grid-yC', label: 'C', axis: 'Y' as const, coordinate: 10.0 }
  ];

  const nodes: NodePoint[] = [];
  const members: StructuralMember[] = [];
  const slabs: SlabElement[] = [];

  let colId = 1;
  let beamId = 1;

  gridLinesY.forEach((gy, iy) => {
    // Base nodes
    const nBaseLeft = `N_Base_L_${iy}`;
    const nBaseRight = `N_Base_R_${iy}`;
    const nEaveLeft = `N_Eave_L_${iy}`;
    const nEaveRight = `N_Eave_R_${iy}`;
    const nApex = `N_Apex_${iy}`;

    nodes.push(
      { id: nBaseLeft, x: -12.0, y: 0, z: gy.coordinate, isRestrained: { fx: true, fy: true, fz: true, mx: false, my: false, mz: false } },
      { id: nBaseRight, x: 12.0, y: 0, z: gy.coordinate, isRestrained: { fx: true, fy: true, fz: true, mx: false, my: false, mz: false } },
      { id: nEaveLeft, x: -12.0, y: 6.0, z: gy.coordinate },
      { id: nEaveRight, x: 12.0, y: 6.0, z: gy.coordinate },
      { id: nApex, x: 0.0, y: 8.5, z: gy.coordinate, loads: { fx: 15.0, fy: -80.0, fz: 0.0 } }
    );

    // Columns
    members.push({
      id: `C${colId++}`,
      name: `Column C${colId - 1}`,
      type: 'column',
      story: 'Eaves Level',
      startNodeId: nBaseLeft,
      endNodeId: nEaveLeft,
      sectionId: 'sec-heb300',
      materialId: 'mat-s355',
      length: 6.0,
      releases: 'Continuous',
      localAxisAngle: 0,
      forces: { axialP: -280, shearV2: 45, shearV3: 2, torsionT: 1, momentM2: 3, momentM3: 185, maxDeflection: 12, utilizationRatio: 0.76, designStatus: 'PASS' }
    });

    members.push({
      id: `C${colId++}`,
      name: `Column C${colId - 1}`,
      type: 'column',
      story: 'Eaves Level',
      startNodeId: nBaseRight,
      endNodeId: nEaveRight,
      sectionId: 'sec-heb300',
      materialId: 'mat-s355',
      length: 6.0,
      releases: 'Continuous',
      localAxisAngle: 0,
      forces: { axialP: -265, shearV2: 42, shearV3: 2, torsionT: 1, momentM2: 3, momentM3: 172, maxDeflection: 11, utilizationRatio: 0.72, designStatus: 'PASS' }
    });

    // Rafters
    members.push({
      id: `B${beamId++}`,
      name: `Rafter Left B${beamId - 1}`,
      type: 'beam',
      story: 'Apex / Ridge',
      startNodeId: nEaveLeft,
      endNodeId: nApex,
      sectionId: 'sec-ipe400',
      materialId: 'mat-s355',
      length: 12.25,
      releases: 'Continuous',
      localAxisAngle: 0,
      distributedLoad: 14.5,
      forces: { axialP: -95, shearV2: 68, shearV3: 1, torsionT: 0.5, momentM2: 2, momentM3: 210, maxDeflection: 22, utilizationRatio: 0.84, designStatus: 'PASS' }
    });

    members.push({
      id: `B${beamId++}`,
      name: `Rafter Right B${beamId - 1}`,
      type: 'beam',
      story: 'Apex / Ridge',
      startNodeId: nApex,
      endNodeId: nEaveRight,
      sectionId: 'sec-ipe400',
      materialId: 'mat-s355',
      length: 12.25,
      releases: 'Continuous',
      localAxisAngle: 0,
      distributedLoad: 14.5,
      forces: { axialP: -92, shearV2: 65, shearV3: 1, torsionT: 0.5, momentM2: 2, momentM3: 202, maxDeflection: 21, utilizationRatio: 0.81, designStatus: 'PASS' }
    });
  });

  // Longitudinal Purlins & Eaves ties
  for (let iy = 0; iy < gridLinesY.length - 1; iy++) {
    members.push({
      id: `B${beamId++}`,
      name: `Eaves Tie L ${beamId - 1}`,
      type: 'beam',
      story: 'Eaves Level',
      startNodeId: `N_Eave_L_${iy}`,
      endNodeId: `N_Eave_L_${iy + 1}`,
      sectionId: 'sec-ipe400',
      materialId: 'mat-s355',
      length: 10.0,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0,
      forces: { axialP: -45, shearV2: 12, shearV3: 0.5, torsionT: 0.2, momentM2: 1, momentM3: 35, maxDeflection: 6, utilizationRatio: 0.35, designStatus: 'PASS' }
    });
    members.push({
      id: `B${beamId++}`,
      name: `Ridge Tie ${beamId - 1}`,
      type: 'beam',
      story: 'Apex / Ridge',
      startNodeId: `N_Apex_${iy}`,
      endNodeId: `N_Apex_${iy + 1}`,
      sectionId: 'sec-ipe400',
      materialId: 'mat-s355',
      length: 10.0,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0,
      forces: { axialP: -38, shearV2: 10, shearV3: 0.4, torsionT: 0.2, momentM2: 1, momentM3: 28, maxDeflection: 5, utilizationRatio: 0.30, designStatus: 'PASS' }
    });
    members.push({
      id: `B${beamId++}`,
      name: `Eaves Tie R ${beamId - 1}`,
      type: 'beam',
      story: 'Eaves Level',
      startNodeId: `N_Eave_R_${iy}`,
      endNodeId: `N_Eave_R_${iy + 1}`,
      sectionId: 'sec-ipe400',
      materialId: 'mat-s355',
      length: 10.0,
      releases: 'Pinned-Pinned',
      localAxisAngle: 0,
      forces: { axialP: -42, shearV2: 11, shearV3: 0.5, torsionT: 0.2, momentM2: 1, momentM3: 32, maxDeflection: 6, utilizationRatio: 0.34, designStatus: 'PASS' }
    });
  }

  return {
    projectName: 'Steel Industrial Portal Frame',
    version: 'v2.1',
    units: 'kN-m, C',
    stories,
    gridLinesX,
    gridLinesY,
    materials: defaultMaterials,
    sections: defaultSections,
    nodes,
    members,
    slabs
  };
}
