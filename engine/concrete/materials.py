"""
STRUCTURE-X ULTIMATE — CONCRETE & REBAR MATERIAL MODELS
Authoritative constitutive equations for ACI 318-19 and Eurocode 2 (EN 1992-1-1).
"""

import math
from dataclasses import dataclass
from .types import DesignCode, CodeEdition


@dataclass
class ConcreteMaterial:
    """
    Standard Reinforced Concrete constitutive parameters.
    Strength input is in MPa (N/mm^2).
    """
    fc_prime: float  # Specified compressive strength f'c (ACI) or characteristic cylinder fck (EC2) in MPa
    density_kg_m3: float = 2400.0  # Normalweight concrete density
    aggregate_factor_lambda: float = 1.0  # 1.0 for normalweight, 0.75-0.85 for lightweight

    def get_elastic_modulus_aci(self) -> float:
        """
        ACI 318-19 Clause 19.2.2.1:
        Ec = 4700 * sqrt(f'c) in MPa for normalweight concrete.
        """
        return 4700.0 * math.sqrt(max(self.fc_prime, 1.0))

    def get_elastic_modulus_ec2(self) -> float:
        """
        Eurocode 2 Table 3.1:
        Ecm = 22000 * ((fck + 8) / 10)^0.3 in MPa.
        """
        fcm = self.fc_prime + 8.0
        return 22000.0 * math.pow(fcm / 10.0, 0.3)

    def get_modulus_of_rupture_aci(self) -> float:
        """
        ACI 318-19 Clause 19.2.3.1:
        fr = 0.62 * lambda * sqrt(f'c) in MPa.
        """
        return 0.62 * self.aggregate_factor_lambda * math.sqrt(max(self.fc_prime, 1.0))

    def get_fctm_ec2(self) -> float:
        """
        Eurocode 2 Table 3.1:
        fctm = 0.30 * fck^(2/3) for fck <= 50 MPa.
        """
        if self.fc_prime <= 50.0:
            return 0.30 * math.pow(self.fc_prime, 2.0 / 3.0)
        return 2.12 * math.log(1.0 + (self.fc_prime + 8.0) / 10.0)

    def get_beta1_aci(self) -> float:
        """
        ACI 318-19 Table 22.2.2.4.3:
        beta1 is the depth factor for equivalent rectangular compressive stress block.
        For 17 <= f'c <= 28 MPa: beta1 = 0.85
        For 28 < f'c < 55 MPa: beta1 = 0.85 - 0.05 * (f'c - 28) / 7
        For f'c >= 55 MPa: beta1 = 0.65
        """
        if self.fc_prime <= 28.0:
            return 0.85
        elif self.fc_prime >= 55.0:
            return 0.65
        else:
            b1 = 0.85 - 0.05 * (self.fc_prime - 28.0) / 7.0
            return max(0.65, min(0.85, b1))

    def get_ec2_stress_block_factors(self) -> tuple[float, float]:
        """
        Eurocode 2 Clause 3.1.7(3):
        Returns (lambda_ec, eta_ec) factors for rectangular stress block.
        For fck <= 50 MPa: lambda = 0.8, eta = 1.0
        """
        if self.fc_prime <= 50.0:
            return 0.8, 1.0
        lambda_ec = 0.8 - (self.fc_prime - 50.0) / 400.0
        eta_ec = 1.0 - (self.fc_prime - 50.0) / 200.0
        return max(0.65, lambda_ec), max(0.65, eta_ec)

    def get_design_strength_ec2(self, gamma_c: float = 1.5, alpha_cc: float = 0.85) -> float:
        """
        Eurocode 2 Clause 3.1.6:
        fcd = alpha_cc * fck / gamma_c
        """
        return alpha_cc * self.fc_prime / gamma_c

    @property
    def ultimate_strain(self) -> float:
        """
        ACI 318-19 Cl. 22.2.2.1: eps_cu = 0.003
        """
        return 0.003


@dataclass
class RebarMaterial:
    """
    Standard Reinforcing Steel material parameters.
    Yield strength fy in MPa.
    """
    fy: float = 420.0  # Grade 60 (420 MPa) or B500B (500 MPa)
    Es: float = 200000.0  # Modulus of elasticity in MPa (200 GPa)
    fyt: Optional[float] = None  # Transverse rebar yield strength (default equal to fy)

    def __post_init__(self):
        if self.fyt is None:
            self.fyt = self.fy

    @property
    def yield_strain(self) -> float:
        return self.fy / self.Es

    def get_design_yield_strength_ec2(self, gamma_s: float = 1.15) -> float:
        """
        Eurocode 2 Clause 3.2.7:
        fyd = fyk / gamma_s
        """
        return self.fy / gamma_s
