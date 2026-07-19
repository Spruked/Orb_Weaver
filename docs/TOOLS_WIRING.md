# Tool Wiring

The repository's `tools/` directory contains executable operator and runtime support entry points. These tools do not own persistent data; generated state and logs must go through `vault_system/`.

| Tool | Role | Wiring |
| --- | --- | --- |
| `check_weaver_runtime.sh` | Read-only runtime readiness check | Probes the local Orb Weaver backend, Ollama, Linux Tesseract, Windows Tesseract, and an optional OCR fixture. |
| `kokoro_openai_tts_server.py` | Local Kokoro speech service | Called through `ORB_TTS_KOKORO_URL`; supports `/speak` and `/v1/audio/speech`. |
| `start_kokoro_tts.sh` | Kokoro operator launcher | Starts the TTS service and stores PID/log state under `vault_system/runtime/`. |
| `orb_mcp_host_relay.py` | HTTP-to-stdio Desktop MCP relay | Used by `ORBDesktopMCPClient` when `ORB_DESKTOP_MCP_URL` is configured; audit events go to the canonical Vault. |
| `start_orb_mcp_host_relay.sh` | Desktop MCP relay entry point | Resolves the local or R-drive MCP server and starts the relay on port `8765` by default. |
| `orb_mcp_test_pad.py` | Safe visual integration fixture | Operator-only test window used to verify OCR, pointer, mouse, and confirmation behavior without targeting another application. |

## Validation

```bash
bash -n tools/*.sh
python3.12 -m py_compile tools/*.py
tools/check_weaver_runtime.sh
curl http://127.0.0.1:8880/health
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/tools/list
```

The MCP test pad intentionally requires a graphical desktop and must be started manually:

```bash
python3.12 tools/orb_mcp_test_pad.py
```
