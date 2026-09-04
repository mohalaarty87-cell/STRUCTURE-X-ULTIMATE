"""
Cross-Section Geometric Property Definition
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
"""

from dataclasses import dataclass
import math
from typing import Optional

@dataclass
class CrossSection:
    """
    Parametric and arbitrary beam cross-section geometry.
    All dimensional properties stored in base SI units (m, m2, m4).
    Local coordinate convention:
      - Local x: Longitudinal beam axis (from node i to node j)
      - Local z: Major bending axis (or horizontal web)
      - Local y: Minor bending axis (or vertical depth)
    """
    id: str
    name: str
    area: float                 # A (m2)
    iz: float                   # Iz - Moment of inertia about local z-axis (m4) - Major axis
    iy: float                   # Iy - Moment of inertia about local y-axis (m4) - Minor axis
    torsion_j: float            # J - St. Venant Torsional constant (m4)
    shear_area_y: Optional[float] = None  # Asy - Effective shear area along local y (m2)
    shear_area_z: Optional[float] = None  # Asz - Effective shear area along local z (m2)
    depth: float = 0.0          # Overall depth (m)
    width: float = 0.0          # Overall width (m)

    @property
    def A(self) -> float:
        return self.area

    @property
    def Iz(self) -> float:
        return self.iz

    @property
    def moment_of_inertia_z(self) -> float:
        return self.iz

    @property
    def Iy(self) -> float:
        return self.iy

    @property
    def moment_of_inertia_y(self) -> float:
        return self.iy

    @property
    def J(self) -> float:
        return self.torsion_j

    @property
    def Asy(self) -> float:
        """Effective shear area in local y. Defaults to 5/6 * A if not specified."""
        if self.shear_area_y is not None and self.shear_area_y > 0:
            return self.shear_area_y
        return (5.0 / 6.0) * self.area

    @property
    def Asz(self) -> float:
        """Effective shear area in local z. Defaults to 5/6 * A if not specified."""
        if self.shear_area_z is not None and self.shear_area_z > 0:
            return self.shear_area_z
        return (5.0 / 6.0) * self.area

    @classmethod
    def rectangular(cls, id: str, name: str, width_b: float, depth_h: float) -> "CrossSection":
        """
        Solid rectangular section:
        width_b (m) along local z, depth_h (m) along local y.
        A = b * h
        Iz = (b * h^3) / 12 (bending in y direction about z)
        Iy = (h * b^3) / 12 (bending in z direction about y)
        J = b * h^3 * (1/3 - 0.21 * (h/b) * (1 - (h^4)/(12*b^4))) for b >= h
        """
        b = float(width_b)
        h = float(depth_h)
        area = b * h
        iz = (b * (h ** 3)) / 12.0
        iy = (h * (b ** 3)) / 12.0
        
        # Accurate St Venant torsion approximation for rectangle
        a_max = max(b, h)
        b_min = min(b, h)
        ratio = b_min / a_max
        beta_t = (1.0 / 3.0) - 0.21 * ratio * (1.0 - (ratio ** 4) / 12.0)
        j = beta_t * a_max * (b_min ** 3)

        asy = (5.0 / 6.0) * area
        asz = (5.0 / 6.0) * area

        return cls(
            id=id,
            name=name,
            area=area,
            iz=iz,
            iy=iy,
            torsion_j=j,
            shear_area_y=asy,
            shear_area_z=asz,
            depth=h,
            width=b
        )

    @classmethod
    def circular(cls, id: str, name: str, diameter: float) -> "CrossSection":
        """Solid circular section of diameter d (m)."""
        d = float(diameter)
        r = d / 2.0
        area = math.pi * (r ** 2)
        i = (math.pi * (d ** 4)) / 64.0
        j = (math.pi * (d ** 4)) / 32.0
        ashear = 0.9 * area

        return cls(
            id=id,
            name=name,
            area=area,
            iz=i,
            iy=i,
            torsion_j=j,
            shear_area_y=ashear,
            shear_area_z=ashear,
            depth=d,
            width=d
        )

    @classmethod
    def i_section(cls, id: str, name: str, depth_h: float, flange_width_bf: float, 
                  flange_thick_tf: float, web_thick_tw: float) -> "CrossSection":
        """
        Standard I / H-beam cross section.
        """
        h = float(depth_h)
        bf = float(flange_width_bf)
        tf = float(flange_thick_tf)
        tw = float(web_thick_tw)
        hw = h - 2 * tf

        area = 2.0 * bf * tf + hw * tw
        # Major axis Iz (bending in vertical web plane)
        iz = (bf * (h ** 3) - (bf - tw) * (hw ** 3)) / 12.0
        # Minor axis Iy (bending in lateral flange plane)
        iy = (2.0 * tf * (bf ** 3) + hw * (tw ** 3)) / 12.0
        # Torsional constant J
        j = (2.0 * bf * (tf ** 3) + hw * (tw ** 3)) / 3.0
        # Shear areas
        asy = hw * tw # Web resists vertical shear
        asz = 2.0 * (5.0 / 6.0) * bf * tf # Flanges resist lateral shear

        return cls(
            id=id,
            name=name,
            area=area,
            iz=iz,
            iy=iy,
            torsion_j=j,
            shear_area_y=asy,
            shear_area_z=asz,
            depth=h,
            width=bf
        )
