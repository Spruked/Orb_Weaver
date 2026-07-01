#!/usr/bin/env python3
import sys
import json
from pathlib import Path

REPO_ROOT = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
)

print("READY: Caleon", flush=True)

for line in sys.stdin:
    try:
        msg = json.loads(line)
    except Exception:
        continue
    if msg.get("type") == "query":
        text = msg.get("text", "")
        result = {
            "type": "result",
            "data": {
                "text": f"Caleon echo: {text}",
                "confidence": 0.5,
                "reasoning_path": ["stub"],
            },
        }
        print(json.dumps(result), flush=True)
