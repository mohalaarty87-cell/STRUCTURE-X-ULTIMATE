"""
STRUCTURE-X ULTIMATE — CAD & BIM INTEROPERABILITY VERIFICATION TESTS (PHASE 13)
Automated benchmark and verification suite for:
- IFC Import & Export
- DXF Import & Export
- CSV Import & Export
- Excel Import & Export
- JSON Import & Export
- Validation Engine (geometry, topology, tolerances)
- Mapping Engine (scales, layers, materials, sections)
- Non-Destructive Project Commitment (zero corruption guarantee)
"""

import math
import unittest
from engine.cad_bim import (
    CadBimInteropEngine,
    InteropFormat,
    MergeStrategy,
    ValidationSeverity,
    MappingConfig,
    CoordinateTransform,
)


def create_sample_structural_model():
    """Builds a realistic 2-story reinforced concrete and steel frame model."""
    return {
        "projectName": "Benchmark Building 13",
        "version": "5.0.0-PRO",
        "units": "kN-m, C",
        "stories": [
            {"id": "STORY_1", "name": "Story 1", "elevation": 3.5, "height": 3.5},
            {"id": "STORY_2", "name": "Story 2", "elevation": 7.0, "height": 3.5}
        ],
        "materials": [
            {
                "id": "MAT-C30",
                "name": "Concrete C30/37",
                "type": "concrete",
                "grade": "C30/37",
                "elasticModulusE": 33.0,
                "poissonRatio": 0.2,
                "unitWeight": 25.0,
                "compressiveStrengthFc": 30.0
            },
            {
                "id": "MAT-S355",
                "name": "Structural Steel S355",
                "type": "steel",
                "grade": "S355",
                "elasticModulusE": 210.0,
                "poissonRatio": 0.3,
                "unitWeight": 78.5,
                "yieldStrengthFy": 355.0
            }
        ],
        "sections": [
            {
                "id": "SEC-COL-400X400",
                "name": "RC Column 400x400",
                "shape": "rectangular",
                "materialId": "MAT-C30",
                "dimensions": {"width": 400.0, "height": 400.0},
                "area": 1600.0,
                "momentOfInertiaIxx": 213333.3,
                "momentOfInertiaIyy": 213333.3,
                "torsionalConstantJ": 360000.0,
                "weightPerMeter": 100.0
            },
            {
                "id": "SEC-IPE-400",
                "name": "Steel IPE 400",
                "shape": "i_beam",
                "materialId": "MAT-S355",
                "dimensions": {"width": 180.0, "height": 400.0, "webThickness": 8.6, "flangeThickness": 13.5},
                "area": 84.5,
                "momentOfInertiaIxx": 23130.0,
                "momentOfInertiaIyy": 1318.0,
                "torsionalConstantJ": 51.1,
                "weightPerMeter": 66.3
            }
        ],
        "nodes": [
            {"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0, "restraints": {"translationX": True, "translationY": True, "translationZ": True, "rotationX": True, "rotationY": True, "rotationZ": True}},
            {"id": "N2", "x": 6.0, "y": 0.0, "z": 0.0, "restraints": {"translationX": True, "translationY": True, "translationZ": True, "rotationX": True, "rotationY": True, "rotationZ": True}},
            {"id": "N3", "x": 6.0, "y": 6.0, "z": 0.0, "restraints": {"translationX": True, "translationY": True, "translationZ": True, "rotationX": True, "rotationY": True, "rotationZ": True}},
            {"id": "N4", "x": 0.0, "y": 6.0, "z": 0.0, "restraints": {"translationX": True, "translationY": True, "translationZ": True, "rotationX": True, "rotationY": True, "rotationZ": True}},
            {"id": "N5", "x": 0.0, "y": 0.0, "z": 3.5},
            {"id": "N6", "x": 6.0, "y": 0.0, "z": 3.5},
            {"id": "N7", "x": 6.0, "y": 6.0, "z": 3.5},
            {"id": "N8", "x": 0.0, "y": 6.0, "z": 3.5},
        ],
        "members": [
            {"id": "C1", "name": "Column C1", "type": "column", "story": "Story 1", "startNodeId": "N1", "endNodeId": "N5", "sectionId": "SEC-COL-400X400", "materialId": "MAT-C30", "length": 3.5, "layer": "COLUMNS"},
            {"id": "C2", "name": "Column C2", "type": "column", "story": "Story 1", "startNodeId": "N2", "endNodeId": "N6", "sectionId": "SEC-COL-400X400", "materialId": "MAT-C30", "length": 3.5, "layer": "COLUMNS"},
            {"id": "C3", "name": "Column C3", "type": "column", "story": "Story 1", "startNodeId": "N3", "endNodeId": "N7", "sectionId": "SEC-COL-400X400", "materialId": "MAT-C30", "length": 3.5, "layer": "COLUMNS"},
            {"id": "C4", "name": "Column C4", "type": "column", "story": "Story 1", "startNodeId": "N4", "endNodeId": "N8", "sectionId": "SEC-COL-400X400", "materialId": "MAT-C30", "length": 3.5, "layer": "COLUMNS"},
            {"id": "B1", "name": "Beam B1", "type": "beam", "story": "Story 1", "startNodeId": "N5", "endNodeId": "N6", "sectionId": "SEC-IPE-400", "materialId": "MAT-S355", "length": 6.0, "layer": "BEAMS"},
            {"id": "B2", "name": "Beam B2", "type": "beam", "story": "Story 1", "startNodeId": "N6", "endNodeId": "N7", "sectionId": "SEC-IPE-400", "materialId": "MAT-S355", "length": 6.0, "layer": "BEAMS"},
            {"id": "B3", "name": "Beam B3", "type": "beam", "story": "Story 1", "startNodeId": "N7", "endNodeId": "N8", "sectionId": "SEC-IPE-400", "materialId": "MAT-S355", "length": 6.0, "layer": "BEAMS"},
            {"id": "B4", "name": "Beam B4", "type": "beam", "story": "Story 1", "startNodeId": "N8", "endNodeId": "N5", "sectionId": "SEC-IPE-400", "materialId": "MAT-S355", "length": 6.0, "layer": "BEAMS"},
        ],
        "slabs": [
            {"id": "S1", "name": "Floor Slab S1", "story": "Story 1", "nodeIds": ["N5", "N6", "N7", "N8"], "thickness": 0.20, "materialId": "MAT-C30", "loadDead": 2.5, "loadLive": 3.0, "diaphragm": "rigid", "layer": "SLABS"}
        ],
        "walls": [
            {"id": "W1", "name": "Shear Wall W1", "story": "Story 1", "nodeIds": ["N1", "N2", "N6", "N5"], "thickness": 0.25, "materialId": "MAT-C30", "layer": "WALLS"}
        ]
    }


class TestCadBimInteroperability(unittest.TestCase):
    """
    Unit and integration tests for Phase 13 CAD and BIM Interoperability.
    """

    def setUp(self):
        self.sample_model = create_sample_structural_model()

    # --- Test 1: IFC Export and Import Round-Trip ---
    def test_ifc_export_and_import(self):
        # 1. Export to IFC4
        res_exp = CadBimInteropEngine.export_model(self.sample_model, InteropFormat.IFC)
        self.assertTrue(res_exp.success)
        self.assertIsNotNone(res_exp.file_content)
        self.assertIn("ISO-10303-21", res_exp.file_content)
        self.assertIn("IFCBEAM", res_exp.file_content)
        self.assertIn("IFCCOLUMN", res_exp.file_content)
        self.assertIn("IFCSLAB", res_exp.file_content)

        # 2. Import back from IFC string
        res_imp = CadBimInteropEngine.import_file(res_exp.file_content, InteropFormat.IFC, "test.ifc")
        self.assertTrue(res_imp.success)
        self.assertIsNotNone(res_imp.data)
        self.assertGreaterEqual(len(res_imp.data["nodes"]), 4)
        self.assertGreaterEqual(len(res_imp.data["members"]), 4)
        self.assertIsNotNone(res_imp.preview)
        self.assertEqual(res_imp.preview.format_type, InteropFormat.IFC)

    # --- Test 2: DXF Export and Import Round-Trip ---
    def test_dxf_export_and_import(self):
        # 1. Export to AutoCAD DXF
        res_exp = CadBimInteropEngine.export_model(self.sample_model, InteropFormat.DXF)
        self.assertTrue(res_exp.success)
        self.assertIsNotNone(res_exp.file_content)
        self.assertIn("SECTION", res_exp.file_content)
        self.assertIn("ENTITIES", res_exp.file_content)
        self.assertIn("COLUMNS", res_exp.file_content)
        self.assertIn("BEAMS", res_exp.file_content)
        self.assertIn("3DFACE", res_exp.file_content)

        # 2. Import back from DXF string
        res_imp = CadBimInteropEngine.import_file(res_exp.file_content, InteropFormat.DXF, "frame.dxf")
        self.assertTrue(res_imp.success)
        self.assertIsNotNone(res_imp.data)
        # Should have recovered nodes and members
        self.assertGreaterEqual(len(res_imp.data["nodes"]), 8)
        self.assertGreaterEqual(len(res_imp.data["members"]), 8)
        # Recovered 3DFACE slabs and walls
        self.assertGreaterEqual(len(res_imp.data["slabs"]) + len(res_imp.data["walls"]), 1)

    # --- Test 3: CSV Export and Import Round-Trip ---
    def test_csv_export_and_import(self):
        # 1. Export to multi-section CSV
        res_exp = CadBimInteropEngine.export_model(self.sample_model, InteropFormat.CSV)
        self.assertTrue(res_exp.success)
        self.assertIn("# NODES", res_exp.file_content)
        self.assertIn("# MEMBERS", res_exp.file_content)
        self.assertIn("# SLABS", res_exp.file_content)
        self.assertIn("# MATERIALS", res_exp.file_content)

        # 2. Import back
        res_imp = CadBimInteropEngine.import_file(res_exp.file_content, InteropFormat.CSV, "model.csv")
        self.assertTrue(res_imp.success)
        self.assertEqual(len(res_imp.data["nodes"]), len(self.sample_model["nodes"]))
        self.assertEqual(len(res_imp.data["members"]), len(self.sample_model["members"]))
        self.assertEqual(len(res_imp.data["slabs"]), len(self.sample_model["slabs"]))
        self.assertEqual(len(res_imp.data["walls"]), len(self.sample_model["walls"]))

    # --- Test 4: Excel Export and Import Round-Trip ---
    def test_excel_export_and_import(self):
        # 1. Export to Excel SpreadsheetML
        res_exp = CadBimInteropEngine.export_model(self.sample_model, InteropFormat.EXCEL)
        self.assertTrue(res_exp.success)
        self.assertIn("<Workbook", res_exp.file_content)
        self.assertIn('ss:Name="NODES"', res_exp.file_content)
        self.assertIn('ss:Name="MEMBERS"', res_exp.file_content)

        # 2. Import back
        res_imp = CadBimInteropEngine.import_file(res_exp.file_content, InteropFormat.EXCEL, "workbook.xml")
        self.assertTrue(res_imp.success)
        self.assertEqual(len(res_imp.data["nodes"]), 8)
        self.assertEqual(len(res_imp.data["members"]), 8)
        self.assertEqual(len(res_imp.data["slabs"]), 1)
        self.assertEqual(len(res_imp.data["walls"]), 1)

    # --- Test 5: JSON Full-Fidelity Round-Trip ---
    def test_json_fidelity(self):
        res_exp = CadBimInteropEngine.export_model(self.sample_model, InteropFormat.JSON)
        self.assertTrue(res_exp.success)

        res_imp = CadBimInteropEngine.import_file(res_exp.file_content, InteropFormat.JSON, "model.json")
        self.assertTrue(res_imp.success)
        # Verify complete coordinates preservation
        for n_orig, n_imp in zip(self.sample_model["nodes"], res_imp.data["nodes"]):
            self.assertAlmostEqual(n_orig["x"], n_imp["x"], places=4)
            self.assertAlmostEqual(n_orig["y"], n_imp["y"], places=4)
            self.assertAlmostEqual(n_orig["z"], n_imp["z"], places=4)

    # --- Test 6: Validation Engine ---
    def test_validation_detects_errors(self):
        corrupt_model = {
            "nodes": [
                {"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0},
                {"id": "N2", "x": 0.0, "y": 0.0, "z": 0.0001}, # duplicate within 1mm
            ],
            "members": [
                {"id": "M_ZERO", "startNodeId": "N1", "endNodeId": "N2"}, # near-zero length
                {"id": "M_DANG", "startNodeId": "N1", "endNodeId": "NON_EXISTENT_NODE"} # dangling node
            ],
            "slabs": [
                {"id": "S_DEGEN", "nodeIds": ["N1", "N2"]} # only 2 vertices (<3)
            ]
        }
        val = CadBimInteropEngine.validate_data(corrupt_model, tolerance_m=0.001)
        self.assertFalse(val.is_valid)
        self.assertGreater(val.error_count, 0)
        codes = [iss.code for iss in val.issues]
        self.assertIn("VAL-NODE-COINCIDENT", codes)
        self.assertIn("VAL-MEM-ZERO-LENGTH", codes)
        self.assertIn("VAL-MEM-DANGLING-NODE", codes)
        self.assertIn("VAL-SLAB-VERTICES", codes)

    # --- Test 7: Mapping and Coordinate Transformation ---
    def test_mapping_transforms_and_scales(self):
        # Raw CAD model in millimeters with layer-based classification
        raw_cad = {
            "nodes": [
                {"id": "1", "x": 0.0, "y": 0.0, "z": 0.0},
                {"id": "2", "x": 6000.0, "y": 0.0, "z": 0.0},
                {"id": "3", "x": 6000.0, "y": 0.0, "z": 3500.0},
            ],
            "members": [
                {"id": "M1", "startNodeId": "1", "endNodeId": "2", "layer": "S-BEAM"},
                {"id": "M2", "startNodeId": "2", "endNodeId": "3", "layer": "S-COL"}
            ],
            "materials": [],
            "sections": []
        }

        config = MappingConfig(
            coordinate_transform=CoordinateTransform(scale_factor=0.001), # mm -> m
            layer_type_map={"S-BEAM": "beam", "S-COL": "column"},
            default_material_id="MAT-C30",
            default_section_id="SEC-COL-400X400"
        )

        mapped = CadBimInteropEngine.map_data(raw_cad, config)

        # Check coordinate scaling: 6000mm -> 6.0m
        n2 = next(n for n in mapped["nodes"] if n["id"] == "2")
        self.assertAlmostEqual(n2["x"], 6.0, places=3)

        n3 = next(n for n in mapped["nodes"] if n["id"] == "3")
        self.assertAlmostEqual(n3["z"], 3.5, places=3)

        # Check layer mapping
        m1 = next(m for m in mapped["members"] if m["id"] == "M1")
        m2 = next(m for m in mapped["members"] if m["id"] == "M2")
        self.assertEqual(m1["type"], "beam")
        self.assertEqual(m2["type"], "column")

    # --- Test 8: Non-Destructive Project Merging ---
    def test_non_destructive_project_merge(self):
        existing = create_sample_structural_model()
        existing_nodes_count = len(existing["nodes"])
        existing_members_count = len(existing["members"])

        # New imported extension
        new_extension = {
            "projectName": "Roof Extension",
            "nodes": [
                {"id": "N1", "x": 0.0, "y": 0.0, "z": 10.5}, # Colliding ID with existing N1
                {"id": "N_EXT_2", "x": 6.0, "y": 0.0, "z": 10.5}
            ],
            "members": [
                {"id": "C1", "name": "Roof Rafter", "type": "beam", "startNodeId": "N1", "endNodeId": "N_EXT_2", "layer": "BEAMS"} # Colliding ID C1
            ],
            "slabs": [],
            "walls": [],
            "materials": [],
            "sections": []
        }

        # Merge with Append strategy
        merged = CadBimInteropEngine.confirm_and_commit(
            existing_project=existing,
            mapped_data=new_extension,
            strategy=MergeStrategy.MERGE_APPEND
        )

        # 1. Existing elements MUST be completely preserved
        self.assertEqual(len(merged["nodes"]), existing_nodes_count + 2)
        self.assertEqual(len(merged["members"]), existing_members_count + 1)

        # 2. Existing original N1 (z=0) still intact
        orig_n1 = next(n for n in merged["nodes"] if n["id"] == "N1")
        self.assertEqual(orig_n1["z"], 0.0)

        # 3. New node was renamed safely to prevent collision
        reassigned_node = next(n for n in merged["nodes"] if n["z"] == 10.5 and n["x"] == 0.0)
        self.assertNotEqual(reassigned_node["id"], "N1")
        self.assertTrue(reassigned_node["id"].startswith("N1_imp"))


def run_all_cad_bim_verification_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCadBimInteroperability)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise RuntimeError("CAD/BIM interoperability verification tests failed!")
    print("\n[PHASE 13] All CAD & BIM Interoperability tests PASSED with 100% success rate.\n")


if __name__ == "__main__":
    run_all_cad_bim_verification_tests()
