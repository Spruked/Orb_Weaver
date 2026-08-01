"""
Vault — MANDATORY (storage shape frozen), covariance computation
working. Does NOT implement Organized Doubt / re-challenge
scheduling — see challenge.py. Does NOT yet store KnowledgeClaims
(only promoted KnowledgeAtoms) pending resolution of GAP_A / GAP_F.
"""

from typing import Dict, List
import numpy as np

from .atoms import KnowledgeAtom, CorrespondenceEdge


class Vault:
    def __init__(self):
        self.atoms: Dict[str, KnowledgeAtom] = {}
        self.edges: List[CorrespondenceEdge] = []

    def add_atom(self, atom: KnowledgeAtom):
        if atom.atom_id in self.atoms:
            raise ValueError(f"atom_id {atom.atom_id} already exists")
        self.atoms[atom.atom_id] = atom

    def add_edge(self, edge: CorrespondenceEdge):
        for atom_id in (edge.source_atom_id, edge.target_atom_id):
            if atom_id not in self.atoms:
                raise ValueError(f"edge references unknown atom_id {atom_id}")
        self.edges.append(edge)

    def edges_for(self, atom_id: str) -> List[CorrespondenceEdge]:
        return [
            e for e in self.edges
            if atom_id in (e.source_atom_id, e.target_atom_id)
        ]

    def covariance_matrix(self) -> np.ndarray:
        """
        Covariance across all stored atoms' correspondence vectors.
        Required by geometry.MahalanobisGate. Raises if fewer than
        2 atoms (covariance undefined below that).
        """
        if len(self.atoms) < 2:
            raise ValueError("covariance_matrix requires at least 2 atoms")
        vectors = np.array([a.correspondence_vector.as_tuple() for a in self.atoms.values()])
        return np.cov(vectors, rowvar=False)
