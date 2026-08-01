"""
Context & Correspondence Orchestrator - ORBS Runtime Conductor

A production-ready ORBS orchestration layer for task-aware context reduction,
retrieval, Vault compilation, correspondence preparation, provenance and
articulation handoff. It includes three context reduction strategies:
- Summary (Possibility A)
- Semantic Retrieval (Possibility B)  
- Hierarchical Memory (Possibility C)

Integrated with ORBS Vault architecture where the Vault remains authoritative
and CCO working context packages are disposable projections.
"""

__version__ = "1.0.0"
__author__ = "ORBS Engineering"

from .models import (
    CompressRequest, CompressResponse,
    ContextRunRequest, ContextRunResponse,
    CompressionStrategy, OrchestrationMetadata,
    CanaryTestRequest, CanaryTestResponse
)
from .core.engine import ContextCorrespondenceOrchestrator
from .core.store import HandleStore
from .core.task_analyzer import TaskAnalyzer

__all__ = [
    "CompressRequest", "CompressResponse",
    "ContextRunRequest", "ContextRunResponse", 
    "CompressionStrategy", "OrchestrationMetadata",
    "CanaryTestRequest", "CanaryTestResponse",
    "ContextCorrespondenceOrchestrator", "HandleStore", "TaskAnalyzer"
]
