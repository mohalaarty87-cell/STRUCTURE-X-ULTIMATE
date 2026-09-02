"""
Material Constitutive Representation
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Material:
    """
    Isotropic linear elastic material definition.
    All properties stored in base SI units (Pa, kg/m3).
    """
    id: str
    name: str
    elastic_modulus: float      # E in Pa (N/m2)
    poisson_ratio: float = 0.20 # nu
    density: float = 2500.0     # rho in kg/m3
    thermal_coef: float = 1.0e-5 # alpha (1/K)
    shear_modulus_val: Optional[float] = None # G in Pa

    @property
    def E(self) -> float:
        return self.elastic_modulus

    @property
    def nu(self) -> float:
        return self.poisson_ratio

    @property
    def G(self) -> float:
        """Shear Modulus G = E / (2 * (1 + nu))"""
        if self.shear_modulus_val is not None and self.shear_modulus_val > 0:
            return self.shear_modulus_val
        return self.elastic_modulus / (2.0 * (1.0 + self.poisson_ratio))

    @property
    def rho(self) -> float:
        return self.density

    # Standard Pre-defined Engineering Materials
    @classmethod
    def concrete_c30(cls, id: str = "MAT-C30") -> "Material":
        """Eurocode / ACI C30/37 Concrete (E = 33 GPa, nu = 0.20)"""
        return cls(id=id, name="Concrete C30/37", elastic_modulus=33.0e9, poisson_ratio=0.20, density=2500.0)

    @classmethod
    def concrete_c25(cls, id: str = "MAT-C25") -> "Material":
        """Eurocode / ACI C25/30 Concrete (E = 31 GPa, nu = 0.20)"""
        return cls(id=id, name="Concrete C25/30", elastic_modulus=31.0e9, poisson_ratio=0.20, density=2500.0)

    @classmethod
    def steel_s355(cls, id: str = "MAT-S355") -> "Material":
        """Structural Steel S355 / A992 (E = 210 GPa, nu = 0.30)"""
        return cls(id=id, name="Steel S355", elastic_modulus=210.0e9, poisson_ratio=0.30, density=7850.0)

    @classmethod
    def steel_s275(cls, id: str = "MAT-S275") -> "Material":
        """Structural Steel S275 / A36 (E = 200 GPa, nu = 0.30)"""
        return cls(id=id, name="Steel S275", elastic_modulus=200.0e9, poisson_ratio=0.30, density=7850.0)
