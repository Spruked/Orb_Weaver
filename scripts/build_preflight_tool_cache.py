#!/usr/bin/env python3
"""
Build a zero-latency ORB voice tool cache from static intents, fallback language,
and the currently exposed MCP tool catalog.

The generated JSON is meant for the scan/build phase. Runtime can resolve:
intent_keyword -> entry -> WAV/audio asset, and only call MCP on cache misses.

Product boundary:
- default build is "basic" and never probes the MCP relay
- enhanced/showcase builds require ORB_BUILD_ALLOW_MCP=true or --allow-mcp
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ALLOW_MCP_ENV = "ORB_BUILD_ALLOW_MCP"
DEFAULT_DOMAIN = "orbweaver.spruked.com"


COMMON_INTENTS = [
    ("hero_overview", ["what is this site", "what do you do", "tell me about this", "hero"]),
    ("pricing_overview", ["pricing", "how much does it cost", "plans", "tiers"]),
    ("basic_plan", ["basic plan", "starter plan", "basic orb", "entry tier"]),
    ("premium_plan", ["premium plan", "premium orb", "advanced tier", "browser verification"]),
    ("enterprise_plan", ["enterprise", "custom plan", "large business", "full tools"]),
    ("cart_status", ["cart", "what is in my cart", "checkout cart", "cart total"]),
    ("checkout_help", ["checkout", "buy now", "complete purchase", "payment"]),
    ("contact_options", ["contact", "call you", "email", "support"]),
    ("booking_help", ["book", "schedule", "appointment", "calendar"]),
    ("faq_overview", ["faq", "questions", "help center", "common questions"]),
    ("shipping", ["shipping", "delivery", "ship date", "where is my order"]),
    ("returns", ["return", "refund", "exchange", "cancel order"]),
    ("login_help", ["login", "sign in", "account", "password"]),
    ("product_search", ["find product", "search product", "show me", "catalog"]),
    ("services", ["services", "what services", "work with you", "offerings"]),
    ("portfolio", ["portfolio", "examples", "case studies", "past work"]),
    ("reviews", ["reviews", "testimonials", "ratings", "proof"]),
    ("location", ["where are you", "location", "address", "near me"]),
    ("hours", ["hours", "open", "closed", "when are you available"]),
    ("team", ["team", "who works here", "about you", "founder"]),
    ("privacy", ["privacy", "data", "cookies", "terms"]),
    ("accessibility", ["accessibility", "screen reader", "accessible", "ada"]),
    ("preflight_status", ["scan result", "preflight", "is the site ready", "readiness"]),
    ("tool_status", ["tools", "mcp", "tesseract", "can you use tools"]),
    ("visual_audit", ["read the screen", "ocr", "visible text", "visual check"]),
    ("escalate_human", ["human", "representative", "agent", "talk to someone"]),
    ("fallback_checking", ["check that", "look that up", "one moment", "verify"]),
]

DEFAULT_RESPONSES = {
    "hero_overview": "This page explains the main offer and where to go next.",
    "pricing_overview": "I can help compare pricing and point you to the right plan.",
    "cart_status": "I can check the cart state when owner tools are enabled.",
    "contact_options": "I can guide you to the contact path or help prepare a support request.",
    "faq_overview": "I can answer common questions from the site's cached guide.",
    "preflight_status": "I can answer from the latest preflight cache instantly.",
    "tool_status": "I can use cached answers first, then MCP or OCR when a live check is needed.",
    "visual_audit": "I can compare visible OCR text with structured tool data.",
    "fallback_checking": "One moment, let me check that for you.",
}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _safe_pack_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())
    return cleaned.strip("._-") or "unknown_site"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None, token: str = "", timeout: float = 30) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _list_mcp_tools(relay_url: str, token: str) -> List[Dict[str, Any]]:
    if not relay_url:
        return []
    try:
        payload = _http_json("GET", f"{relay_url.rstrip('/')}/tools/list", token=token)
    except Exception:
        return []
    return (((payload or {}).get("result") or {}).get("tools") or [])


def _call_mcp_tool(relay_url: str, token: str, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return _http_json("POST", f"{relay_url.rstrip('/')}/tools/call", {"name": name, "arguments": args}, token=token)
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"error": str(exc)}


def _match_tool(intent_id: str, tool_names: List[str]) -> Optional[str]:
    aliases = {
        "cart": ["cart", "checkout"],
        "pricing": ["pricing", "price", "tier", "plan"],
        "contact": ["contact", "support", "ticket"],
        "faq": ["faq", "knowledge", "kb", "search"],
        "visual": ["ocr", "screenshot", "visual"],
        "preflight": ["scan", "preflight", "audit"],
    }
    haystack = intent_id.replace("_", " ")
    for key, terms in aliases.items():
        if key in haystack or any(term in haystack for term in terms):
            for tool_name in tool_names:
                lowered = tool_name.lower()
                if any(term in lowered for term in terms):
                    return tool_name
    return None


def _fallback_phrases(fallback_path: Path) -> List[str]:
    payload = _read_json(fallback_path)
    groups = (payload.get("response_groups") or {})
    phrases = []
    for values in groups.values():
        if isinstance(values, list):
            phrases.extend(str(value) for value in values if value)
    return phrases


def _context_dir(args: argparse.Namespace) -> Path:
    return Path(args.substrate_root) / "clients" / _safe_pack_name(args.domain) / "website_orb_context"


def _output_path(args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output)
    return _context_dir(args) / "tool_cache.json"


def _load_pointer_map(args: argparse.Namespace) -> Dict[str, Any]:
    pointer_path = Path(args.pointer_map) if args.pointer_map else _context_dir(args) / "pointer_plot_map.json"
    payload = _read_json(pointer_path)
    return {
        "path": str(pointer_path),
        "available": bool(payload),
        "schema": payload.get("schema"),
        "record_count": int(payload.get("record_count") or 0),
    }


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _synthesize_tts(backend_url: str, text: str, token: str) -> Dict[str, Any]:
    if not backend_url:
        return {"tts_audio_url": None, "tts_provider": None, "tts_error": None}
    try:
        payload = _http_json("POST", f"{backend_url.rstrip('/')}/api/orb/tts", {"text": text}, token=token, timeout=90)
        return {
            "tts_audio_url": payload.get("tts_audio_url"),
            "tts_provider": payload.get("tts_provider"),
            "tts_error": payload.get("tts_error"),
        }
    except Exception as exc:
        return {"tts_audio_url": None, "tts_provider": None, "tts_error": str(exc)}


def build_cache(args: argparse.Namespace) -> Dict[str, Any]:
    fallback_phrases = _fallback_phrases(Path(args.fallback_responses))
    visual_targets = _load_pointer_map(args)
    allow_mcp = bool(args.allow_mcp or _env_flag(ALLOW_MCP_ENV))
    mcp_tools = _list_mcp_tools(args.mcp_relay_url, args.mcp_token) if allow_mcp else []
    tool_names = [str(tool.get("name")) for tool in mcp_tools if isinstance(tool, dict) and tool.get("name")]
    tool_params = _read_json(Path(args.tool_params_json)) if args.tool_params_json else {}
    mode = "enhanced" if allow_mcp and tool_names else "basic"
    if allow_mcp and not tool_names:
        print("MCP relay not found or returned no tools. Building BASIC cache only.", file=sys.stderr)

    entries = []
    for index, (intent_id, keywords) in enumerate(COMMON_INTENTS, start=1):
        response = DEFAULT_RESPONSES.get(intent_id)
        if not response:
            response = fallback_phrases[(index - 1) % len(fallback_phrases)] if fallback_phrases else "I can help with that."
        mcp_tool = _match_tool(intent_id, tool_names)
        mcp_result = None
        if allow_mcp and args.dry_run_tools and mcp_tool:
            mcp_result = _call_mcp_tool(args.mcp_relay_url, args.mcp_token, mcp_tool, dict(tool_params.get(mcp_tool) or {}))
        tts_result = _synthesize_tts(args.backend_url, response, args.backend_token) if args.synthesize_tts else {}
        entries.append(
            {
                "id": intent_id,
                "rank": index,
                "keywords": keywords,
                "resolution": "wav" if args.synthesize_tts else "text",
                "spoken_output": response,
                "wav_filename": f"{index:02d}_{_slug(intent_id)}.wav",
                "tts_audio_url": tts_result.get("tts_audio_url"),
                "tts_provider": tts_result.get("tts_provider"),
                "mcp_tool": mcp_tool,
                "mcp_prefetch": mcp_result,
            }
        )

    now = datetime.now(timezone.utc)
    return {
        "schema": "orb_weaver.tool_cache.v1",
        "mode": mode,
        "domain": args.domain,
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(days=args.ttl_days)).isoformat(),
        "runtime_rule": "intent_keyword -> play WAV; cache miss -> filler WAV -> async MCP call",
        "visual_targets": visual_targets,
        "product_boundary": {
            "basic_customer_cache_has_mcp_dependency": False,
            "mcp_allowed_for_this_build": allow_mcp,
            "mcp_data_included": bool(tool_names),
            "mcp_requires_explicit_build_flag": True,
            "statement": (
                "Basic customer Website ORB caches are static, website-native, and do not probe MCP. "
                "Enhanced MCP data is only included for the Orb Weaver showcase or deliberately configured advanced adapters."
            ),
        },
        "mcp": {
            "relay_url": args.mcp_relay_url if allow_mcp else None,
            "tool_count": len(tool_names),
            "tools": tool_names,
        },
        "entries": entries[: args.limit],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ORB pre-flight tool_cache.json for low-latency voice guidance.")
    parser.add_argument("--fallback-responses", default="frontend/public/orb/voice/fallback_responses.json")
    parser.add_argument("--domain", default=os.getenv("ORB_CACHE_DOMAIN", DEFAULT_DOMAIN))
    parser.add_argument("--substrate-root", default=os.getenv("ORB_WEAVER_SUBSTRATE_ROOT", "substrate"))
    parser.add_argument("--pointer-map", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--ttl-days", type=int, default=14)
    parser.add_argument("--mcp-relay-url", default=os.getenv("ORB_DESKTOP_MCP_URL", "http://127.0.0.1:8765"))
    parser.add_argument("--mcp-token", default=os.getenv("ORB_DESKTOP_MCP_TOKEN", ""))
    parser.add_argument("--backend-url", default=os.getenv("ORB_BACKEND_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--backend-token", default=os.getenv("ORB_BACKEND_TOKEN", ""))
    parser.add_argument("--tool-params-json", default="")
    parser.add_argument("--allow-mcp", action="store_true", help=f"Allow enhanced/showcase MCP discovery. Also enabled by {ALLOW_MCP_ENV}=true.")
    parser.add_argument("--dry-run-tools", action="store_true")
    parser.add_argument("--synthesize-tts", action="store_true")
    args = parser.parse_args()

    payload = build_cache(args)
    output = _output_path(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"output": str(output), "mode": payload["mode"], "entries": len(payload["entries"]), "mcp_tools": payload["mcp"]["tool_count"]}, indent=2))


if __name__ == "__main__":
    main()
