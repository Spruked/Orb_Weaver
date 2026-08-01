"""
Context & Correspondence Orchestrator - Compression Strategies
Three possible technical architectures plus ORBS-specific compilation.
"""

from .base import BaseStrategy
from .summary import SummaryStrategy
from .semantic_retrieval import SemanticRetrievalStrategy
from .hierarchical import HierarchicalStrategy
from .vault_compile import VaultCompileStrategy

__all__ = [
    "BaseStrategy",
    "SummaryStrategy", 
    "SemanticRetrievalStrategy",
    "HierarchicalStrategy",
    "VaultCompileStrategy"
]
