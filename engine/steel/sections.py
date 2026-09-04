"""
STRUCTURE-X ULTIMATE — STRUCTURAL STEEL CROSS-SECTIONS & DATABASE
Engineering geometric properties, torsion/warping constants, compactness classification,
and comprehensive standard profiles library (AISC Wide-Flange, European IPE/HE, and HSS).
All internal dimensional properties are stored in SI units (mm, mm^2, mm^3, mm^4, mm^6, kg/m).
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from .types import SteelSectionType, SectionCompactness
from .materials import SteelMaterial


@dataclass
class SteelSection:
    """
    Complete geometric and structural parameters of a steel cross-section.
    Coordinate axes convention (AISC):
    - X-X (or Z-Z in EC3): Major principal bending axis (perpendicular to web)
    - Y-Y: Minor principal bending axis (parallel to web)
    """
    name: str
    section_type: SteelSectionType
    d: float                    # Total section depth (mm)
    bf: float                   # Flange width (mm) (or width B for HSS)
    tf: float                   # Flange thickness (mm) (or wall thickness for HSS)
    tw: float                   # Web thickness (mm) (or wall thickness for HSS)
    r: float = 10.0             # Root fillet radius / k-distance (mm)
    Ag: float = 0.0             # Gross cross-sectional area (mm^2)
    weight_kg_m: float = 0.0    # Linear mass (kg/m)
    Ix: float = 0.0             # Major moment of inertia (mm^4)
    Iy: float = 0.0             # Minor moment of inertia (mm^4)
    rx: float = 0.0             # Major radius of gyration (mm)
    ry: float = 0.0             # Minor radius of gyration (mm)
    Sx: float = 0.0             # Major elastic section modulus (mm^3)
    Sy: float = 0.0             # Minor elastic section modulus (mm^3)
    Zx: float = 0.0             # Major plastic section modulus (mm^3)
    Zy: float = 0.0             # Minor plastic section modulus (mm^3)
    J: float = 0.0              # Torsional constant (mm^4)
    Cw: float = 0.0             # Warping constant (mm^6)
    rts: float = 0.0            # Effective radius of gyration for LTB (mm)
    ho: float = 0.0             # Distance between flange centroids = d - tf (mm)
    perimeter_mm: float = 0.0   # External coating / painting perimeter (mm)
    fabrication_factor: float = 1.0  # Relative fabrication cost complexity factor

    def __post_init__(self):
        # Auto-compute dependent properties if left 0
        if self.ho <= 0.0:
            self.ho = max(self.d - self.tf, 1.0)
        
        if self.Ag <= 0.0:
            if self.section_type == SteelSectionType.I_SHAPE:
                self.Ag = 2.0 * self.bf * self.tf + (self.d - 2.0 * self.tf) * self.tw
            elif self.section_type == SteelSectionType.HSS_RECTANGULAR:
                self.Ag = 2.0 * self.tf * (self.bf + self.d - 2.0 * self.tf)
            elif self.section_type == SteelSectionType.HSS_ROUND:
                self.Ag = math.pi * ((self.d / 2.0)**2 - ((self.d - 2.0 * self.tf) / 2.0)**2)
            else:
                self.Ag = 2.0 * self.bf * self.tf + (self.d - 2.0 * self.tf) * self.tw

        if self.weight_kg_m <= 0.0:
            self.weight_kg_m = (self.Ag / 1.0e6) * 7850.0

        if self.rx <= 0.0 and self.Ag > 0 and self.Ix > 0:
            self.rx = math.sqrt(self.Ix / self.Ag)
        if self.ry <= 0.0 and self.Ag > 0 and self.Iy > 0:
            self.ry = math.sqrt(self.Iy / self.Ag)

        if self.Sx <= 0.0 and self.d > 0 and self.Ix > 0:
            self.Sx = (2.0 * self.Ix) / self.d
        if self.Sy <= 0.0 and self.bf > 0 and self.Iy > 0:
            self.Sy = (2.0 * self.Iy) / self.bf

        if self.Zx <= 0.0 and self.Sx > 0:
            self.Zx = 1.15 * self.Sx
        if self.Zy <= 0.0 and self.Sy > 0:
            self.Zy = 1.50 * self.Sy

        if self.Cw <= 0.0 and self.section_type == SteelSectionType.I_SHAPE:
            self.Cw = (self.Iy * (self.ho ** 2)) / 4.0

        if self.rts <= 0.0 and self.section_type == SteelSectionType.I_SHAPE:
            # AISC 360-16 Eq. F2-7: rts^2 = sqrt(Iy * Cw) / Sx
            if self.Sx > 0 and self.Cw > 0:
                self.rts = math.sqrt(math.sqrt(self.Iy * self.Cw) / self.Sx)
            elif self.ry > 0:
                self.rts = self.ry * 1.1

        if self.perimeter_mm <= 0.0:
            if self.section_type == SteelSectionType.I_SHAPE:
                self.perimeter_mm = 4.0 * self.bf + 2.0 * self.d - 2.0 * self.tw
            elif self.section_type == SteelSectionType.HSS_RECTANGULAR:
                self.perimeter_mm = 2.0 * (self.bf + self.d)
            elif self.section_type == SteelSectionType.HSS_ROUND:
                self.perimeter_mm = math.pi * self.d
            else:
                self.perimeter_mm = 2.0 * (self.bf + self.d)

    @property
    def b_over_2tf(self) -> float:
        """Flange slenderness ratio for I-shapes."""
        return (self.bf / 2.0) / max(self.tf, 0.1)

    @property
    def h_over_tw(self) -> float:
        """
        Web slenderness ratio (h/tw).
        AISC 360-16: h is the clear distance between flanges less the fillet or corner radius for rolled shapes.
        """
        clear_web = self.d - 2.0 * (self.tf + self.r)
        if clear_web > 0:
            return clear_web / max(self.tw, 0.1)
        return max(self.d - 2.0 * self.tf, 1.0) / max(self.tw, 0.1)

    def check_compression_compactness_aisc(self, material: SteelMaterial) -> Tuple[SectionCompactness, Dict[str, Any]]:
        """
        AISC 360-16 Table B4.1a (Members Subject to Axial Compression).
        """
        E = material.E
        Fy = material.Fy
        sqrt_E_Fy = math.sqrt(E / max(Fy, 1.0))

        if self.section_type == SteelSectionType.I_SHAPE:
            # Flanges: b/t <= 0.56 * sqrt(E / Fy)
            lambda_flange = self.b_over_2tf
            lambda_r_flange = 0.56 * sqrt_E_Fy
            flange_slender = lambda_flange > lambda_r_flange

            # Webs: h/tw <= 1.49 * sqrt(E / Fy)
            lambda_web = self.h_over_tw
            lambda_r_web = 1.49 * sqrt_E_Fy
            web_slender = lambda_web > lambda_r_web

            is_slender = flange_slender or web_slender
            compactness = SectionCompactness.SLENDER if is_slender else SectionCompactness.COMPACT
            details = {
                "flange_b_2tf": round(lambda_flange, 2),
                "flange_lambda_r": round(lambda_r_flange, 2),
                "flange_slender": flange_slender,
                "web_h_tw": round(lambda_web, 2),
                "web_lambda_r": round(lambda_r_web, 2),
                "web_slender": web_slender,
                "is_slender": is_slender
            }
            return compactness, details

        elif self.section_type == SteelSectionType.HSS_RECTANGULAR:
            # Walls of rectangular HSS: b/t <= 1.40 * sqrt(E / Fy)
            lambda_wall = (self.bf - 3.0 * self.tf) / max(self.tf, 0.1)
            lambda_r_wall = 1.40 * sqrt_E_Fy
            is_slender = lambda_wall > lambda_r_wall
            compactness = SectionCompactness.SLENDER if is_slender else SectionCompactness.COMPACT
            return compactness, {"wall_b_t": round(lambda_wall, 2), "lambda_r": round(lambda_r_wall, 2), "is_slender": is_slender}

        else:
            return SectionCompactness.COMPACT, {"is_slender": False}

    def check_flexural_compactness_aisc(self, material: SteelMaterial) -> Tuple[SectionCompactness, Dict[str, Any]]:
        """
        AISC 360-16 Table B4.1b (Members Subject to Flexure).
        Categorizes section as COMPACT, NON_COMPACT, or SLENDER.
        """
        E = material.E
        Fy = material.Fy
        sqrt_E_Fy = math.sqrt(E / max(Fy, 1.0))

        if self.section_type == SteelSectionType.I_SHAPE:
            # Flanges:
            # Compact limit lambda_p = 0.38 * sqrt(E / Fy)
            # Non-compact limit lambda_r = 1.0 * sqrt(E / Fy)
            lambda_f = self.b_over_2tf
            lp_f = 0.38 * sqrt_E_Fy
            lr_f = 1.00 * sqrt_E_Fy

            if lambda_f <= lp_f:
                flange_class = SectionCompactness.COMPACT
            elif lambda_f <= lr_f:
                flange_class = SectionCompactness.NON_COMPACT
            else:
                flange_class = SectionCompactness.SLENDER

            # Webs:
            # Compact limit lambda_p = 3.76 * sqrt(E / Fy)
            # Non-compact limit lambda_r = 5.70 * sqrt(E / Fy)
            lambda_w = self.h_over_tw
            lp_w = 3.76 * sqrt_E_Fy
            lr_w = 5.70 * sqrt_E_Fy

            if lambda_w <= lp_w:
                web_class = SectionCompactness.COMPACT
            elif lambda_w <= lr_w:
                web_class = SectionCompactness.NON_COMPACT
            else:
                web_class = SectionCompactness.SLENDER

            # Overall is governed by worst element
            if flange_class == SectionCompactness.SLENDER or web_class == SectionCompactness.SLENDER:
                overall = SectionCompactness.SLENDER
            elif flange_class == SectionCompactness.NON_COMPACT or web_class == SectionCompactness.NON_COMPACT:
                overall = SectionCompactness.NON_COMPACT
            else:
                overall = SectionCompactness.COMPACT

            details = {
                "flange_lambda": round(lambda_f, 2),
                "flange_lambda_p": round(lp_f, 2),
                "flange_lambda_r": round(lr_f, 2),
                "flange_class": flange_class.value,
                "web_lambda": round(lambda_w, 2),
                "web_lambda_p": round(lp_w, 2),
                "web_lambda_r": round(lr_w, 2),
                "web_class": web_class.value,
                "overall": overall.value
            }
            return overall, details

        return SectionCompactness.COMPACT, {"overall": SectionCompactness.COMPACT.value}


class SteelSectionDatabase:
    """
    Standard catalog of verified hot-rolled structural steel shapes and tubular sections.
    """
    _catalog: Dict[str, SteelSection] = {}

    @classmethod
    def initialize(cls):
        """Populates database with standard AISC W-Shapes, European IPE/HE, and HSS."""
        if cls._catalog:
            return

        # ----------------------------------------------------
        # 1. AISC Wide-Flange (W-Shapes) — Verified Properties
        # ----------------------------------------------------
        w_profiles = [
            # name, d, bf, tf, tw, r, Ag (mm2), wt (kg/m), Ix (1e6 mm4), Iy (1e6 mm4), Zx (1e3 mm3), Zy (1e3 mm3), J (1e3 mm4), Cw (1e9 mm6), rts (mm)
            ("W8X24", 201.0, 165.0, 10.2, 6.2, 8.0, 4570.0, 35.9, 34.5, 7.62, 380.0, 143.0, 142.0, 71.0, 47.0),
            ("W8X31", 203.0, 203.0, 11.0, 7.2, 9.0, 5890.0, 46.1, 45.8, 15.4, 498.0, 230.0, 222.0, 146.0, 56.4),
            ("W10X33", 247.0, 202.0, 11.0, 7.4, 9.0, 6260.0, 49.1, 71.2, 15.2, 636.0, 229.0, 241.0, 212.0, 55.6),
            ("W10X49", 253.0, 254.0, 14.2, 8.6, 11.0, 9290.0, 72.9, 113.0, 38.9, 990.0, 469.0, 579.0, 566.0, 70.1),
            ("W12X40", 302.0, 203.0, 13.1, 7.5, 10.0, 7610.0, 59.8, 128.0, 18.3, 941.0, 277.0, 375.0, 382.0, 56.1),
            ("W12X50", 310.0, 205.0, 16.3, 9.4, 11.0, 9420.0, 74.4, 164.0, 23.4, 1180.0, 354.0, 712.0, 514.0, 58.4),
            ("W12X65", 308.0, 305.0, 15.4, 9.9, 12.0, 12300.0, 96.7, 222.0, 72.4, 1610.0, 718.0, 907.0, 1570.0, 83.3),
            ("W14X68", 356.0, 255.0, 18.3, 10.5, 12.0, 12900.0, 101.0, 301.0, 50.4, 1880.0, 600.0, 1260.0, 1480.0, 71.4),
            ("W14X90", 356.0, 368.0, 18.0, 11.2, 13.0, 17100.0, 134.0, 416.0, 151.0, 2570.0, 1260.0, 1700.0, 4420.0, 100.0),
            ("W14X132", 373.0, 374.0, 26.2, 16.4, 15.0, 25000.0, 196.0, 637.0, 228.0, 3830.0, 1890.0, 5160.0, 7160.0, 103.0),
            ("W16X40", 407.0, 178.0, 12.8, 7.7, 10.0, 7610.0, 59.5, 216.0, 12.0, 1190.0, 211.0, 337.0, 467.0, 46.5),
            ("W16X50", 413.0, 181.0, 16.0, 9.7, 11.0, 9480.0, 74.4, 274.0, 15.5, 1490.0, 275.0, 628.0, 620.0, 47.8),
            ("W18X35", 450.0, 152.0, 10.8, 7.6, 9.0, 6650.0, 52.1, 212.0, 6.37, 1090.0, 134.0, 211.0, 313.0, 38.6),
            ("W18X50", 457.0, 190.0, 14.5, 9.0, 11.0, 9480.0, 74.4, 333.0, 16.7, 1660.0, 277.0, 516.0, 837.0, 49.3),
            ("W21X44", 526.0, 165.0, 11.4, 8.9, 10.0, 8390.0, 65.5, 351.0, 8.62, 1570.0, 167.0, 321.0, 566.0, 40.9),
            ("W21X62", 533.0, 210.0, 15.6, 10.2, 12.0, 11800.0, 92.3, 554.0, 24.0, 2360.0, 362.0, 753.0, 1610.0, 52.6),
            ("W24X55", 600.0, 178.0, 12.8, 10.0, 11.0, 10500.0, 81.8, 562.0, 12.1, 2200.0, 215.0, 479.0, 1030.0, 42.4),
            ("W24X68", 603.0, 228.0, 14.9, 10.5, 12.0, 12900.0, 101.0, 762.0, 29.5, 2900.0, 403.0, 778.0, 2550.0, 56.4),
            ("W27X84", 678.0, 253.0, 16.3, 11.7, 13.0, 16000.0, 125.0, 1190.0, 44.1, 4000.0, 544.0, 1170.0, 4770.0, 61.2),
            ("W30X90", 759.0, 264.0, 15.5, 12.0, 14.0, 17000.0, 134.0, 1500.0, 47.9, 4640.0, 567.0, 1190.0, 6540.0, 62.0),
            ("W36X135", 904.0, 304.0, 20.1, 15.2, 17.0, 25600.0, 201.0, 3250.0, 95.7, 8260.0, 988.0, 2710.0, 18700.0, 74.7),
        ]

        for (name, d, bf, tf, tw, r, Ag, wt, Ix_m, Iy_m, Zx_k, Zy_k, J_k, Cw_g, rts) in w_profiles:
            cls._catalog[name] = SteelSection(
                name=name,
                section_type=SteelSectionType.I_SHAPE,
                d=d,
                bf=bf,
                tf=tf,
                tw=tw,
                r=r,
                Ag=Ag,
                weight_kg_m=wt,
                Ix=Ix_m * 1.0e6,
                Iy=Iy_m * 1.0e6,
                rx=math.sqrt((Ix_m * 1.0e6) / Ag),
                ry=math.sqrt((Iy_m * 1.0e6) / Ag),
                Sx=(2.0 * Ix_m * 1.0e6) / d,
                Sy=(2.0 * Iy_m * 1.0e6) / bf,
                Zx=Zx_k * 1.0e3,
                Zy=Zy_k * 1.0e3,
                J=J_k * 1.0e3,
                Cw=Cw_g * 1.0e9,
                rts=rts,
                ho=d - tf,
                fabrication_factor=1.0
            )

        # ----------------------------------------------------
        # 2. European Profiles (IPE & HEB)
        # ----------------------------------------------------
        eu_profiles = [
            ("IPE 200", 200.0, 100.0, 8.5, 5.6, 12.0, 2850.0, 22.4, 19.43, 1.42, 220.6, 44.6, 69.8, 12.99, 25.1),
            ("IPE 240", 240.0, 120.0, 9.8, 6.2, 15.0, 3910.0, 30.7, 38.92, 2.84, 366.6, 73.9, 128.8, 37.39, 29.8),
            ("IPE 270", 270.0, 135.0, 10.2, 6.6, 15.0, 4590.0, 36.1, 57.90, 4.20, 484.0, 97.0, 159.4, 70.58, 33.3),
            ("IPE 300", 300.0, 150.0, 10.7, 7.1, 15.0, 5380.0, 42.2, 83.56, 6.04, 628.4, 125.2, 201.2, 125.9, 36.9),
            ("IPE 360", 360.0, 170.0, 12.7, 8.0, 18.0, 7270.0, 57.1, 162.7, 10.43, 1019.0, 191.1, 373.2, 313.6, 41.9),
            ("IPE 400", 400.0, 180.0, 13.5, 8.6, 21.0, 8450.0, 66.3, 231.3, 13.18, 1307.0, 229.0, 510.8, 490.0, 44.2),
            ("HEA 200", 190.0, 200.0, 10.0, 6.5, 18.0, 5380.0, 42.3, 36.92, 13.36, 429.5, 200.3, 209.8, 108.0, 55.4),
            ("HEA 240", 230.0, 240.0, 12.0, 7.5, 21.0, 7680.0, 60.3, 77.63, 27.69, 744.6, 345.2, 415.7, 328.5, 66.4),
            ("HEA 300", 290.0, 300.0, 14.0, 8.5, 27.0, 11250.0, 88.3, 182.6, 63.10, 1383.0, 641.2, 851.7, 1200.0, 82.5),
            ("HEB 200", 200.0, 200.0, 15.0, 9.0, 18.0, 7810.0, 61.3, 56.96, 20.03, 642.5, 305.8, 592.8, 171.1, 56.3),
            ("HEB 240", 240.0, 240.0, 17.0, 10.0, 21.0, 10600.0, 83.2, 112.6, 39.23, 1053.0, 498.4, 1027.0, 486.9, 67.2),
            ("HEB 300", 300.0, 300.0, 19.0, 11.0, 27.0, 14910.0, 117.0, 251.7, 85.63, 1869.0, 874.8, 1850.0, 1688.0, 83.7),
        ]

        for (name, d, bf, tf, tw, r, Ag, wt, Ix_m, Iy_m, Zx_k, Zy_k, J_k, Cw_g, rts) in eu_profiles:
            cls._catalog[name] = SteelSection(
                name=name,
                section_type=SteelSectionType.I_SHAPE,
                d=d,
                bf=bf,
                tf=tf,
                tw=tw,
                r=r,
                Ag=Ag,
                weight_kg_m=wt,
                Ix=Ix_m * 1.0e6,
                Iy=Iy_m * 1.0e6,
                rx=math.sqrt((Ix_m * 1.0e6) / Ag),
                ry=math.sqrt((Iy_m * 1.0e6) / Ag),
                Sx=(2.0 * Ix_m * 1.0e6) / d,
                Sy=(2.0 * Iy_m * 1.0e6) / bf,
                Zx=Zx_k * 1.0e3,
                Zy=Zy_k * 1.0e3,
                J=J_k * 1.0e3,
                Cw=Cw_g * 1.0e9,
                rts=rts,
                ho=d - tf,
                fabrication_factor=1.0
            )

        # ----------------------------------------------------
        # 3. Hollow Structural Sections (HSS Rectangular/Square)
        # ----------------------------------------------------
        hss_rect = [
            # name, d, b, t, Ag (mm2), wt (kg/m), Ix (1e6), Iy (1e6), Zx (1e3), Zy (1e3), J (1e3)
            ("HSS100X100X6", 100.0, 100.0, 6.0, 2220.0, 17.4, 3.25, 3.25, 78.4, 78.4, 5.09e3),
            ("HSS150X150X8", 150.0, 150.0, 8.0, 4420.0, 34.7, 14.8, 14.8, 237.0, 237.0, 23.9e3),
            ("HSS200X200X10", 200.0, 200.0, 10.0, 7360.0, 57.8, 43.5, 43.5, 518.0, 518.0, 71.3e3),
            ("HSS250X250X12", 250.0, 250.0, 12.0, 11100.0, 87.1, 104.0, 104.0, 990.0, 990.0, 173.0e3),
            ("HSS200X100X6", 200.0, 100.0, 6.0, 3350.0, 26.3, 17.0, 5.64, 203.0, 132.0, 13.4e3),
            ("HSS250X150X8", 250.0, 150.0, 8.0, 6020.0, 47.3, 53.6, 24.3, 513.0, 371.0, 55.4e3),
            ("HSS300X200X10", 300.0, 200.0, 10.0, 9360.0, 73.5, 124.0, 64.8, 988.0, 755.0, 142.0e3),
        ]

        for (name, d, b, t, Ag, wt, Ix_m, Iy_m, Zx_k, Zy_k, J_k) in hss_rect:
            cls._catalog[name] = SteelSection(
                name=name,
                section_type=SteelSectionType.HSS_RECTANGULAR,
                d=d,
                bf=b,
                tf=t,
                tw=t,
                r=2.0 * t,
                Ag=Ag,
                weight_kg_m=wt,
                Ix=Ix_m * 1.0e6,
                Iy=Iy_m * 1.0e6,
                rx=math.sqrt((Ix_m * 1.0e6) / Ag),
                ry=math.sqrt((Iy_m * 1.0e6) / Ag),
                Sx=(2.0 * Ix_m * 1.0e6) / d,
                Sy=(2.0 * Iy_m * 1.0e6) / b,
                Zx=Zx_k * 1.0e3,
                Zy=Zy_k * 1.0e3,
                J=J_k * 1.0e3,
                Cw=0.0,
                rts=math.sqrt((Iy_m * 1.0e6) / Ag),
                ho=d - t,
                fabrication_factor=1.12
            )

        # ----------------------------------------------------
        # 4. HSS Round / Pipe Sections
        # ----------------------------------------------------
        pipes = [
            ("PIPE 4 STD", 114.3, 114.3, 6.02, 6.02, 2050.0, 16.1, 3.01, 3.01, 69.4, 69.4, 6.02e3),
            ("PIPE 6 STD", 168.3, 168.3, 7.11, 7.11, 3600.0, 28.3, 11.7, 11.7, 185.0, 185.0, 23.4e3),
            ("PIPE 8 STD", 219.1, 219.1, 8.18, 8.18, 5420.0, 42.5, 30.2, 30.2, 360.0, 360.0, 60.4e3),
            ("PIPE 10 STD", 273.0, 273.0, 9.27, 9.27, 7700.0, 60.3, 68.3, 68.3, 650.0, 650.0, 136.0e3),
            ("PIPE 12 STD", 323.8, 323.8, 9.53, 9.53, 9410.0, 73.8, 117.0, 117.0, 940.0, 940.0, 234.0e3),
        ]

        for (name, od, _, t, _, Ag, wt, Ix_m, Iy_m, Zx_k, Zy_k, J_k) in pipes:
            cls._catalog[name] = SteelSection(
                name=name,
                section_type=SteelSectionType.HSS_ROUND,
                d=od,
                bf=od,
                tf=t,
                tw=t,
                r=0.0,
                Ag=Ag,
                weight_kg_m=wt,
                Ix=Ix_m * 1.0e6,
                Iy=Iy_m * 1.0e6,
                rx=math.sqrt((Ix_m * 1.0e6) / Ag),
                ry=math.sqrt((Iy_m * 1.0e6) / Ag),
                Sx=(2.0 * Ix_m * 1.0e6) / od,
                Sy=(2.0 * Iy_m * 1.0e6) / od,
                Zx=Zx_k * 1.0e3,
                Zy=Zy_k * 1.0e3,
                J=J_k * 1.0e3,
                Cw=0.0,
                rts=math.sqrt((Iy_m * 1.0e6) / Ag),
                ho=od - t,
                fabrication_factor=1.10
            )

    @classmethod
    def get(cls, name: str) -> Optional[SteelSection]:
        cls.initialize()
        key = name.strip().upper().replace(" ", "")
        for k, v in cls._catalog.items():
            if k.replace(" ", "") == key:
                return v
        return None

    @classmethod
    def all_sections(cls) -> List[SteelSection]:
        cls.initialize()
        return list(cls._catalog.values())

    @classmethod
    def filter_by_type(cls, section_type: SteelSectionType) -> List[SteelSection]:
        cls.initialize()
        return [s for s in cls._catalog.values() if s.section_type == section_type]


# Automatically trigger catalog initial setup
SteelSectionDatabase.initialize()
