from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from .articulation import articulate
from .catalog_repository import CatalogRepository
from .provider_router import invoke_provider


LocalModel = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any] | str]]
PosterioriLookup = Callable[[str, str, str], Optional[Dict[str, Any]]]
VaultSKGLookup = Callable[[str, str], Optional[Dict[str, Any]]]
ProviderInvoke = Callable[..., Awaitable[Dict[str, Any]]]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9][a-z0-9_-]+", (value or "").lower()) if len(token) > 2}


def _score(query: str, candidates: list[str]) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    scores = []
    for candidate in candidates:
        candidate_tokens = _tokens(candidate)
        if candidate_tokens:
            scores.append(len(query_tokens & candidate_tokens) / max(1, min(len(query_tokens), len(candidate_tokens))))
    return max(scores, default=0.0)


def _answer_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class CanonicalTurnResolver:
    def __init__(
        self,
        *,
        local_model: Optional[LocalModel] = None,
        posteriori_lookup: Optional[PosterioriLookup] = None,
        vault_skg_lookup: Optional[VaultSKGLookup] = None,
        provider_invoke: ProviderInvoke = invoke_provider,
    ):
        self.local_model = local_model
        self.posteriori_lookup = posteriori_lookup
        self.vault_skg_lookup = vault_skg_lookup
        self.provider_invoke = provider_invoke

    async def resolve(
        self,
        transcript: str,
        *,
        domain: str,
        route: str = "/",
        catalog_path: Optional[Path | str] = None,
        apriori: Optional[Dict[str, Any]] = None,
        site_world: Optional[Dict[str, Any]] = None,
        page_capsule: Optional[Dict[str, Any]] = None,
        pointer_matches: Optional[list[Dict[str, Any]]] = None,
        provider_configuration: Optional[Dict[str, Any]] = None,
        articulation_profile: Optional[Dict[str, Any]] = None,
        model_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        query = re.sub(r"\s+", " ", transcript).strip()
        attempts: list[Dict[str, Any]] = []
        semantic: Optional[Dict[str, Any]] = self._control(query)
        attempts.append({"lane": "control", "matched": bool(semantic)})

        if semantic is None and catalog_path:
            semantic = self._catalog(query, CatalogRepository(catalog_path))
            attempts.append({"lane": "catalog", "matched": bool(semantic)})
        if semantic is None:
            semantic = self._apriori(query, apriori or {})
            attempts.append({"lane": "apriori", "matched": bool(semantic)})
        if semantic is None and self.vault_skg_lookup:
            match = self.vault_skg_lookup("apriori", query)
            if match:
                semantic = self._semantic(
                    answer=str(match["answer"]), source_lane="apriori", answer_state="known",
                    evidence_ids=[str(item) for item in match.get("evidence_ids") or []],
                    confidence=float(match.get("confidence") or 0.0),
                )
                semantic["vault_skg_trace"] = match
            attempts.append({"lane": "apriori_skg", "matched": bool(semantic)})
        if semantic is None and self.posteriori_lookup and domain:
            case = self.posteriori_lookup(domain, query, route)
            if case and case.get("spoken_output"):
                semantic = self._semantic(
                    answer=str(case["spoken_output"]), source_lane="posteriori", answer_state="resolved",
                    evidence_ids=[str(item) for item in case.get("evidence_refs") or [case.get("case_id") or "verified_case"]],
                    confidence=float(case.get("cache_score") or 1.0),
                )
            attempts.append({"lane": "posteriori", "matched": bool(semantic)})
        if semantic is None and self.vault_skg_lookup:
            match = self.vault_skg_lookup("posteriori", query)
            if match:
                semantic = self._semantic(
                    answer=str(match["answer"]), source_lane="posteriori", answer_state="resolved",
                    evidence_ids=[str(item) for item in match.get("evidence_ids") or []],
                    confidence=float(match.get("confidence") or 0.0),
                )
                semantic["vault_skg_trace"] = match
            attempts.append({"lane": "posteriori_skg", "matched": bool(semantic)})
        if semantic is None:
            semantic = self._site_world(query, site_world or {}, route)
            attempts.append({"lane": "site_world", "matched": bool(semantic)})

        local_failure = None
        if semantic is None and self.local_model:
            try:
                local_result = await self.local_model(query, {
                    "site_world": site_world or {}, "page_capsule": page_capsule or {}, "route": route, **(model_context or {})
                })
                if isinstance(local_result, str):
                    local_result = {"text": local_result, "source": "local_model"}
                text = str(local_result.get("text") or local_result.get("spoken_output") or "").strip()
                if text and not local_result.get("failed"):
                    semantic = self._semantic(answer=text, source_lane="local_model", answer_state="unknown", evidence_ids=[], confidence=0.55)
                    semantic["escalation_used"] = "local_model"
                else:
                    local_failure = str(local_result.get("error") or "local_model_empty")
            except Exception as exc:
                local_failure = f"local_model_failed:{str(exc)[:240]}"
            attempts.append({"lane": "local_model", "matched": bool(semantic), "error": local_failure})

        provider_result = None
        configuration = dict(provider_configuration or {})
        if semantic is None and configuration.get("provider") not in (None, "", "runtime_default", "ollama_local"):
            provider_result = await self.provider_invoke(
                configuration,
                prompt=self._provider_prompt(query, site_world or {}, page_capsule or {}),
                system_instruction="You are the Website ORB articulation provider. Use only supplied site context, preserve uncertainty, and return concise speech.",
            )
            if provider_result.get("success") and provider_result.get("text"):
                semantic = self._semantic(
                    answer=str(provider_result["text"]), source_lane="external_provider", answer_state="unknown", evidence_ids=[], confidence=0.5
                )
                semantic["escalation_used"] = provider_result.get("provider")
            attempts.append({"lane": "external_provider", "matched": bool(semantic), "error": provider_result.get("error")})

        if semantic is None:
            semantic = self._semantic(
                answer="I do not have enough verified site information to answer that yet.",
                source_lane="unknown",
                answer_state="unknown",
                evidence_ids=[],
                confidence=0.0,
            )
            semantic["learning_eligible"] = True

        semantic["route_context"] = {"domain": domain, "route": route}
        semantic["guidance"] = (pointer_matches or [None])[0]
        articulation = articulate(semantic, articulation_profile)
        return {
            **semantic,
            "spoken_output": articulation["spoken_text"],
            "trace": {
                "schema": "orb_weaver.canonical_turn_trace.v1",
                "resolution_order": ["control", "catalog", "apriori", "posteriori", "site_world", "local_model", "external_provider", "articulation"],
                "attempts": attempts,
                "factual_source": {"lane": semantic["source_lane"], "evidence_ids": semantic["evidence_ids"]},
                "semantic_resolution": {"answer_state": semantic["answer_state"], "confidence": semantic["confidence"]},
                "articulation": articulation["trace"],
                "provider": provider_result,
            },
        }

    @staticmethod
    def _semantic(*, answer: str, source_lane: str, answer_state: str, evidence_ids: list[str], confidence: float) -> Dict[str, Any]:
        return {
            "answer": answer,
            "answer_hash": _answer_hash(answer),
            "answer_state": answer_state,
            "source_lane": source_lane,
            "source": source_lane,
            "evidence_ids": evidence_ids,
            "confidence": round(confidence, 3),
            "verification_state": "verified" if source_lane in {"control", "catalog", "apriori", "posteriori", "site_world"} else "not_verified",
            "escalation_used": None,
            "learning_eligible": source_lane not in {"control", "catalog", "apriori", "posteriori", "site_world"},
        }

    def _control(self, query: str) -> Optional[Dict[str, Any]]:
        normalized = re.sub(r"^(?:hey\s+)?weaver[\s,:-]+", "", query.lower()).strip()
        motion_commands = (
            ("move_out_of_way", ("move out of the way", "get out of the way"), "Oh, excuse me."),
            ("move_to_side", ("move over", "scoot over", "move to the side", "go over there"), "Of course."),
            ("move_up", ("move up",), "Moving up."),
            ("move_down", ("move down",), "Moving down."),
            ("move_left", ("move left",), "Moving left."),
            ("move_right", ("move right",), "Moving right."),
            ("come_back", ("come back",), "Coming back."),
            ("come_here", ("come here",), "Coming closer."),
            ("hold_position", ("stay there", "stop moving", "wait there"), "I'll stay here."),
            ("wake", ("wake up",), "I'm awake."),
            ("listen", ("go back to listening",), "I'm listening."),
        )
        for command, phrases, answer in motion_commands:
            if normalized.rstrip(".!?") in phrases:
                semantic = self._semantic(
                    answer=answer,
                    source_lane="control",
                    answer_state="known",
                    evidence_ids=[f"control:{command}"],
                    confidence=1.0,
                )
                semantic["control_action"] = {"type": "orb_motion", "command": command}
                return semantic
        if any(re.search(rf"\b{re.escape(phrase)}\b", normalized) for phrase in ("who are you", "what are you", "what do you do", "your purpose")):
            return self._semantic(
                answer="I'm Weaver, this website's ORB host. I use verified site knowledge to answer and guide visitors.",
                source_lane="control", answer_state="known", evidence_ids=["control:website_orb_identity"], confidence=1.0,
            )
        if normalized in {"stop", "cancel", "be quiet", "stop speaking"}:
            return self._semantic(
                answer="Stopped.", source_lane="control", answer_state="known", evidence_ids=["control:stop"], confidence=1.0
            )
        return None

    def _catalog(self, query: str, repository: CatalogRepository) -> Optional[Dict[str, Any]]:
        match = repository.lookup(query)
        if not match:
            return None
        record = match.record
        price = record.get("price") or {}
        current_amount = price.get("sale_amount") if price.get("sale_amount") is not None else price.get("amount")
        display = price.get("display_text")
        if price.get("sale_amount") is not None:
            display = f"{price.get('currency') or ''} {price['sale_amount']:.2f}".strip()
        availability = record.get("availability")
        details = [record["name"]]
        if current_amount is not None or display:
            details.append(f"is {display or current_amount}")
        if availability not in (None, "null", True):
            details.append(f"and availability is {availability}")
        answer = " ".join(details).strip() + "."
        return self._semantic(
            answer=answer, source_lane="catalog", answer_state="known",
            evidence_ids=[str(item) for item in record.get("source_evidence_ids") or []], confidence=match.score,
        )

    def _apriori(self, query: str, apriori: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best = None
        for entry in (apriori.get("qa") or {}).get("entries") or []:
            score = _score(query, [entry.get("question", ""), *(entry.get("aliases") or [])])
            if score >= 0.62 and (best is None or score > best[0]):
                best = (score, entry.get("answer"), entry.get("source_evidence_ids") or [])
        for rule in (apriori.get("policies") or {}).get("rules") or []:
            score = _score(query, [rule.get("title", ""), rule.get("category", "")])
            if score >= 0.7 and (best is None or score > best[0]):
                best = (score, rule.get("text"), rule.get("source_evidence_ids") or [])
        if not best or not best[1]:
            return None
        return self._semantic(
            answer=str(best[1]), source_lane="apriori", answer_state="known",
            evidence_ids=[str(item) for item in best[2]], confidence=float(best[0]),
        )

    def _site_world(self, query: str, site_world: Dict[str, Any], route: str) -> Optional[Dict[str, Any]]:
        best = None
        normalized_query = " ".join(query.lower().split())
        site_name = str(site_world.get("site_name") or site_world.get("brand") or "").strip()
        site_summary = str(site_world.get("site_summary") or "").strip()
        if site_name and site_summary:
            normalized_name = " ".join(site_name.lower().split())
            identity_question = normalized_name in normalized_query and any(
                phrase in normalized_query for phrase in ("what does", "what is", "tell me about", "explain")
            )
            if identity_question:
                best = (0.9, site_summary, ["site_world:site_summary"])
        for index, fact in enumerate(site_world.get("key_facts") or []):
            fact_text = str(fact).strip()
            score = _score(query, [fact_text])
            if fact_text and score >= 0.55 and (best is None or score > best[0]):
                best = (score, fact_text, [f"site_world:key_fact:{index}"])
        for label, destination in (site_world.get("route_hints") or {}).items():
            score = _score(query, [str(label), str(destination)])
            if score >= 0.62 and (best is None or score > best[0]):
                best = (score, f"You'll find {label} at {destination}.", [f"route:{destination}"])
        chunks = (site_world.get("knowledge_chunks") or {}).get("chunks") or []
        for chunk in chunks:
            if chunk.get("route") not in (None, "", route):
                continue
            score = _score(query, [str(chunk.get("title") or ""), str(chunk.get("heading") or ""), str(chunk.get("text") or "")])
            if score >= 0.68 and (best is None or score > best[0]):
                best = (score, str(chunk.get("text") or "")[:900], [str(chunk.get("chunk_id") or chunk.get("content_hash") or "site_world")])
        if not best:
            return None
        return self._semantic(answer=best[1], source_lane="site_world", answer_state="known", evidence_ids=best[2], confidence=best[0])

    @staticmethod
    def _provider_prompt(query: str, site_world: Dict[str, Any], page_capsule: Dict[str, Any]) -> str:
        return f"Visitor question: {query}\nSite context: {site_world}\nCurrent page: {page_capsule}"
