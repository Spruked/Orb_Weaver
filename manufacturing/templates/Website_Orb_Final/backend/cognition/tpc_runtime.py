from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from .hlsf_geometry import hlsf_singleton


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDOR_TPC_ROOT = PROJECT_ROOT / "vendor" / "TPC_Triple_Predicate_Cubed"


class TPCWebsiteRuntime:
    """TPC-only cognition runtime for the compiled Website ORB."""

    def __init__(self) -> None:
        self.hlsf = hlsf_singleton
        self._native_hlsf = None
        self._native_glyph_class = None
        self._hlsf_source = "backend/cognition/hlsf_geometry"
        self._egf = None
        self._egf_error = ""
        self._load_native_hlsf()
        self._load_egf()

    def evaluate(
        self,
        message: str,
        intent: str,
        route_record: Dict[str, Any],
        runtime_language: Dict[str, Any],
        pointer_targets: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        stimulus = {
            "message": message,
            "intent": intent,
            "route": route_record.get("route") or route_record.get("path") or "/",
            "page_purpose": route_record.get("page_purpose") or "",
            "summary": route_record.get("summary") or runtime_language.get("site_summary", ""),
            "pointer_target_count": len(pointer_targets or []),
            "intensity": self._estimate_intensity(message, pointer_targets or []),
            "velocity": min(len(message) / 160.0, 2.0),
        }

        hlsf_state, thought_vector = self._run_hlsf(stimulus)

        egf_state = self._run_egf(thought_vector)
        output_classes = route_record.get("tpc_output_classes") or {}
        precleared = output_classes.get("precleared") or ["answer", "point_if_resolved"]
        escalation = output_classes.get("requires_escalation") or ["site_modification", "desktop_tool"]
        summary = route_record.get("summary") or runtime_language.get("site_summary", "")

        return {
            "locke": {"basis": "route_facts", "verdict": summary},
            "hume": {"basis": "visitor_intent", "verdict": intent},
            "kant": {"basis": "action_class", "verdict": "answer" if "answer" in precleared else "voice_only"},
            "spinoza": {"basis": "site_world", "verdict": route_record.get("page_purpose", "site guidance")},
            "fifth_mind": {
                "candidate_action_class": "answer",
                "precleared": precleared,
                "requires_escalation": escalation,
            },
            "hlsf": hlsf_state,
            "egf": egf_state,
            "source": "tpc_website_runtime",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "cognitive_system": "TPC",
            "active_runtime": "tpc_website_runtime",
            "vendor_tpc_present": VENDOR_TPC_ROOT.exists(),
            "hlsf": {
                "present": True,
                "source": self._hlsf_source,
                "field_density": self._hlsf_density(),
                "dimension": 18,
            },
            "egf": {
                "present": (Path(__file__).parent / "Epistemic_Gravity_Field" / "space_field.py").exists(),
                "loaded": self._egf is not None,
                "error": self._egf_error,
            },
        }

    def _load_native_hlsf(self) -> None:
        if not VENDOR_TPC_ROOT.exists():
            return
        try:
            module_path = VENDOR_TPC_ROOT / "core" / "geometric_primitives.py"
            spec = importlib.util.spec_from_file_location("website_orb_tpc_geometric_primitives", module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Unable to load TPC HLSF from {module_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            self._native_glyph_class = module.GlyphSignature
            self._native_hlsf = module.SpaceField()
            self._hlsf_source = "vendor/TPC_Triple_Predicate_Cubed/core/geometric_primitives.py"
        except Exception:
            self._native_glyph_class = None
            self._native_hlsf = None
            self._hlsf_source = "backend/cognition/hlsf_geometry"

    def _run_hlsf(self, stimulus: Dict[str, Any]) -> tuple[Dict[str, Any], tuple[float, ...]]:
        if self._native_hlsf is not None and self._native_glyph_class is not None:
            vector = self._stimulus_vector(stimulus)
            glyph = self._native_glyph_class.from_stimulus(vector, origin="website_orb")
            self._native_hlsf.insert(glyph)
            neighbors = self._native_hlsf.traverse(glyph, top_k=5)
            thought_vector = tuple(float(v) for v in glyph.coordinates)
            return (
                {
                    "source": self._hlsf_source,
                    "node": {
                        "certainty": round(float(glyph.certainty), 6),
                        "vivacity": round(float(glyph.vivacity), 6),
                        "neighbor_count": len(neighbors),
                    },
                    "pulse": {
                        "field_density": len(self._native_hlsf.nodes),
                        "edge_cutter_active": bool(self._native_hlsf.edge_cutter_active),
                    },
                    "thought_vector_head": [round(v, 6) for v in thought_vector[:6]],
                },
                thought_vector,
            )

        node = self.hlsf.map_adjacency(stimulus)
        neighbors = self.hlsf.get_recursive_neighbors(node)
        thought_vector = self.hlsf.calculate_thought_vector([node, *neighbors])
        return (
            {
                "source": self._hlsf_source,
                "node": {
                    "n": node.n,
                    "k": node.k,
                    "cognitive_load": round(node.cognitive_load, 6),
                    "neighbor_count": len(neighbors),
                },
                "pulse": self.hlsf.pulse(),
                "thought_vector_head": [round(v, 6) for v in thought_vector[:6]],
            },
            thought_vector,
        )

    def _hlsf_density(self) -> int:
        if self._native_hlsf is not None:
            return len(self._native_hlsf.nodes)
        return len(self.hlsf.field_map)

    @classmethod
    def _stimulus_vector(cls, stimulus: Dict[str, Any]) -> np.ndarray:
        seed = repr(cls._to_plain(stimulus))
        values = []
        for index in range(18):
            digest = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()
            raw = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
            values.append((raw * 2.0) - 1.0)
        return np.asarray(values, dtype=float)

    def _load_egf(self) -> None:
        try:
            from .Epistemic_Gravity_Field import SpaceFieldCognition

            self._egf = SpaceFieldCognition(device="cpu")
        except Exception as exc:
            self._egf = None
            self._egf_error = f"{type(exc).__name__}: {exc}"

    def _run_egf(self, thought_vector: tuple[float, ...]) -> Dict[str, Any]:
        if self._egf is None:
            return {
                "available": False,
                "reason": self._egf_error or "not_loaded",
                "mode": "tpc_hlsf_only",
            }

        try:
            signal = self._build_egf_signal(thought_vector)
            self._egf.broadcast_to_field(signal)
            self._egf.step()
            stats = self._egf.get_field_stats()
            return {
                "available": True,
                "mode": "space_field_cognition",
                "stats": self._to_plain(stats),
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": f"{type(exc).__name__}: {exc}",
                "mode": "tpc_hlsf_only",
            }

    def _build_egf_signal(self, thought_vector: tuple[float, ...]):
        import torch

        dim = self._egf.config.DIM
        channels = self._egf.config.DIFFUSION_CHANNELS
        signal = torch.zeros(dim, dim, dim, channels, device=self._egf.device)
        center = dim // 2
        values = list(thought_vector[:channels])
        while len(values) < channels:
            values.append(0.0)
        signal[center, center, center, :] = torch.tensor(values[:channels], device=self._egf.device)
        return signal

    @staticmethod
    def _estimate_intensity(message: str, pointer_targets: List[Dict[str, Any]]) -> float:
        marker_hits = sum(1 for marker in ("?", "help", "where", "how", "buy", "contact") if marker in message.lower())
        return min(1.0, 0.25 + (len(pointer_targets) * 0.1) + (marker_hits * 0.15))

    @classmethod
    def _to_plain(cls, value: Any) -> Any:
        if is_dataclass(value):
            return cls._to_plain(asdict(value))
        if isinstance(value, dict):
            return {str(k): cls._to_plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._to_plain(v) for v in value]
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        return value


tpc_runtime = TPCWebsiteRuntime()
