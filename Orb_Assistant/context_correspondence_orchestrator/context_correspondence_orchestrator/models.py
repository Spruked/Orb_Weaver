"""
Context & Correspondence Orchestrator - Data Models
Pydantic models for API requests/responses and internal data structures.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class CompressionStrategy(str, Enum):
    """Three possible technical architectures per the engineering analysis."""
    SUMMARY = "summary"                    # Possibility A - aggressive summarization
    SEMANTIC_RETRIEVAL = "semantic_retrieval"  # Possibility B - compressed representation + index
    HIERARCHICAL = "hierarchical"          # Possibility C - multi-level memory
    VAULT_COMPILE = "vault_compile"        # ORBS-specific: deterministic vault record compilation
    AUTO = "auto"                          # Let engine select based on source size and task


class SourceType(str, Enum):
    TEXT = "text"
    DOCUMENT = "document"
    CHAT_HISTORY = "chat_history"
    CODE = "code"
    MIXED = "mixed"
    VAULT_RECORDS = "vault_records"  # ORBS structured data


class CompressRequest(BaseModel):
    """POST /v1/compress request body."""
    source: str = Field(..., description="Raw source material to compress")
    source_type: SourceType = Field(default=SourceType.TEXT)
    task: str = Field(..., description="What the context will be used for")
    target_token_budget: int = Field(default=8000, ge=100, le=32000, 
                                     description="Target token budget for the CCO working context package")
    strategy: CompressionStrategy = Field(default=CompressionStrategy.AUTO)
    metadata: Optional[Dict[str, Any]] = Field(default=None, 
                                                  description="Optional user metadata")
    preserve_exact: Optional[List[str]] = Field(default=None,
                                                 description="Strings/facts that must be preserved verbatim")
    vault_schema: Optional[Dict[str, Any]] = Field(default=None,
                                                    description="ORBS vault schema for vault_compile mode")


class CompressResponse(BaseModel):
    """POST /v1/compress response."""
    context_handle: str = Field(..., description="Unique handle to retrieve the CCO working context package")
    strategy_used: CompressionStrategy
    original_tokens: int
    crystal_tokens: int
    compression_ratio: float
    task_profile: Dict[str, Any]
    created_at: datetime
    ttl_seconds: int = Field(default=86400, description="Time-to-live for the handle")
    warnings: List[str] = Field(default_factory=list)


class ContextRunRequest(BaseModel):
    """POST /v1/context/run request body."""
    context_handle: str = Field(..., description="Handle from /v1/compress")
    task: str = Field(..., description="Specific task to perform using the CCO working context package")
    max_tokens: int = Field(default=4000, ge=100, le=16000)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    retrieve_depth: int = Field(default=2, ge=1, le=5,
                                 description="For hierarchical/retrieval: how deep to fetch")
    include_provenance: bool = Field(default=True,
                                    description="Include source references in response")


class ContextRunResponse(BaseModel):
    """POST /v1/context/run response."""
    answer: str
    context_handle: str
    tokens_used: int
    strategy_used: CompressionStrategy
    retrieved_segments: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class OrchestrationMetadata(BaseModel):
    """Internal metadata for a stored CCO working context package."""
    handle: str
    strategy: CompressionStrategy
    original_tokens: int
    crystal_tokens: int
    task: str
    task_profile: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 86400
    source_hash: str
    crystal_data: Dict[str, Any]  # Compatibility field: the CCO working context package
    preserve_exact: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskProfile(BaseModel):
    """Extracted profile from task description."""
    intent: str
    entities: List[str] = Field(default_factory=list)
    information_needs: List[str] = Field(default_factory=list)
    priority_keywords: List[str] = Field(default_factory=list)
    temporal_constraints: List[str] = Field(default_factory=list)
    domain: Optional[str] = None


class CanaryTestRequest(BaseModel):
    """Request to run scope leakage detection."""
    context_handle: str
    test_queries: List[str]
    ground_truth_source: Optional[str] = None
    expected_facts: Optional[List[Dict[str, str]]] = None


class CanaryTestResult(BaseModel):
    """Result of a single canary test."""
    query: str
    crystal_answer: str
    raw_answer: Optional[str] = None
    fact_preservation_score: float  # 0.0 - 1.0
    scope_leakage_detected: bool
    hallucination_risk: float
    details: Dict[str, Any]


class CanaryTestResponse(BaseModel):
    """Full canary test report."""
    context_handle: str
    overall_score: float
    strategy_used: CompressionStrategy
    results: List[CanaryTestResult]
    recommendations: List[str]
    timestamp: datetime
