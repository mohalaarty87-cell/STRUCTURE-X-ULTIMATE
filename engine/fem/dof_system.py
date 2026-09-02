"""
Node and Degree-of-Freedom (DOF) Management System
STRUCTURE-X ULTIMATE — 3D Frame FEM Engine
"""

from typing import Dict, List, Tuple, Optional, Set
import math

class NodeDOFSystem:
    """
    Manages 3D spatial nodes, global DOF indexing (6 DOFs per node),
    kinematic boundary conditions, and grounded nodal springs.
    """
    DOFS_PER_NODE = 6
    DOF_NAMES = ("UX", "UY", "UZ", "RX", "RY", "RZ")

    def __init__(self):
        self.nodes: Dict[str, Tuple[float, float, float]] = {}  # id -> (x, y, z)
        self.node_order: List[str] = []
        self.node_indices: Dict[str, int] = {}  # id -> sequential index 0..N-1
        
        # Restraints: node_id -> dict of {dof_index (0..5): is_restrained (bool)}
        self.restraints: Dict[str, Dict[int, bool]] = {}
        
        # Prescribed displacements: node_id -> dict of {dof_index: prescribed_value}
        self.prescribed_displacements: Dict[str, Dict[int, float]] = {}
        
        # Grounded springs: node_id -> dict of {dof_index: spring_stiffness_k}
        self.grounded_springs: Dict[str, Dict[int, float]] = {}

    def add_node(self, node_id: str, x: float, y: float, z: float) -> int:
        """Add or update a nodal point in 3D global Cartesian space."""
        if node_id not in self.node_indices:
            idx = len(self.node_order)
            self.node_indices[node_id] = idx
            self.node_order.append(node_id)
        else:
            idx = self.node_indices[node_id]
        
        self.nodes[node_id] = (float(x), float(y), float(z))
        return idx

    def set_restraint(self, node_id: str, 
                      ux: bool = False, uy: bool = False, uz: bool = False,
                      rx: bool = False, ry: bool = False, rz: bool = False):
        """Assign 6-DOF kinematic boundary restraints to a node."""
        if node_id not in self.node_indices:
            raise ValueError(f"Node '{node_id}' does not exist in DOF system.")
        
        self.restraints[node_id] = {
            0: bool(ux),
            1: bool(uy),
            2: bool(uz),
            3: bool(rx),
            4: bool(ry),
            5: bool(rz)
        }

    def set_prescribed_displacement(self, node_id: str, dof_index: int, value: float):
        """Set a prescribed nonzero displacement/rotation at a restrained DOF."""
        if node_id not in self.node_indices:
            raise ValueError(f"Node '{node_id}' does not exist in DOF system.")
        if dof_index < 0 or dof_index > 5:
            raise ValueError(f"DOF index must be between 0 and 5, received {dof_index}.")
        
        if node_id not in self.prescribed_displacements:
            self.prescribed_displacements[node_id] = {}
        self.prescribed_displacements[node_id][dof_index] = float(value)
        
        # Also mark this DOF as restrained
        if node_id not in self.restraints:
            self.restraints[node_id] = {d: False for d in range(6)}
        self.restraints[node_id][dof_index] = True

    def add_grounded_spring(self, node_id: str, 
                            kx: float = 0.0, ky: float = 0.0, kz: float = 0.0,
                            krx: float = 0.0, kry: float = 0.0, krz: float = 0.0):
        """Add grounded elastic spring stiffness to nodal DOFs."""
        if node_id not in self.node_indices:
            raise ValueError(f"Node '{node_id}' does not exist in DOF system.")
        
        stiffness_dict = {
            0: float(kx), 1: float(ky), 2: float(kz),
            3: float(krx), 4: float(kry), 5: float(krz)
        }
        self.grounded_springs[node_id] = {d: k for d, k in stiffness_dict.items() if k > 0.0}

    @property
    def total_nodes(self) -> int:
        return len(self.node_order)

    @property
    def total_dofs(self) -> int:
        return len(self.node_order) * self.DOFS_PER_NODE

    def get_node_global_dofs(self, node_id: str) -> List[int]:
        """Return the 6 global DOF indices [6i, 6i+1, 6i+2, 6i+3, 6i+4, 6i+5] for a node."""
        if node_id not in self.node_indices:
            raise ValueError(f"Node '{node_id}' not found in DOF system.")
        node_idx = self.node_indices[node_id]
        base_dof = node_idx * self.DOFS_PER_NODE
        return [base_dof + i for i in range(self.DOFS_PER_NODE)]

    def get_element_dof_indices(self, start_node_id: str, end_node_id: str) -> List[int]:
        """Return the 12 global DOF indices for a 2-node 3D beam element."""
        start_dofs = self.get_node_global_dofs(start_node_id)
        end_dofs = self.get_node_global_dofs(end_node_id)
        return start_dofs + end_dofs

    def get_shell_element_dof_indices(self, node_ids: List[str]) -> List[int]:
        """Return the global DOF indices (6 DOFs per node) for a 3-node or 4-node shell element."""
        indices = []
        for nid in node_ids:
            indices.extend(self.get_node_global_dofs(nid))
        return indices

    def partition_dofs(self) -> Tuple[List[int], List[int]]:
        """
        Partitions all system DOFs into:
          - free_dofs: Unconstrained / free degrees of freedom
          - restrained_dofs: Fixed or prescribed boundary degrees of freedom
        """
        free_dofs = []
        restrained_dofs = []

        for node_id in self.node_order:
            node_idx = self.node_indices[node_id]
            base_dof = node_idx * self.DOFS_PER_NODE
            node_restr = self.restraints.get(node_id, {})
            
            for d in range(self.DOFS_PER_NODE):
                global_dof = base_dof + d
                if node_restr.get(d, False):
                    restrained_dofs.append(global_dof)
                else:
                    free_dofs.append(global_dof)

        return free_dofs, restrained_dofs
