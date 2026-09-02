"""
STRUCTURE-X ULTIMATE — PHASE 06 LOAD ENGINE
Comprehensive Load Management, Patterns, Types, Cases, Combinations,
Mass Source, and Static Equilibrium Verification Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any, Set
import math
import time

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from .materials import Material
from .sections import CrossSection
from .dof_system import NodeDOFSystem
from .frame_element_3d import FrameElement3D, MemberLoad, MemberInternalForces
from .shell_element_3d import ShellElement3D, ShellSurfaceLoad, ShellStressResult
from .meshing import MeshedAreaEntity


class LoadPatternType(str, Enum):
    DEAD = "DEAD"
    LIVE = "LIVE"
    ROOF_LIVE = "ROOF_LIVE"
    SUPER_DEAD = "SUPER_DEAD"
    WIND_X = "WIND_X"
    WIND_Y = "WIND_Y"
    SEISMIC_X = "SEISMIC_X"
    SEISMIC_Y = "SEISMIC_Y"
    TEMPERATURE = "TEMPERATURE"
    SNOW = "SNOW"
    RAIN = "RAIN"
    CUSTOM = "CUSTOM"


class LoadType(str, Enum):
    JOINT_LOAD = "JOINT_LOAD"
    FRAME_POINT_LOAD = "FRAME_POINT_LOAD"
    FRAME_DISTRIBUTED_LOAD = "FRAME_DISTRIBUTED_LOAD"
    AREA_LOAD = "AREA_LOAD"
    SHELL_PRESSURE = "SHELL_PRESSURE"
    TEMPERATURE_LOAD = "TEMPERATURE_LOAD"
    SUPPORT_DISPLACEMENT = "SUPPORT_DISPLACEMENT"
    GROUND_ACCELERATION = "GROUND_ACCELERATION"


class LoadCaseType(str, Enum):
    STATIC_LINEAR = "STATIC_LINEAR"
    MODAL = "MODAL"
    RESPONSE_SPECTRUM = "RESPONSE_SPECTRUM"
    EQUIVALENT_LATERAL_SEISMIC = "EQUIVALENT_LATERAL_SEISMIC"
    SETTLEMENT = "SETTLEMENT"
    THERMAL = "THERMAL"


class CombinationType(str, Enum):
    LINEAR_ADD = "LINEAR_ADD"
    ENVELOPE = "ENVELOPE"
    SRSS = "SRSS"
    ABSOLUTE_ADD = "ABSOLUTE_ADD"


class DesignCombinationType(str, Enum):
    ULS = "ULS"  # Ultimate Limit State (Strength)
    SLS_CHARACTERISTIC = "SLS_CHARACTERISTIC"
    SLS_FREQUENT = "SLS_FREQUENT"
    SLS_QUASI_PERMANENT = "SLS_QUASI_PERMANENT"
    SEISMIC_ACCIDENTAL = "SEISMIC_ACCIDENTAL"


@dataclass
class LoadPattern:
    """Definition of a single independent Load Pattern."""
    id: str
    name: str
    pattern_type: LoadPatternType
    self_weight_multiplier: float = 0.0
    description: str = ""


@dataclass
class JointLoad:
    """Concentrated force and moment at a node."""
    id: str
    node_id: str
    pattern_id: str
    fx: float = 0.0  # N
    fy: float = 0.0  # N
    fz: float = 0.0  # N
    mx: float = 0.0  # N*m
    my: float = 0.0  # N*m
    mz: float = 0.0  # N*m


@dataclass
class FramePointLoad:
    """Concentrated force or moment at distance a from member start."""
    id: str
    member_id: str
    pattern_id: str
    direction: str = "global_Y"  # 'local_x', 'local_y', 'local_z', 'global_X', 'global_Y', 'global_Z'
    force_magnitude: float = 0.0  # N (positive in direction)
    moment_magnitude: float = 0.0  # N*m (around axis)
    dist_a: float = 0.0  # Distance from start node (m)
    relative_dist: bool = False  # If True, dist_a is ratio in [0, 1]


@dataclass
class FrameDistributedLoad:
    """Uniform or trapezoidal line load along member length."""
    id: str
    member_id: str
    pattern_id: str
    direction: str = "global_Y"  # 'local_x', 'local_y', 'local_z', 'global_X', 'global_Y', 'global_Z'
    w1: float = 0.0  # N/m at start
    w2: float = 0.0  # N/m at end
    dist_a: float = 0.0  # Start distance from start node (m)
    dist_b: Optional[float] = None  # End distance (m, None means member length)
    is_projected: bool = False  # Projected on horizontal plane for roof loads


@dataclass
class AreaLoad:
    """Uniform area surface load applied to slabs / area panels."""
    id: str
    area_entity_id: str
    pattern_id: str
    direction: str = "global_Y"  # 'global_Y', 'global_Z', 'global_X', 'local_z'
    magnitude: float = 0.0  # N/m2 (Pa)
    distribution_type: str = "two_way"  # 'two_way', 'one_way', 'direct_shell'
    one_way_direction_deg: float = 0.0  # Angle in degrees for one-way load transfer


@dataclass
class ShellPressure:
    """Pressure directly acting on a 3D shell finite element."""
    id: str
    shell_element_id: str
    pattern_id: str
    pressure: float = 0.0  # Pa (N/m2), positive outward or normal
    direction: str = "local_z"  # 'local_z', 'global_X', 'global_Y', 'global_Z'


@dataclass
class TemperatureLoad:
    """Thermal expansion or thermal gradient load on members or shells."""
    id: str
    target_id: str  # member_id or shell_id
    target_type: str  # 'frame' or 'shell'
    pattern_id: str
    delta_t_uniform: float = 0.0  # deg C (uniform temperature rise/fall)
    delta_t_gradient_y: float = 0.0  # deg C (top-bottom temperature difference through height)
    delta_t_gradient_z: float = 0.0  # deg C (left-right temperature difference through width)
    thermal_expansion_coeff: Optional[float] = None  # /deg C (defaults to material alpha)


@dataclass
class SupportDisplacement:
    """Prescribed settlement or translation/rotation at a restrained support."""
    id: str
    node_id: str
    pattern_id: str
    ux: float = 0.0  # m
    uy: float = 0.0  # m
    uz: float = 0.0  # m
    rx: float = 0.0  # rad
    ry: float = 0.0  # rad
    rz: float = 0.0  # rad


@dataclass
class GroundAcceleration:
    """Ground acceleration vector for seismic base excitation."""
    id: str
    pattern_id: str
    accel_x: float = 0.0  # m/s2 (or g fraction if specified)
    accel_y: float = 0.0  # m/s2
    accel_z: float = 0.0  # m/s2
    scale_factor: float = 1.0


@dataclass
class MassSourceFactor:
    pattern_id: str
    factor: float = 1.0


@dataclass
class MassSource:
    """Definition of building mass source for seismic & dynamic calculations."""
    id: str = "MASS_SOURCE_DEFAULT"
    name: str = "Standard Mass Source"
    include_self_mass: bool = True
    pattern_factors: List[MassSourceFactor] = field(default_factory=lambda: [
        MassSourceFactor(LoadPatternType.DEAD.value, 1.0),
        MassSourceFactor(LoadPatternType.SUPER_DEAD.value, 1.0),
        MassSourceFactor(LoadPatternType.LIVE.value, 0.30),
        MassSourceFactor(LoadPatternType.ROOF_LIVE.value, 0.0),
        MassSourceFactor(LoadPatternType.SNOW.value, 0.20),
    ])


@dataclass
class NodalMassResult:
    node_id: str
    mass_kg: float
    x: float
    y: float
    z: float


@dataclass
class StoryMassResult:
    story_name: str
    elevation_y: float
    mass_kg: float
    mass_tonnes: float
    center_of_mass_x: float
    center_of_mass_z: float


@dataclass
class MassSummary:
    total_mass_kg: float
    total_mass_tonnes: float
    total_weight_kn: float
    center_of_mass: Tuple[float, float, float]  # (X, Y, Z)
    nodal_masses: Dict[str, NodalMassResult]
    story_masses: List[StoryMassResult]


@dataclass
class LoadCaseItem:
    pattern_id: str
    scale_factor: float = 1.0


@dataclass
class LoadCase:
    """A single analysis load case defining combination of patterns or ground accelerations."""
    id: str
    name: str
    case_type: LoadCaseType = LoadCaseType.STATIC_LINEAR
    items: List[LoadCaseItem] = field(default_factory=list)
    mass_source_id: Optional[str] = None
    ground_accel: Optional[GroundAcceleration] = None
    displacements: List[SupportDisplacement] = field(default_factory=list)


@dataclass
class CombinationFactor:
    case_id: str
    factor: float = 1.0


@dataclass
class LoadCombination:
    """Design load combination combining multiple load cases."""
    id: str
    name: str
    combo_type: CombinationType = CombinationType.LINEAR_ADD
    design_type: DesignCombinationType = DesignCombinationType.ULS
    factors: List[CombinationFactor] = field(default_factory=list)
    description: str = ""


@dataclass
class StaticEquilibriumCheck:
    """Static equilibrium audit comparing Total Applied Loads vs Total Reactions."""
    case_or_pattern_id: str
    is_balanced: bool
    applied_force: Tuple[float, float, float]  # (Fx, Fy, Fz) in N
    applied_moment: Tuple[float, float, float]  # (Mx, My, Mz) about origin in N*m
    reaction_force: Tuple[float, float, float]  # (Rx, Ry, Rz) in N
    reaction_moment: Tuple[float, float, float]  # (RMx, RMy, RMz) about origin in N*m
    residual_force: Tuple[float, float, float]  # F_applied + R
    residual_moment: Tuple[float, float, float]
    relative_force_error_pct: float
    relative_moment_error_pct: float
    tolerance_pct: float = 0.01  # 0.01% standard tolerance


class LoadEngine:
    """
    Core Phase 06 Load Engine:
    Manages all load patterns, assigns loads, calculates mass distributions,
    generates Eurocode/ASCE load combinations, solves multi-case models,
    and conducts rigorous 3D static equilibrium verification.
    """

    def __init__(self):
        self.patterns: Dict[str, LoadPattern] = {}
        self.joint_loads: Dict[str, JointLoad] = {}
        self.frame_point_loads: Dict[str, FramePointLoad] = {}
        self.frame_distributed_loads: Dict[str, FrameDistributedLoad] = {}
        self.area_loads: Dict[str, AreaLoad] = {}
        self.shell_pressures: Dict[str, ShellPressure] = {}
        self.temperature_loads: Dict[str, TemperatureLoad] = {}
        self.support_displacements: Dict[str, SupportDisplacement] = {}
        self.ground_accelerations: Dict[str, GroundAcceleration] = {}
        
        self.mass_sources: Dict[str, MassSource] = {
            "MASS_SOURCE_DEFAULT": MassSource()
        }
        self.load_cases: Dict[str, LoadCase] = {}
        self.load_combinations: Dict[str, LoadCombination] = {}

        # Initialize default standard 12 load patterns
        self._init_default_patterns()

    def _init_default_patterns(self):
        default_defs = [
            (LoadPatternType.DEAD.value, "Dead (Self-Weight)", LoadPatternType.DEAD, 1.0),
            (LoadPatternType.SUPER_DEAD.value, "Superimposed Dead (Finishes/Partitions)", LoadPatternType.SUPER_DEAD, 0.0),
            (LoadPatternType.LIVE.value, "Live Load (Occupancy)", LoadPatternType.LIVE, 0.0),
            (LoadPatternType.ROOF_LIVE.value, "Roof Live Load", LoadPatternType.ROOF_LIVE, 0.0),
            (LoadPatternType.WIND_X.value, "Wind Load in +X Direction", LoadPatternType.WIND_X, 0.0),
            (LoadPatternType.WIND_Y.value, "Wind Load in +Z (CAD Y) Direction", LoadPatternType.WIND_Y, 0.0),
            (LoadPatternType.SEISMIC_X.value, "Seismic Equivalent Lateral Force +X", LoadPatternType.SEISMIC_X, 0.0),
            (LoadPatternType.SEISMIC_Y.value, "Seismic Equivalent Lateral Force +Z", LoadPatternType.SEISMIC_Y, 0.0),
            (LoadPatternType.TEMPERATURE.value, "Temperature Thermal Load", LoadPatternType.TEMPERATURE, 0.0),
            (LoadPatternType.SNOW.value, "Snow Load", LoadPatternType.SNOW, 0.0),
            (LoadPatternType.RAIN.value, "Rain Ponding Load", LoadPatternType.RAIN, 0.0),
            (LoadPatternType.CUSTOM.value, "Custom Special Load", LoadPatternType.CUSTOM, 0.0),
        ]
        for pid, name, ptype, sw in default_defs:
            self.patterns[pid] = LoadPattern(
                id=pid,
                name=name,
                pattern_type=ptype,
                self_weight_multiplier=sw
            )

    # -------------------------------------------------------------------------
    # Load Pattern Management
    # -------------------------------------------------------------------------

    def add_pattern(
        self,
        pattern_id: str,
        name: str,
        pattern_type: LoadPatternType,
        self_weight_multiplier: float = 0.0,
        description: str = ""
    ) -> LoadPattern:
        p = LoadPattern(
            id=pattern_id,
            name=name,
            pattern_type=pattern_type,
            self_weight_multiplier=self_weight_multiplier,
            description=description
        )
        self.patterns[pattern_id] = p
        return p

    def get_pattern(self, pattern_id: str) -> Optional[LoadPattern]:
        return self.patterns.get(pattern_id)

    # -------------------------------------------------------------------------
    # Load Assignment Methods
    # -------------------------------------------------------------------------

    def add_joint_load(
        self,
        load_id: str,
        node_id: str,
        pattern_id: str,
        fx: float = 0.0,
        fy: float = 0.0,
        fz: float = 0.0,
        mx: float = 0.0,
        my: float = 0.0,
        mz: float = 0.0
    ) -> JointLoad:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        jl = JointLoad(
            id=load_id,
            node_id=node_id,
            pattern_id=pattern_id,
            fx=fx, fy=fy, fz=fz,
            mx=mx, my=my, mz=mz
        )
        self.joint_loads[load_id] = jl
        return jl

    def add_frame_point_load(
        self,
        load_id: str,
        member_id: str,
        pattern_id: str,
        direction: str = "global_Y",
        force_magnitude: float = 0.0,
        moment_magnitude: float = 0.0,
        dist_a: float = 0.0,
        relative_dist: bool = False
    ) -> FramePointLoad:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        fpl = FramePointLoad(
            id=load_id,
            member_id=member_id,
            pattern_id=pattern_id,
            direction=direction,
            force_magnitude=force_magnitude,
            moment_magnitude=moment_magnitude,
            dist_a=dist_a,
            relative_dist=relative_dist
        )
        self.frame_point_loads[load_id] = fpl
        return fpl

    def add_frame_distributed_load(
        self,
        load_id: str,
        member_id: str,
        pattern_id: str,
        direction: str = "global_Y",
        w1: float = 0.0,
        w2: Optional[float] = None,
        dist_a: float = 0.0,
        dist_b: Optional[float] = None,
        is_projected: bool = False
    ) -> FrameDistributedLoad:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        fdl = FrameDistributedLoad(
            id=load_id,
            member_id=member_id,
            pattern_id=pattern_id,
            direction=direction,
            w1=w1,
            w2=w1 if w2 is None else w2,
            dist_a=dist_a,
            dist_b=dist_b,
            is_projected=is_projected
        )
        self.frame_distributed_loads[load_id] = fdl
        return fdl

    def add_area_load(
        self,
        load_id: str,
        area_entity_id: str,
        pattern_id: str,
        direction: str = "global_Y",
        magnitude: float = 0.0,
        distribution_type: str = "two_way",
        one_way_direction_deg: float = 0.0
    ) -> AreaLoad:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        al = AreaLoad(
            id=load_id,
            area_entity_id=area_entity_id,
            pattern_id=pattern_id,
            direction=direction,
            magnitude=magnitude,
            distribution_type=distribution_type,
            one_way_direction_deg=one_way_direction_deg
        )
        self.area_loads[load_id] = al
        return al

    def add_shell_pressure(
        self,
        load_id: str,
        shell_element_id: str,
        pattern_id: str,
        pressure: float = 0.0,
        direction: str = "local_z"
    ) -> ShellPressure:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        sp = ShellPressure(
            id=load_id,
            shell_element_id=shell_element_id,
            pattern_id=pattern_id,
            pressure=pressure,
            direction=direction
        )
        self.shell_pressures[load_id] = sp
        return sp

    def add_temperature_load(
        self,
        load_id: str,
        target_id: str,
        target_type: str,
        pattern_id: str,
        delta_t_uniform: float = 0.0,
        delta_t_gradient_y: float = 0.0,
        delta_t_gradient_z: float = 0.0,
        thermal_expansion_coeff: Optional[float] = None
    ) -> TemperatureLoad:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        tl = TemperatureLoad(
            id=load_id,
            target_id=target_id,
            target_type=target_type,
            pattern_id=pattern_id,
            delta_t_uniform=delta_t_uniform,
            delta_t_gradient_y=delta_t_gradient_y,
            delta_t_gradient_z=delta_t_gradient_z,
            thermal_expansion_coeff=thermal_expansion_coeff
        )
        self.temperature_loads[load_id] = tl
        return tl

    def add_support_displacement(
        self,
        load_id: str,
        node_id: str,
        pattern_id: str,
        ux: float = 0.0,
        uy: float = 0.0,
        uz: float = 0.0,
        rx: float = 0.0,
        ry: float = 0.0,
        rz: float = 0.0
    ) -> SupportDisplacement:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        sd = SupportDisplacement(
            id=load_id,
            node_id=node_id,
            pattern_id=pattern_id,
            ux=ux, uy=uy, uz=uz,
            rx=rx, ry=ry, rz=rz
        )
        self.support_displacements[load_id] = sd
        return sd

    def add_ground_acceleration(
        self,
        accel_id: str,
        pattern_id: str,
        accel_x: float = 0.0,
        accel_y: float = 0.0,
        accel_z: float = 0.0,
        scale_factor: float = 1.0
    ) -> GroundAcceleration:
        if pattern_id not in self.patterns:
            raise ValueError(f"Unknown Load Pattern ID '{pattern_id}'")
        ga = GroundAcceleration(
            id=accel_id,
            pattern_id=pattern_id,
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z,
            scale_factor=scale_factor
        )
        self.ground_accelerations[accel_id] = ga
        return ga

    # -------------------------------------------------------------------------
    # Load Cases and Combinations
    # -------------------------------------------------------------------------

    def add_load_case(
        self,
        case_id: str,
        name: str,
        case_type: LoadCaseType = LoadCaseType.STATIC_LINEAR,
        items: Optional[List[Tuple[str, float]]] = None,
        mass_source_id: Optional[str] = None
    ) -> LoadCase:
        case_items = [LoadCaseItem(pid, factor) for pid, factor in (items or [])]
        lc = LoadCase(
            id=case_id,
            name=name,
            case_type=case_type,
            items=case_items,
            mass_source_id=mass_source_id
        )
        self.load_cases[case_id] = lc
        return lc

    def add_load_combination(
        self,
        combo_id: str,
        name: str,
        combo_type: CombinationType = CombinationType.LINEAR_ADD,
        design_type: DesignCombinationType = DesignCombinationType.ULS,
        factors: Optional[List[Tuple[str, float]]] = None,
        description: str = ""
    ) -> LoadCombination:
        combo_factors = [CombinationFactor(cid, factor) for cid, factor in (factors or [])]
        comb = LoadCombination(
            id=combo_id,
            name=name,
            combo_type=combo_type,
            design_type=design_type,
            factors=combo_factors,
            description=description
        )
        self.load_combinations[combo_id] = comb
        return comb

    def generate_eurocode_combinations(self, include_seismic: bool = True, include_snow: bool = True) -> List[LoadCombination]:
        """
        Auto-generates standard Eurocode EN 1990 design combinations.
        ULS: 1.35 G + 1.50 Q + 1.50*0.6 W_X / W_Y
        SLS Characteristic: 1.0 G + 1.0 Q + 0.6 W_X
        SLS Quasi-Permanent: 1.0 G + 0.3 Q
        Seismic: 1.0 G + 0.3 Q + 1.0 E_X + 0.3 E_Y
        """
        generated = []
        D = LoadPatternType.DEAD.value
        SD = LoadPatternType.SUPER_DEAD.value
        L = LoadPatternType.LIVE.value
        WX = LoadPatternType.WIND_X.value
        WY = LoadPatternType.WIND_Y.value
        EX = LoadPatternType.SEISMIC_X.value
        EY = LoadPatternType.SEISMIC_Y.value
        S = LoadPatternType.SNOW.value

        # 1. ULS Gravity Only
        generated.append(self.add_load_combination(
            "EC_ULS_GRAV", "Eurocode ULS (1.35G + 1.50Q)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.35), (SD, 1.35), (L, 1.50)]
        ))

        # 2. ULS Wind X Dominant
        generated.append(self.add_load_combination(
            "EC_ULS_WX", "Eurocode ULS (1.35G + 1.05Q + 1.50W_X)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.35), (SD, 1.35), (L, 1.05), (WX, 1.50)]
        ))

        # 3. ULS Wind Y Dominant
        generated.append(self.add_load_combination(
            "EC_ULS_WY", "Eurocode ULS (1.35G + 1.05Q + 1.50W_Y)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.35), (SD, 1.35), (L, 1.05), (WY, 1.50)]
        ))

        # 4. SLS Characteristic
        generated.append(self.add_load_combination(
            "EC_SLS_CHAR", "Eurocode SLS Characteristic (1.0G + 1.0Q)",
            CombinationType.LINEAR_ADD, DesignCombinationType.SLS_CHARACTERISTIC,
            [(D, 1.00), (SD, 1.00), (L, 1.00)]
        ))

        # 5. SLS Quasi-Permanent
        generated.append(self.add_load_combination(
            "EC_SLS_QP", "Eurocode SLS Quasi-Permanent (1.0G + 0.3Q)",
            CombinationType.LINEAR_ADD, DesignCombinationType.SLS_QUASI_PERMANENT,
            [(D, 1.00), (SD, 1.00), (L, 0.30)]
        ))

        # 6. Seismic Accidental
        if include_seismic:
            generated.append(self.add_load_combination(
                "EC_SEIS_X", "Eurocode Seismic +X (1.0G + 0.3Q + 1.0E_X + 0.3E_Y)",
                CombinationType.LINEAR_ADD, DesignCombinationType.SEISMIC_ACCIDENTAL,
                [(D, 1.00), (SD, 1.00), (L, 0.30), (EX, 1.00), (EY, 0.30)]
            ))
            generated.append(self.add_load_combination(
                "EC_SEIS_Y", "Eurocode Seismic +Y (1.0G + 0.3Q + 0.3E_X + 1.0E_Y)",
                CombinationType.LINEAR_ADD, DesignCombinationType.SEISMIC_ACCIDENTAL,
                [(D, 1.00), (SD, 1.00), (L, 0.30), (EX, 0.30), (EY, 1.00)]
            ))

        return generated

    def generate_asce_combinations(self, include_seismic: bool = True) -> List[LoadCombination]:
        """
        Auto-generates standard ASCE 7-22 / ACI 318-19 LRFD / ASD design combinations.
        """
        generated = []
        D = LoadPatternType.DEAD.value
        SD = LoadPatternType.SUPER_DEAD.value
        L = LoadPatternType.LIVE.value
        Lr = LoadPatternType.ROOF_LIVE.value
        WX = LoadPatternType.WIND_X.value
        WY = LoadPatternType.WIND_Y.value
        EX = LoadPatternType.SEISMIC_X.value
        EY = LoadPatternType.SEISMIC_Y.value

        # ASCE LRFD 1: 1.4D
        generated.append(self.add_load_combination(
            "ASCE_LRFD_1", "ASCE LRFD 1 (1.4D)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.40), (SD, 1.40)]
        ))

        # ASCE LRFD 2: 1.2D + 1.6L + 0.5Lr
        generated.append(self.add_load_combination(
            "ASCE_LRFD_2", "ASCE LRFD 2 (1.2D + 1.6L + 0.5Lr)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.20), (SD, 1.20), (L, 1.60), (Lr, 0.50)]
        ))

        # ASCE LRFD 3: 1.2D + 1.0W_X + 1.0L + 0.5Lr
        generated.append(self.add_load_combination(
            "ASCE_LRFD_3X", "ASCE LRFD 3X (1.2D + 1.0W_X + 1.0L + 0.5Lr)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 1.20), (SD, 1.20), (WX, 1.00), (L, 1.00), (Lr, 0.50)]
        ))

        # ASCE LRFD 4: 0.9D + 1.0W_X (Uplift/Overturning)
        generated.append(self.add_load_combination(
            "ASCE_LRFD_4X", "ASCE LRFD 4X (0.9D + 1.0W_X)",
            CombinationType.LINEAR_ADD, DesignCombinationType.ULS,
            [(D, 0.90), (SD, 0.90), (WX, 1.00)]
        ))

        if include_seismic:
            # ASCE LRFD 5: 1.2D + 1.0E_X + 1.0L
            generated.append(self.add_load_combination(
                "ASCE_LRFD_5X", "ASCE LRFD 5X (1.2D + 1.0E_X + 1.0L)",
                CombinationType.LINEAR_ADD, DesignCombinationType.SEISMIC_ACCIDENTAL,
                [(D, 1.20), (SD, 1.20), (EX, 1.00), (L, 1.00)]
            ))
            # ASCE LRFD 6: 0.9D + 1.0E_X
            generated.append(self.add_load_combination(
                "ASCE_LRFD_6X", "ASCE LRFD 6X (0.9D + 1.0E_X)",
                CombinationType.LINEAR_ADD, DesignCombinationType.SEISMIC_ACCIDENTAL,
                [(D, 0.90), (SD, 0.90), (EX, 1.00)]
            ))

        return generated

    # -------------------------------------------------------------------------
    # Mass Source Calculation
    # -------------------------------------------------------------------------

    def calculate_mass_source(
        self,
        nodes: Dict[str, Tuple[float, float, float]],
        members: Dict[str, FrameElement3D],
        shell_elements: Dict[str, ShellElement3D],
        mass_source_id: str = "MASS_SOURCE_DEFAULT",
        gravity_accel: float = 9.80665
    ) -> MassSummary:
        """
        Calculates lumped nodal masses and story mass distributions from:
          1. Structural material density * element volumes (self-weight).
          2. Converted load patterns (Dead, Super Dead, Live with factor).
        """
        ms = self.mass_sources.get(mass_source_id, self.mass_sources["MASS_SOURCE_DEFAULT"])
        
        nodal_masses: Dict[str, float] = {nid: 0.0 for nid in nodes}

        # 1. Structural Element Self-Mass (Frame Elements)
        if ms.include_self_mass:
            for elem in members.values():
                rho = elem.material.density  # kg/m3
                vol = elem.section.area * elem.length  # m3
                elem_mass = rho * vol  # kg
                
                # Half to start node, half to end node
                if elem.start_node_id in nodal_masses:
                    nodal_masses[elem.start_node_id] += 0.5 * elem_mass
                if elem.end_node_id in nodal_masses:
                    nodal_masses[elem.end_node_id] += 0.5 * elem_mass

            # Shell Elements Self-Mass
            for se in shell_elements.values():
                rho = se.material.density  # kg/m3
                area = se.area  # m2
                vol = area * se.thickness  # m3
                shell_mass = rho * vol
                share = shell_mass / se.num_nodes
                for nid in se.node_ids:
                    if nid in nodal_masses:
                        nodal_masses[nid] += share

        # 2. Converted Loads via Pattern Multipliers
        for pf in ms.pattern_factors:
            if abs(pf.factor) < 1e-9:
                continue
            
            # Joint loads (vertical FY loads -> mass = abs(FY) / g * factor)
            for jl in self.joint_loads.values():
                if jl.pattern_id == pf.pattern_id:
                    # Mass from FY
                    m_fy = (abs(jl.fy) / gravity_accel) * pf.factor
                    if jl.node_id in nodal_masses:
                        nodal_masses[jl.node_id] += m_fy

            # Frame distributed loads -> convert to total force / g
            for fdl in self.frame_distributed_loads.values():
                if fdl.pattern_id == pf.pattern_id and fdl.member_id in members:
                    elem = members[fdl.member_id]
                    w_avg = 0.5 * (abs(fdl.w1) + abs(fdl.w2))
                    L_load = elem.length if fdl.dist_b is None else (fdl.dist_b - fdl.dist_a)
                    tot_force = w_avg * max(0.0, L_load)
                    tot_mass = (tot_force / gravity_accel) * pf.factor
                    if elem.start_node_id in nodal_masses:
                        nodal_masses[elem.start_node_id] += 0.5 * tot_mass
                    if elem.end_node_id in nodal_masses:
                        nodal_masses[elem.end_node_id] += 0.5 * tot_mass

            # Area loads -> convert to shell nodal masses
            for al in self.area_loads.values():
                if al.pattern_id == pf.pattern_id:
                    for se in shell_elements.values():
                        if se.parent_entity_id == al.area_entity_id or al.area_entity_id in se.element_id:
                            tot_force = abs(al.magnitude) * se.area
                            tot_mass = (tot_force / gravity_accel) * pf.factor
                            share = tot_mass / se.num_nodes
                            for nid in se.node_ids:
                                if nid in nodal_masses:
                                    nodal_masses[nid] += share

        # Calculate Totals & Center of Mass
        total_mass_kg = sum(nodal_masses.values())
        total_mass_tonnes = total_mass_kg / 1000.0
        total_weight_kn = (total_mass_kg * gravity_accel) / 1000.0

        if total_mass_kg > 1e-9:
            cm_x = sum(nodal_masses[nid] * nodes[nid][0] for nid in nodes) / total_mass_kg
            cm_y = sum(nodal_masses[nid] * nodes[nid][1] for nid in nodes) / total_mass_kg
            cm_z = sum(nodal_masses[nid] * nodes[nid][2] for nid in nodes) / total_mass_kg
        else:
            cm_x = cm_y = cm_z = 0.0

        # Build nodal mass result map
        nodal_res = {
            nid: NodalMassResult(
                node_id=nid,
                mass_kg=nodal_masses[nid],
                x=nodes[nid][0],
                y=nodes[nid][1],
                z=nodes[nid][2]
            )
            for nid in nodes
        }

        # Story Mass Grouping (group by unique elevation Y)
        story_elevations = sorted(list(set(round(nodes[nid][1], 3) for nid in nodes)))
        story_masses = []
        for idx, elev in enumerate(story_elevations):
            story_nodes = [nid for nid in nodes if abs(nodes[nid][1] - elev) < 0.05]
            st_mass = sum(nodal_masses[nid] for nid in story_nodes)
            if st_mass > 1e-9:
                st_cm_x = sum(nodal_masses[nid] * nodes[nid][0] for nid in story_nodes) / st_mass
                st_cm_z = sum(nodal_masses[nid] * nodes[nid][2] for nid in story_nodes) / st_mass
            else:
                st_cm_x = st_cm_z = 0.0

            story_masses.append(StoryMassResult(
                story_name=f"Level {idx+1} (Y={elev:.2f}m)",
                elevation_y=elev,
                mass_kg=st_mass,
                mass_tonnes=st_mass / 1000.0,
                center_of_mass_x=st_cm_x,
                center_of_mass_z=st_cm_z
            ))

        return MassSummary(
            total_mass_kg=total_mass_kg,
            total_mass_tonnes=total_mass_tonnes,
            total_weight_kn=total_weight_kn,
            center_of_mass=(cm_x, cm_y, cm_z),
            nodal_masses=nodal_res,
            story_masses=story_masses
        )

    # -------------------------------------------------------------------------
    # Equivalent Static Seismic Forces via Mass Source
    # -------------------------------------------------------------------------

    def generate_equivalent_static_seismic_forces(
        self,
        nodes: Dict[str, Tuple[float, float, float]],
        mass_summary: MassSummary,
        seismic_coefficient_c_s: float = 0.15,  # Cs = Sds / (R / Ie)
        direction: str = "X",  # 'X' or 'Z' (CAD Y)
        pattern_id: str = "SEISMIC_X"
    ) -> Dict[str, float]:
        """
        Computes ASCE 7 / Eurocode 8 vertical distribution of seismic lateral forces:
          F_x = C_vx * V_base
          where C_vx = (w_x * h_x^k) / sum(w_i * h_i^k)
        """
        V_base = seismic_coefficient_c_s * (mass_summary.total_mass_kg * 9.80665)  # N
        k_exponent = 1.0  # Linear for T <= 0.5s

        # Height above base
        min_elev = min(n[1] for n in nodes.values()) if nodes else 0.0
        
        sum_w_h_k = 0.0
        node_weights = {}
        for nid, n_mass in mass_summary.nodal_masses.items():
            h_i = max(0.0, nodes[nid][1] - min_elev)
            w_i = n_mass.mass_kg * 9.80665
            wh = w_i * (h_i ** k_exponent)
            node_weights[nid] = (w_i, h_i, wh)
            sum_w_h_k += wh

        forces = {}
        for nid, (w_i, h_i, wh) in node_weights.items():
            if sum_w_h_k > 1e-9:
                c_vx = wh / sum_w_h_k
                f_i = c_vx * V_base
            else:
                f_i = (w_i / (mass_summary.total_mass_kg * 9.80665 + 1e-9)) * V_base if mass_summary.total_mass_kg > 0 else 0.0
            
            forces[nid] = f_i
            # Add to joint loads for this pattern
            if direction.upper() == 'X':
                self.add_joint_load(f"SEIS_AUTO_{pattern_id}_{nid}", nid, pattern_id, fx=f_i)
            elif direction.upper() == 'Z':
                self.add_joint_load(f"SEIS_AUTO_{pattern_id}_{nid}", nid, pattern_id, fz=f_i)
            elif direction.upper() == 'Y':
                self.add_joint_load(f"SEIS_AUTO_{pattern_id}_{nid}", nid, pattern_id, fy=f_i)

        return forces

    # -------------------------------------------------------------------------
    # Static Equilibrium Verification
    # -------------------------------------------------------------------------

    def verify_static_equilibrium(
        self,
        target_id: str,  # Pattern ID or Case ID
        applied_forces: Tuple[float, float, float],  # (Fx, Fy, Fz) in N
        applied_moments: Tuple[float, float, float],  # (Mx, My, Mz) about (0,0,0)
        reactions: Dict[str, Tuple[float, float, float, float, float, float]],  # node_id -> (fx, fy, fz, mx, my, mz)
        node_coords: Dict[str, Tuple[float, float, float]],
        tolerance_pct: float = 0.01
    ) -> StaticEquilibriumCheck:
        """
        Performs 6-DOF static equilibrium audit:
          Sum(F_applied) + Sum(Reactions) = 0
          Sum(M_applied) + Sum(M_reactions + r x F_reactions) = 0
        """
        # Sum reactions and reaction moments about origin (0, 0, 0)
        tot_rx = sum(r[0] for r in reactions.values())
        tot_ry = sum(r[1] for r in reactions.values())
        tot_rz = sum(r[2] for r in reactions.values())
        
        tot_rmx = sum(r[3] for r in reactions.values())
        tot_rmy = sum(r[4] for r in reactions.values())
        tot_rmz = sum(r[5] for r in reactions.values())

        # Cross-product contributions of reaction forces: r x F
        for nid, r in reactions.items():
            if nid in node_coords:
                x, y, z = node_coords[nid]
                fx, fy, fz = r[0], r[1], r[2]
                # r x F = (y*Fz - z*Fy, z*Fx - x*Fz, x*Fy - y*Fx)
                tot_rmx += (y * fz - z * fy)
                tot_rmy += (z * fx - x * fz)
                tot_rmz += (x * fy - y * fx)

        # Residuals
        res_fx = applied_forces[0] + tot_rx
        res_fy = applied_forces[1] + tot_ry
        res_fz = applied_forces[2] + tot_rz

        res_mx = applied_moments[0] + tot_rmx
        res_my = applied_moments[1] + tot_rmy
        res_mz = applied_moments[2] + tot_rmz

        applied_mag_f = math.sqrt(applied_forces[0]**2 + applied_forces[1]**2 + applied_forces[2]**2)
        res_mag_f = math.sqrt(res_fx**2 + res_fy**2 + res_fz**2)

        applied_mag_m = math.sqrt(applied_moments[0]**2 + applied_moments[1]**2 + applied_moments[2]**2)
        res_mag_m = math.sqrt(res_mx**2 + res_my**2 + res_mz**2)

        rel_err_f_pct = (res_mag_f / max(1.0, applied_mag_f)) * 100.0
        rel_err_m_pct = (res_mag_m / max(1.0, applied_mag_m)) * 100.0

        is_balanced = (rel_err_f_pct <= tolerance_pct) and (rel_err_m_pct <= max(1.0, tolerance_pct * 10))

        return StaticEquilibriumCheck(
            case_or_pattern_id=target_id,
            is_balanced=is_balanced,
            applied_force=applied_forces,
            applied_moment=applied_moments,
            reaction_force=(tot_rx, tot_ry, tot_rz),
            reaction_moment=(tot_rmx, tot_rmy, tot_rmz),
            residual_force=(res_fx, res_fy, res_fz),
            residual_moment=(res_mx, res_my, res_mz),
            relative_force_error_pct=rel_err_f_pct,
            relative_moment_error_pct=rel_err_m_pct,
            tolerance_pct=tolerance_pct
        )

    # -------------------------------------------------------------------------
    # Load Validation Engine
    # -------------------------------------------------------------------------

    def validate_loads(
        self,
        nodes: Dict[str, Tuple[float, float, float]],
        members: Dict[str, FrameElement3D],
        shell_elements: Dict[str, ShellElement3D],
        area_entities: Optional[Dict[str, MeshedAreaEntity]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validates all loads, cases, combinations, and mass sources for integrity.
        Returns list of warning and error diagnostics.
        """
        diagnostics = []

        # 1. Joint Loads
        for jl in self.joint_loads.values():
            if jl.node_id not in nodes:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_NODE_REFERENCE",
                    "id": jl.id,
                    "message": f"Joint load '{jl.id}' targets non-existent node '{jl.node_id}'."
                })
            if jl.pattern_id not in self.patterns:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_PATTERN_REFERENCE",
                    "id": jl.id,
                    "message": f"Joint load '{jl.id}' references non-existent pattern '{jl.pattern_id}'."
                })

        # 2. Frame Point Loads
        for fpl in self.frame_point_loads.values():
            if fpl.member_id not in members:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_MEMBER_REFERENCE",
                    "id": fpl.id,
                    "message": f"Frame point load '{fpl.id}' targets non-existent member '{fpl.member_id}'."
                })
            else:
                mem = members[fpl.member_id]
                max_d = 1.0 if fpl.relative_dist else mem.length
                if fpl.dist_a < 0 or fpl.dist_a > max_d * 1.001:
                    diagnostics.append({
                        "severity": "WARNING",
                        "type": "LOAD_OUT_OF_BOUNDS",
                        "id": fpl.id,
                        "message": f"Frame point load distance {fpl.dist_a} exceeds member length {mem.length}m."
                    })

        # 3. Frame Distributed Loads
        for fdl in self.frame_distributed_loads.values():
            if fdl.member_id not in members:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_MEMBER_REFERENCE",
                    "id": fdl.id,
                    "message": f"Frame line load '{fdl.id}' targets non-existent member '{fdl.member_id}'."
                })
            else:
                mem = members[fdl.member_id]
                if fdl.dist_a < 0 or (fdl.dist_b is not None and fdl.dist_b > mem.length * 1.001):
                    diagnostics.append({
                        "severity": "WARNING",
                        "type": "LOAD_OUT_OF_BOUNDS",
                        "id": fdl.id,
                        "message": f"Frame line load range [{fdl.dist_a}, {fdl.dist_b}] exceeds member length {mem.length}m."
                    })

        # 4. Temperature Loads
        for tl in self.temperature_loads.values():
            if tl.target_type == 'frame' and tl.target_id not in members:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_TARGET_REFERENCE",
                    "id": tl.id,
                    "message": f"Temperature load targets non-existent frame member '{tl.target_id}'."
                })
            elif tl.target_type == 'shell' and tl.target_id not in shell_elements:
                diagnostics.append({
                    "severity": "ERROR",
                    "type": "INVALID_TARGET_REFERENCE",
                    "id": tl.id,
                    "message": f"Temperature load targets non-existent shell element '{tl.target_id}'."
                })

        # 5. Load Combinations (Check for Circular references & Missing Cases)
        for comb in self.load_combinations.values():
            for f in comb.factors:
                if f.case_id not in self.load_cases and f.case_id not in self.patterns:
                    diagnostics.append({
                        "severity": "ERROR",
                        "type": "INVALID_COMBO_FACTOR",
                        "id": comb.id,
                        "message": f"Load combination '{comb.id}' references unknown case/pattern '{f.case_id}'."
                    })

        return diagnostics
