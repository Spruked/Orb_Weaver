"""
ssi_fastapi.py
FastAPI router for ORB SSI operations.
Includes preflight endpoints and existing SSI query/install routes.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vault_system.paths import CLIENTS_ROOT, LOGS_ROOT, require_vault_path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Optional imports — compile-safe fallback
# ---------------------------------------------------------------------------
try:
    from preflight_site_scan import PreflightScanner
except ImportError:
    PreflightScanner = None  # type: ignore

try:
    from ssi_consumers import query_skg, query_morb, query_llm_pack
except ImportError:
    def query_skg(q: str, output_dir: str) -> Dict[str, Any]:
        return {"status": "stub", "query": q}

    def query_morb(q: str, output_dir: str) -> Dict[str, Any]:
        return {"status": "stub", "query": q}

    def query_llm_pack(q: str, output_dir: str) -> Dict[str, Any]:
        return {"status": "stub", "query": q}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("ssi_fastapi")
if not logger.handlers:
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    _handler = logging.FileHandler(LOGS_ROOT / "ssi_fastapi.log")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/orb", tags=["orb"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PreflightRunRequest(BaseModel):
    root_url: str
    output_dir: str


class QueryRequest(BaseModel):
    query: str
    output_dir: str


# ---------------------------------------------------------------------------
# Preflight endpoints
# ---------------------------------------------------------------------------

@router.get("/preflight/report", response_model=Dict[str, Any])
async def get_preflight_report() -> Dict[str, Any]:
    """
    Return the latest site_preflight_report.json if it exists.
    Returns {"status": "not_run"} if not found.
    """
    reports = sorted(
        CLIENTS_ROOT.glob("*/preflight/site_preflight_report.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for report_path in reports:
        if report_path.is_file():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.error("Failed to read preflight report from %s: %s", report_path, str(exc))
                raise HTTPException(status_code=500, detail="Failed to read preflight report.")
    return {"status": "not_run"}


@router.post("/preflight/run", response_model=Dict[str, Any])
async def run_preflight(request: PreflightRunRequest) -> Dict[str, Any]:
    """
    Trigger a PreflightScanner scan asynchronously.
    Returns the preflight report on completion.
    """
    if PreflightScanner is None:
        logger.error("PreflightScanner not available — preflight_site_scan.py missing.")
        raise HTTPException(
            status_code=503,
            detail="Preflight scanner module not available.",
        )

    root_url = request.root_url.strip()
    output_dir = str(require_vault_path(request.output_dir.strip(), "SSI preflight output"))

    if not root_url.startswith(("http://", "https://")):
        root_url = "https://" + root_url

    logger.info("FastAPI preflight run triggered for %s -> %s", root_url, output_dir)

    try:
        scanner = PreflightScanner(root_url=root_url, output_dir=output_dir)
        report = await scanner.scan()
        return report
    except Exception as exc:
        logger.error("Preflight run failed: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preflight scan failed: {exc}")


# ---------------------------------------------------------------------------
# Existing SSI query endpoints (stubs / passthrough)
# ---------------------------------------------------------------------------

@router.post("/query/skg")
async def query_skg_endpoint(request: QueryRequest) -> Dict[str, Any]:
    """Query the Cognitive SKG layer."""
    return query_skg(request.query, str(require_vault_path(request.output_dir, "SKG query output")))


@router.post("/query/morb")
async def query_morb_endpoint(request: QueryRequest) -> Dict[str, Any]:
    """Query the MORB Corpus layer."""
    return query_morb(request.query, str(require_vault_path(request.output_dir, "MORB query output")))


@router.post("/query/llm")
async def query_llm_endpoint(request: QueryRequest) -> Dict[str, Any]:
    """Query the LLM Context Pack layer."""
    return query_llm_pack(request.query, str(require_vault_path(request.output_dir, "LLM pack output")))


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
