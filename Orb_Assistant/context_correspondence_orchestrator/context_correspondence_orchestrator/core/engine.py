"""
Context & Correspondence Orchestrator - Core Engine
Orchestrates task analysis, context reduction, retrieval strategy selection,
and correspondence-ready evidence packaging.
"""

import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..models import (
    CompressRequest, CompressResponse, ContextRunRequest, ContextRunResponse,
    CompressionStrategy, OrchestrationMetadata, TaskProfile
)
from ..config import config
from ..core.llm_abstraction import get_llm, LLMInterface
from ..core.task_analyzer import TaskAnalyzer
from ..strategies import (
    SummaryStrategy, SemanticRetrievalStrategy,
    HierarchicalStrategy, VaultCompileStrategy
)


class ContextCorrespondenceOrchestrator:
    """
    Runtime conductor for CCO operations.
    Handles task analysis, working context packaging, storage, and querying.
    """

    def __init__(self, store, llm: Optional[LLMInterface] = None):
        self.store = store
        self.llm = llm or get_llm(config.LLM_PROVIDER)
        self.task_analyzer = TaskAnalyzer()

        # Strategy registry
        self.strategies = {
            CompressionStrategy.SUMMARY: SummaryStrategy(self.llm),
            CompressionStrategy.SEMANTIC_RETRIEVAL: SemanticRetrievalStrategy(self.llm),
            CompressionStrategy.HIERARCHICAL: HierarchicalStrategy(self.llm),
            CompressionStrategy.VAULT_COMPILE: VaultCompileStrategy(self.llm),
        }

    def compress(self, request: CompressRequest) -> CompressResponse:
        """Compile source material into a CCO working context package."""

        # Analyze task
        task_profile = self.task_analyzer.analyze(request.task)

        # Select strategy
        strategy = self._select_strategy(
            request.strategy, 
            request.source, 
            request.source_type,
            request.target_token_budget
        )

        # Execute compression
        strategy_impl = self.strategies[strategy]
        result = strategy_impl.compress(
            source=request.source,
            task_profile=task_profile,
            target_budget=request.target_token_budget,
            preserve_exact=request.preserve_exact or []
        )

        # Generate handle
        source_hash = hashlib.sha256(request.source.encode()).hexdigest()[:16]
        handle = f"ctx_{source_hash}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Store the working context package.
        metadata = OrchestrationMetadata(
            handle=handle,
            strategy=strategy,
            original_tokens=result["original_tokens"],
            crystal_tokens=result["crystal_tokens"],
            task=request.task,
            task_profile=task_profile.dict(),
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=0,
            ttl_seconds=config.DEFAULT_TTL_SECONDS,
            source_hash=source_hash,
            crystal_data=result,
            preserve_exact=request.preserve_exact or [],
            metadata=request.metadata or {}
        )

        self.store.save(metadata)

        # Calculate compression ratio
        ratio = result["original_tokens"] / max(result["crystal_tokens"], 1)

        # Warnings
        warnings = []
        if ratio < 2.0:
            warnings.append("Low compression ratio - source may already be compact")
        if result["crystal_tokens"] > request.target_token_budget * 1.2:
            warnings.append("CCO working context exceeds target budget - consider increasing budget")
        if strategy == CompressionStrategy.SUMMARY and result["original_tokens"] > 500000:
            warnings.append("Large source with summary strategy may lose obscure facts")

        return CompressResponse(
            context_handle=handle,
            strategy_used=strategy,
            original_tokens=result["original_tokens"],
            crystal_tokens=result["crystal_tokens"],
            compression_ratio=round(ratio, 1),
            task_profile=task_profile.dict(),
            created_at=metadata.created_at,
            ttl_seconds=config.DEFAULT_TTL_SECONDS,
            warnings=warnings
        )

    def run(self, request: ContextRunRequest) -> ContextRunResponse:
        """Run a task against a stored CCO working context package."""

        # Retrieve the working context package.
        metadata = self.store.get(request.context_handle)
        if not metadata:
            raise ValueError(f"Context handle not found: {request.context_handle}")

        # Update access stats
        metadata.last_accessed = datetime.utcnow()
        metadata.access_count += 1
        self.store.save(metadata)

        # Get strategy
        strategy = self.strategies[metadata.strategy]

        # Execute query
        result = strategy.query(
            crystal_data=metadata.crystal_data,
            task=request.task,
            max_tokens=request.max_tokens,
            retrieve_depth=request.retrieve_depth
        )

        # Build response
        response = ContextRunResponse(
            answer=result["answer"],
            context_handle=request.context_handle,
            tokens_used=result["tokens_used"],
            strategy_used=metadata.strategy,
            retrieved_segments=result.get("retrieved_segments", []),
            confidence=result.get("confidence", 0.5),
            provenance=result.get("provenance", []),
            warnings=[]
        )

        # Add warnings based on confidence
        if response.confidence < 0.5:
            response.warnings.append("Low confidence - answer may be unreliable")
        if metadata.strategy == CompressionStrategy.SUMMARY:
            response.warnings.append("Summary strategy may miss obscure facts")

        return response

    def _select_strategy(self, requested: CompressionStrategy, source: str,
                         source_type, target_budget: int) -> CompressionStrategy:
        """Auto-select or validate compression strategy."""

        if requested != CompressionStrategy.AUTO:
            return requested

        # Estimate source size
        words = len(source.split())
        tokens = int(words * 0.75)

        # Vault records always use vault compile
        if source_type.value == "vault_records":
            return CompressionStrategy.VAULT_COMPILE

        # Small source: summary is fine
        if tokens < 50000:
            return CompressionStrategy.SUMMARY

        # Medium source: semantic retrieval
        if tokens < 500000:
            return CompressionStrategy.SEMANTIC_RETRIEVAL

        # Large source: hierarchical
        return CompressionStrategy.HIERARCHICAL
