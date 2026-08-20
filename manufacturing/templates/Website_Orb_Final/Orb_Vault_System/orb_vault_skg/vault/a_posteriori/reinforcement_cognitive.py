"""
orb/vault/a_posteriori/reinforcement_cognitive.py
Cognitive state for reinforcement tracking.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from ..shared.types import KnowledgeNode


@dataclass
class ReinforcementCognitiveState:
    """
    Tracks reinforcement history and usage patterns.
    """

    # Usage history: node_id -> [(timestamp, success, query)]
    usage_history: Dict[str, List[tuple]] = field(default_factory=lambda: defaultdict(list))

    # Resolution time tracking: node_id -> [times_ms]
    resolution_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    # Daily access counts for trend analysis
    daily_access_counts: Dict[str, int] = field(default_factory=dict)

    def record_usage(self, node_id: str, success: bool, query: str = "", resolution_time_ms: float = 0.0):
        """Record a usage event."""
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        self.usage_history[node_id].append((timestamp, success, query))
        if resolution_time_ms > 0:
            self.resolution_times[node_id].append(resolution_time_ms)

        # Daily count
        day_key = timestamp[:10]
        self.daily_access_counts[day_key] = self.daily_access_counts.get(day_key, 0) + 1

    def get_average_resolution_time(self, node_id: str) -> float:
        """Get average resolution time for a node."""
        times = self.resolution_times.get(node_id, [])
        if not times:
            return 0.0
        return sum(times) / len(times)

    def get_success_rate(self, node_id: str, lookback: int = 20) -> float:
        """Calculate recent success rate."""
        history = self.usage_history.get(node_id, [])
        if not history:
            return 0.0
        recent = history[-lookback:]
        successes = sum(1 for _, success, _ in recent if success)
        return successes / len(recent)

    def get_usage_trend(self, days: int = 7) -> str:
        """Analyze recent usage trend."""
        from datetime import datetime, timedelta
        counts = []
        for i in range(days):
            day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            counts.append(self.daily_access_counts.get(day, 0))

        if not counts or sum(counts) == 0:
            return "flat"

        # Simple trend: compare first half to second half
        mid = len(counts) // 2
        first_half = sum(counts[:mid]) / max(mid, 1)
        second_half = sum(counts[mid:]) / max(len(counts) - mid, 1)

        if second_half > first_half * 1.2:
            return "rising"
        elif second_half < first_half * 0.8:
            return "falling"
        return "stable"
