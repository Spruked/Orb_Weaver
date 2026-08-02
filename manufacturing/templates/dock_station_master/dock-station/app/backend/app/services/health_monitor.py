"""Health monitoring — gateway, pointer, voice, model lanes"""
import random
from typing import Dict, Any
from datetime import datetime
from app.models import HealthStatus, PointerStatus

class HealthMonitor:
    def __init__(self):
        self.pointer_targets = self._seed_pointer_targets()
        self.gateway_lanes = self._seed_gateway_lanes()
        self.voice_provider = {"healthy": True, "last_error": None, "fallback_active": False}

    def _seed_pointer_targets(self) -> list:
        return [
            {"id": "hero-cta", "selector": "#hero .cta-button", "status": PointerStatus.VERIFIED, "confidence": 0.98},
            {"id": "pricing-card", "selector": "#pricing .card", "status": PointerStatus.VERIFIED, "confidence": 0.95},
            {"id": "nav-contact", "selector": "nav a[href='/contact']", "status": PointerStatus.VERIFIED, "confidence": 0.92},
            {"id": "footer-signup", "selector": "footer .signup", "status": PointerStatus.RECOVERED, "confidence": 0.78},
            {"id": "feature-grid", "selector": "#features .grid", "status": PointerStatus.NEW, "confidence": 0.65},
            {"id": "old-banner", "selector": "#banner-v1", "status": PointerStatus.DEPRECATED, "confidence": 0.30},
        ]

    def _seed_gateway_lanes(self) -> list:
        return [
            {"name": "universal", "provider": "llama.cpp", "healthy": True, "latency_ms": 120, "queue_depth": 2},
            {"name": "scale", "provider": "Aphrodite", "healthy": True, "latency_ms": 85, "queue_depth": 0},
            {"name": "accelerated", "provider": "TensorRT-LLM", "healthy": False, "latency_ms": None, "queue_depth": None, "error": "Service unreachable"},
            {"name": "fallback", "provider": "Ollama", "healthy": True, "latency_ms": 340, "queue_depth": 1},
        ]

    def get_overall_health(self) -> Dict[str, Any]:
        pointer_confidence = sum(t["confidence"] for t in self.pointer_targets) / len(self.pointer_targets)
        model_healthy = any(l["healthy"] for l in self.gateway_lanes)
        voice_healthy = self.voice_provider["healthy"]

        overall = HealthStatus.HEALTHY
        if not model_healthy or not voice_healthy:
            overall = HealthStatus.UNHEALTHY
        elif pointer_confidence < 0.8:
            overall = HealthStatus.DEGRADED

        return {
            "pointer_confidence": round(pointer_confidence, 2),
            "model_reachability": HealthStatus.HEALTHY if model_healthy else HealthStatus.UNHEALTHY,
            "voice_reachability": HealthStatus.HEALTHY if voice_healthy else HealthStatus.DEGRADED,
            "overall": overall,
            "checks": {
                "pointer_verified": len([t for t in self.pointer_targets if t["status"] == PointerStatus.VERIFIED]),
                "pointer_total": len(self.pointer_targets),
                "gateway_lanes_up": len([l for l in self.gateway_lanes if l["healthy"]]),
                "gateway_lanes_total": len(self.gateway_lanes),
                "voice_fallback_active": self.voice_provider["fallback_active"],
            }
        }

    def get_pointer_report(self) -> Dict[str, Any]:
        return {
            "targets": self.pointer_targets,
            "verified_count": len([t for t in self.pointer_targets if t["status"] == PointerStatus.VERIFIED]),
            "needs_recovery": [t for t in self.pointer_targets if t["status"] in (PointerStatus.NEW, PointerStatus.RECOVERED)],
            "deprecated_count": len([t for t in self.pointer_targets if t["status"] == PointerStatus.DEPRECATED]),
        }

    def get_gateway_report(self) -> Dict[str, Any]:
        return {
            "lanes": self.gateway_lanes,
            "active_lane": "scale",
            "routing_status": "load_balanced",
        }

    def run_pointer_recovery(self) -> Dict[str, Any]:
        recovered = []
        for t in self.pointer_targets:
            if t["status"] in (PointerStatus.NEW, PointerStatus.RECOVERED):
                t["status"] = PointerStatus.RECOVERED
                t["confidence"] = min(0.9, t["confidence"] + random.uniform(0.1, 0.25))
                recovered.append(t["id"])
        return {"recovered": recovered, "timestamp": datetime.utcnow().isoformat()}

    def get_diagnostics(self) -> list:
        issues = []

        # Pointer issues
        degraded = [t for t in self.pointer_targets if t["confidence"] < 0.8]
        if degraded:
            issues.append({
                "id": "pointer-degraded",
                "category": "pointer",
                "severity": "warning",
                "message": f"{len(degraded)} pointer target(s) below confidence threshold.",
                "remediation": "Run pointer recovery pass or review changed page targets.",
                "auto_resolvable": True,
            })

        # Gateway issues
        down_lanes = [l for l in self.gateway_lanes if not l["healthy"]]
        for lane in down_lanes:
            issues.append({
                "id": f"gateway-{lane['name']}-down",
                "category": "gateway",
                "severity": "warning" if lane["name"] != "universal" else "critical",
                "message": f"Lane '{lane['name']}' ({lane['provider']}) is unreachable.",
                "remediation": "Check endpoint or failover to next priority lane.",
                "auto_resolvable": lane["name"] != "universal",
            })

        # Voice issues
        if not self.voice_provider["healthy"]:
            issues.append({
                "id": "voice-provider-failing",
                "category": "voice",
                "severity": "critical",
                "message": "Voice provider failing last 3 requests.",
                "remediation": "Switch to local fallback voice temporarily.",
                "auto_resolvable": True,
            })

        return issues

health_monitor = HealthMonitor()
