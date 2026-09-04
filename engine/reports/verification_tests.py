"""
STRUCTURE-X ULTIMATE — PROFESSIONAL ENGINEERING REPORTING VERIFICATION TESTS (PHASE 14)
Automated verification suite validating:
- Full 24-section calculation report assembly
- Concrete & Steel code compliance calculations (ACI 318-19, Eurocode 2, AISC 360-16, Eurocode 3)
- Modal dynamic eigenvalue synthesis & participation verification (≥90% mass participation)
- Lateral drift and story shear code evaluations (ASCE 7-16 2.0% limit)
- Multi-format exporters: HTML, PDF print stylesheet, Excel XML, CSV
- Embedded SVG visualizations: 3D model, internal force diagrams (BMD/SFD), and charts
"""

import unittest
from engine.reports import (
    EngineeringReportGenerator,
    ReportExporter,
    DesignStatus,
    ReportExportFormat,
)


def create_sample_model():
    """Generates a realistic structural building model."""
    return {
        "projectName": "Apex Financial Tower",
        "version": "5.0.0-PRO",
        "units": "kN-m, C",
        "stories": [
            {"id": "STORY_BASE", "name": "Base / Foundation", "elevation": 0.0, "height": 0.0},
            {"id": "STORY_1", "name": "Story 1", "elevation": 3.5, "height": 3.5},
            {"id": "STORY_2", "name": "Story 2 (Roof)", "elevation": 7.0, "height": 3.5}
        ],
        "gridLinesX": [
            {"id": "GX_1", "axis": "X", "label": "1", "coordinate": -6.0},
            {"id": "GX_2", "axis": "X", "label": "2", "coordinate": -2.0},
            {"id": "GX_3", "axis": "X", "label": "3", "coordinate": 2.0},
            {"id": "GX_4", "axis": "X", "label": "4", "coordinate": 6.0}
        ],
        "gridLinesY": [
            {"id": "GY_A", "axis": "Y", "label": "A", "coordinate": -4.0},
            {"id": "GY_B", "axis": "Y", "label": "B", "coordinate": 0.0},
            {"id": "GY_C", "axis": "Y", "label": "C", "coordinate": 4.0}
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
                "name": "400x400 RC Column",
                "shape": "rectangular",
                "materialId": "MAT-C30",
                "area": 1600.0,
                "momentOfInertiaIxx": 213333.3,
                "momentOfInertiaIyy": 213333.3,
                "torsionalConstantJ": 360000.0,
                "weightPerMeter": 100.0,
                "dimensions": {"width": 400, "height": 400}
            },
            {
                "id": "SEC-300X500RC",
                "name": "300x500 RC Beam",
                "shape": "rectangular",
                "materialId": "MAT-C30",
                "area": 1500.0,
                "momentOfInertiaIxx": 312500.0,
                "momentOfInertiaIyy": 112500.0,
                "torsionalConstantJ": 280000.0,
                "weightPerMeter": 93.8,
                "dimensions": {"width": 300, "height": 500}
            }
        ],
        "nodes": [
            {"id": "N0", "x": -6.0, "y": 0.0, "z": -4.0, "isRestrained": True},
            {"id": "N1", "x": 6.0, "y": 0.0, "z": -4.0, "isRestrained": True},
            {"id": "N2", "x": -6.0, "y": 3.5, "z": -4.0},
            {"id": "N3", "x": 6.0, "y": 3.5, "z": -4.0},
            {"id": "N4", "x": -6.0, "y": 7.0, "z": -4.0},
            {"id": "N5", "x": 6.0, "y": 7.0, "z": -4.0},
        ],
        "members": [
            {
                "id": "C1",
                "name": "Column C1",
                "type": "column",
                "startNodeId": "N0",
                "endNodeId": "N2",
                "sectionId": "SEC-COL-400X400",
                "length": 3.5,
                "forces": {
                    "axialP": -850.0,
                    "shearV2": 34.0,
                    "shearV3": 12.0,
                    "torsionT": 4.5,
                    "momentM2": 18.0,
                    "momentM3": 58.5,
                    "utilizationRatio": 0.68
                }
            },
            {
                "id": "B1",
                "name": "Beam B1",
                "type": "beam",
                "startNodeId": "N2",
                "endNodeId": "N3",
                "sectionId": "SEC-300X500RC",
                "length": 12.0,
                "distributedLoad": 24.0,
                "forces": {
                    "axialP": -15.0,
                    "shearV2": 58.6,
                    "shearV3": 2.0,
                    "torsionT": 6.5,
                    "momentM2": 8.0,
                    "momentM3": 88.4,
                    "utilizationRatio": 0.71
                }
            }
        ],
        "slabs": [
            {
                "id": "S1",
                "name": "Floor Slab S1",
                "story": "Story 1",
                "nodeIds": ["N2", "N3", "N4", "N5"],
                "thickness": 0.20,
                "loadDead": 3.0,
                "loadLive": 2.5
            }
        ],
        "walls": [
            {
                "id": "W1",
                "name": "Shear Wall SW-1",
                "story": "Story 1",
                "nodeIds": ["N0", "N1", "N2", "N3"],
                "thickness": 0.25
            }
        ]
    }


