#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx


def run_once(client: httpx.Client, base_url: str, lane: str, prompt: str, max_tokens: int) -> Dict[str, Any]:
    started = time.perf_counter()
    response = client.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        headers={"X-ORB-Lane": lane},
        json={
            "model": "orb-auto",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "stream": False,
        },
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.raise_for_status()
    payload = response.json()
    runtime = payload.get("orb_runtime") or {}
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "lane": lane,
        "provider": runtime.get("provider"),
        "model": payload.get("model"),
        "round_trip_ms": elapsed_ms,
        "provider_latency_ms": runtime.get("latency_ms"),
        "output": str(message.get("content") or "")[:500],
        "usage": payload.get("usage") or {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark every healthy ORB inference lane.")
    parser.add_argument("--base-url", default="http://127.0.0.1:16520")
    parser.add_argument("--prompt", default="In one sentence, state that the ORB runtime is operational.")
    parser.add_argument("--lanes", default="universal,scale,accelerated,fallback")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=48)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    lanes = [lane.strip() for lane in args.lanes.split(",") if lane.strip()]
    records: List[Dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout) as client:
        for lane in lanes:
            for run in range(1, args.runs + 1):
                try:
                    record = run_once(client, args.base_url, lane, args.prompt, args.max_tokens)
                    record["run"] = run
                except Exception as exc:
                    record = {"lane": lane, "run": run, "error": str(exc)}
                records.append(record)
                print(json.dumps(record, ensure_ascii=False))

    summaries = []
    for lane in lanes:
        timings = [r["round_trip_ms"] for r in records if r.get("lane") == lane and "round_trip_ms" in r]
        summaries.append(
            {
                "lane": lane,
                "successful_runs": len(timings),
                "median_round_trip_ms": round(statistics.median(timings), 2) if timings else None,
                "best_round_trip_ms": min(timings) if timings else None,
            }
        )
    report = {
        "generated_at_epoch": time.time(),
        "base_url": args.base_url,
        "summaries": summaries,
        "records": records,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    return 0 if any("round_trip_ms" in record for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
