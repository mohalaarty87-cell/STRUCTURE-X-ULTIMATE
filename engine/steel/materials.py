"""
STRUCTURE-X ULTIMATE — STRUCTURAL STEEL MATERIALS
Authoritative constitutive models for AISC 360-16 (ASTM) and Eurocode 3 (EN 10025).
All standard stress units stored in SI (MPa = N/mm^2).
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class SteelMaterial:
    """
    Constitutive model for structural steel.
    """
    name: str
    Fy: float                   # Minimum yield stress (MPa)
    Fu: float                   # Specified minimum tensile strength (MPa)
    E: float = 200000.0         # Modulus of elasticity (MPa, ~29,000 ksi)
    G: float = 77200.0          # Shear modulus (MPa, ~11,200 ksi)
    nu: float = 0.30            # Poisson's ratio
    density_kg_m3: float = 7850.0  # Mass density (kg/m^3)
    thermal_coeff: float = 1.2e-5  # Thermal expansion coefficient (1/°C)

    @property
    def fy(self) -> float:
        """Alias for yield strength."""
        return self.Fy

    @property
    def fu(self) -> float:
        """Alias for ultimate tensile strength."""
        return self.Fu

    @property
    def epsilon(self) -> float:
        """
        Eurocode 3 classification parameter:
        epsilon = sqrt(235 / fy)
        """
        return math.sqrt(235.0 / max(self.Fy, 1.0))

    # --- Pre-configured Standard ASTM Structural Grades ---

    @classmethod
    def a992(cls) -> "SteelMaterial":
        """ASTM A992 (Standard for Wide Flange shapes, Fy=50 ksi / 345 MPa)."""
        return cls(
            name="ASTM A992",
            Fy=345.0,
            Fu=450.0,
            E=200000.0,
            G=77200.0
        )

    @classmethod
    def a36(cls) -> "SteelMaterial":
        """ASTM A36 (Standard carbon steel, Fy=36 ksi / 250 MPa)."""
        return cls(
            name="ASTM A36",
            Fy=250.0,
            Fu=400.0,
            E=200000.0,
            G=77200.0
        )

    @classmethod
    def a572_gr50(cls) -> "SteelMaterial":
        """ASTM A572 Grade 50 (High-strength low-alloy, Fy=50 ksi / 345 MPa)."""
        return cls(
            name="ASTM A572 Gr. 50",
            Fy=345.0,
            Fu=450.0,
            E=200000.0,
            G=77200.0
        )

    @classmethod
    def a500_gr_b(cls, shape_type: str = "rect") -> "SteelMaterial":
        """ASTM A500 Grade B (Cold-formed HSS)."""
        if "round" in shape_type.lower() or "pipe" in shape_type.lower():
            return cls(name="ASTM A500 Gr. B (Round)", Fy=290.0, Fu=400.0)
        return cls(name="ASTM A500 Gr. B (Rect)", Fy=317.0, Fu=400.0)

    @classmethod
    def a500_gr_c(cls, shape_type: str = "rect") -> "SteelMaterial":
        """ASTM A500 Grade C (Cold-formed HSS)."""
        if "round" in shape_type.lower() or "pipe" in shape_type.lower():
            return cls(name="ASTM A500 Gr. C (Round)", Fy=317.0, Fu=427.0)
        return cls(name="ASTM A500 Gr. C (Rect)", Fy=345.0, Fu=427.0)

    # --- Pre-configured Standard Eurocode Grades (EN 10025-2) ---

    @classmethod
    def s235(cls) -> "SteelMaterial":
        """EN 10025-2 S235 (fy=235 MPa, fu=360 MPa)."""
        return cls(name="S235 (EN 10025)", Fy=235.0, Fu=360.0, E=210000.0, G=81000.0)

    @classmethod
    def s275(cls) -> "SteelMaterial":
        """EN 10025-2 S275 (fy=275 MPa, fu=430 MPa)."""
        return cls(name="S275 (EN 10025)", Fy=275.0, Fu=430.0, E=210000.0, G=81000.0)

    @classmethod
    def s355(cls) -> "SteelMaterial":
        """EN 10025-2 S355 (fy=355 MPa, fu=510 MPa)."""
        return cls(name="S355 (EN 10025)", Fy=355.0, Fu=510.0, E=210000.0, G=81000.0)

    @classmethod
    def s460(cls) -> "SteelMaterial":
        """EN 10025-2 S460 (fy=460 MPa, fu=540 MPa)."""
        return cls(name="S460 (EN 10025)", Fy=460.0, Fu=540.0, E=210000.0, G=81000.0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "Fy_MPa": self.Fy,
            "Fu_MPa": self.Fu,
            "E_MPa": self.E,
            "G_MPa": self.G,
            "nu": self.nu,
            "density_kg_m3": self.density_kg_m3,
            "epsilon_ec3": round(self.epsilon, 4)
        }