class TestProfessionalEngineeringReporting(unittest.TestCase):
    """Test suite for Phase 14 Professional Engineering Reporting Engine."""

    def setUp(self):
        self.model = create_sample_model()
        self.report = EngineeringReportGenerator.generate_from_model(
            self.model,
            custom_info={"projectNumber": "TEST-PHASE14-001"}
        )

    def test_project_information_and_metadata(self):
        """Validates all Project Information fields."""
        p = self.report.projectInfo
        self.assertEqual(p.projectName, "Apex Financial Tower")
        self.assertEqual(p.projectNumber, "TEST-PHASE14-001")
        self.assertIn("Structure-X", p.softwareName)
        self.assertTrue(len(p.engineerName) > 0)
        self.assertTrue(len(p.date) > 0)

    def test_units_and_codes_completeness(self):
        """Validates engineering units and standard design codes."""
        u = self.report.units
        self.assertEqual(u.force, "kN")
        self.assertEqual(u.stress, "MPa (N/mm²)")
        self.assertEqual(u.moment, "kN.m")

        c = self.report.designCodes
        self.assertIn("ACI 318", c.concreteCode)
        self.assertIn("AISC 360", c.steelCode)
        self.assertIn("ASCE 7", c.seismicCode)
        self.assertIn("ASCE 7", c.windCode)

    def test_geometry_and_takeoff(self):
        """Validates stories, grids, materials, sections, and geometry summary."""
        self.assertGreaterEqual(len(self.report.stories), 2)
        self.assertGreaterEqual(len(self.report.grids), 4)
        self.assertGreaterEqual(len(self.report.materials), 2)
        self.assertGreaterEqual(len(self.report.sections), 2)
        self.assertGreaterEqual(self.report.geometry.totalNodes, 6)
        self.assertGreaterEqual(self.report.geometry.totalMembers, 2)
        self.assertGreater(self.report.geometry.boundingSpanX, 0.0)

    def test_loads_and_combinations(self):
        """Validates loading cases, combinations, and solver settings."""
        self.assertGreaterEqual(len(self.report.loads), 1)
        self.assertGreaterEqual(len(self.report.loadCases), 4)
        self.assertGreaterEqual(len(self.report.loadCombinations), 5)
        self.assertIn("Direct Stiffness", self.report.analysisSettings.solverType)

    def test_modal_and_lateral_results(self):
        """Validates modal eigenvalue results, seismic RSA, and wind analysis."""
        m = self.report.modalResults
        self.assertGreaterEqual(len(m), 3)
        self.assertGreater(m[0].period, 0.0)
        self.assertGreater(m[0].frequency, 0.0)
        # Cumulative mass should exceed 90% for typical code compliance
        self.assertGreaterEqual(m[-1].cumulativeMassX, 90.0)

        # Seismic & Wind
        self.assertGreater(self.report.seismicResults.baseShearVx, 0.0)
        self.assertGreater(self.report.windResults.basicWindSpeed, 0.0)

    def test_drifts_shears_and_reactions(self):
        """Validates story drifts against code allowable limits and foundation reactions."""
        drifts = self.report.storyDrifts
        self.assertGreaterEqual(len(drifts), 2)
        for d in drifts:
            self.assertLessEqual(d.driftRatioX, 0.020, f"Drift ratio {d.driftRatioX} exceeds 2.0% limit")
            self.assertEqual(d.status, DesignStatus.PASS)

        shears = self.report.storyShears
        self.assertGreaterEqual(len(shears), 2)
        self.assertGreater(shears[-1].shearVx, shears[0].shearVx)

        rxns = self.report.reactions
        self.assertGreaterEqual(len(rxns), 1)
        self.assertGreater(rxns[0].fy, 0.0)

    def test_concrete_and_steel_code_design(self):
        """Validates concrete, steel, wall, and slab design results and calculation details."""
        cd = self.report.concreteDesign
        self.assertGreaterEqual(len(cd), 2)
        for c_elem in cd:
            self.assertLessEqual(c_elem.dcRatio, 1.0)
            self.assertEqual(c_elem.status, DesignStatus.PASS)
            self.assertIn("mm", c_elem.providedRebarDesc)

        st = self.report.steelDesign
        self.assertGreaterEqual(len(st), 2)
        for s_elem in st:
            self.assertLessEqual(s_elem.interactionRatio, 1.0)
            self.assertEqual(s_elem.status, DesignStatus.PASS)

        # Wall & Slab
        self.assertGreaterEqual(len(self.report.wallDesign), 1)
        self.assertGreaterEqual(len(self.report.slabDesign), 1)

        # Step-by-step calculations
        calcs = self.report.calculationDetails
        self.assertGreaterEqual(len(calcs), 3)
        for c in calcs:
            self.assertGreaterEqual(len(c.intermediateCalculations), 4)
            self.assertLessEqual(c.governingRatio, 1.0)
            self.assertEqual(c.status, DesignStatus.PASS)

        # Warnings & Limitations
        self.assertGreaterEqual(len(self.report.warnings), 1)
        self.assertGreaterEqual(len(self.report.limitations), 2)

    def test_html_and_pdf_export_rendering(self):
        """Validates HTML and print-ready PDF export with embedded SVG charts."""
        html_content = ReportExporter.export_to_html(self.report)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("Apex Financial Tower", html_content)
        self.assertIn("@media print", html_content)
        self.assertIn("<svg", html_content)  # Embedded 3D model and diagrams
        self.assertIn("Bending Moment Diagram", html_content)
        self.assertIn("Story Drift Ratio Profile", html_content)
        self.assertIn("PASS", html_content)

    def test_csv_export_format(self):
        """Validates structured CSV export."""
        csv_content = ReportExporter.export_to_csv(self.report)
        self.assertIn("PROJECT INFORMATION", csv_content)
        self.assertIn("Apex Financial Tower", csv_content)
        self.assertIn("STORIES", csv_content)
        self.assertIn("CONCRETE DESIGN", csv_content)
        self.assertIn("STEEL DESIGN", csv_content)
        self.assertTrue(len(csv_content.splitlines()) > 30)

    def test_excel_export_format(self):
        """Validates multi-sheet Excel SpreadsheetML export."""
        excel_content = ReportExporter.export_to_excel_xml(self.report)
        self.assertIn("<?xml version=\"1.0\"?>", excel_content)
        self.assertIn("<Workbook", excel_content)
        self.assertIn("ss:Name=\"Project Summary\"", excel_content)
        self.assertIn("ss:Name=\"Stories &amp; Grids\"", excel_content)
        self.assertIn("ss:Name=\"Drifts &amp; Shears\"", excel_content)
        self.assertIn("ss:Name=\"Concrete Design\"", excel_content)
        self.assertIn("ss:Name=\"Steel Design\"", excel_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
