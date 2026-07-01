#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# --- WIRE AS NEEDED: Connect to Adaptive Cochlear Processor ---
REPO_ROOT = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
)
ACP_PATH = REPO_ROOT / "Adaptive_Cochlear_Processor_1.0"
if str(ACP_PATH) not in sys.path:
    sys.path.append(str(ACP_PATH))

try:
    from orchestrator import ACPHub

    hub = ACPHub()
    ACP_ACTIVE = True
except Exception as e:
    hub = None
    ACP_ACTIVE = False
    # Don't print here to avoid polluting stdout before READY

print("READY: CALI", flush=True)

for line in sys.stdin:
    try:
        msg = json.loads(line)
    except Exception:
        continue
    if msg.get("type") == "query":
        text = msg.get("text", "")

        response_text = f"CALI echo: {text}"
        audio_file = None

        if ACP_ACTIVE and hub:
            try:
                # Use Coqui/ACP to speak the response
                audio_file = hub.speak(response_text)
            except Exception as e:
                response_text += f" [Audio Error: {e}]"

        result = {
            "type": "result",
            "data": {
                "text": response_text,
                "audio": audio_file,
                "confidence": 0.5,
                "reasoning_path": [
                    "stub",
                    "acp_connected" if ACP_ACTIVE else "acp_offline",
                ],
            },
        }
        print(json.dumps(result), flush=True)
