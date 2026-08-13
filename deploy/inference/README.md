# ORB Inference Runtime Stack

Orb Weaver uses one stable local API and three optimized inference lanes:

- **Universal:** `llama.cpp` / `llama-server` with GGUF and mmap.
- **Scale:** Aphrodite Engine for continuous batching and KV-cache-efficient shared serving.
- **Accelerated:** TensorRT-LLM for fixed NVIDIA deployments, including a guarded legacy precompiled-engine path.
- **Fallback:** Ollama, retained so the current deployment can continue operating during migration.

Orb Weaver itself calls only:

```text
http://127.0.0.1:16520/api/generate
```

The gateway probes providers, selects the requested lane, records provider/latency/failure telemetry under the canonical Vault, and fails over without rewriting Website ORB cognition.

## Lane selection

| Lane | First choice | Intended use |
|---|---|---|
| `universal` | llama.cpp | Normal Website ORB and desktop operation |
| `scale` | Aphrodite | Concurrent visitors and hosted customer ORBs |
| `accelerated` | TensorRT-LLM | Fixed NVIDIA enterprise deployment |
| `fallback` | Ollama | Compatibility and recovery |
| `auto` | llama.cpp or Aphrodite | Switches to scale at the configured active-request threshold |

Send `X-ORB-Lane: universal`, `scale`, `accelerated`, `fallback`, or `auto` to the gateway. If omitted, `ORB_INFERENCE_DEFAULT_LANE` is used.

## Important 6 GB GPU operating rule

Do not keep llama.cpp, Aphrodite, and TensorRT-LLM models resident at the same time on the RTX 3050 6 GB. All three are integrated, but the operator profile script activates one GPU-heavy engine at a time. Ollama should also be stopped when it holds a competing model in VRAM.

## Setup

```bash
cd /path/to/Orb_Weaver
cp deploy/inference/env.example .env.inference
nano .env.inference
```

Install each lane as needed:

```bash
bash deploy/inference/llama_cpp/install_wsl.sh
bash deploy/inference/aphrodite/install_wsl.sh
bash deploy/inference/tensorrt_llm/install_wsl.sh
```

Start the gateway and one engine profile:

```bash
bash tools/orb-inference-profile.sh gateway
bash tools/orb-inference-profile.sh llama
```

Inspect readiness:

```bash
bash tools/orb-inference-profile.sh status
```

Benchmark all available lanes:

```bash
python backend/tools/benchmark_inference_gateway.py \
  --base-url http://127.0.0.1:16520 \
  --output vault_system/runtime/inference_gateway/benchmark.json
```

## Container behavior

The primary Orb Weaver container starts the inference gateway on loopback port `16520`. Provider engines remain host/WSL services and are reached through `host.docker.internal`. This avoids putting CUDA runtimes and model weights inside the web application image.

## TensorRT-LLM paths

`run_current.sh` uses the current `trtllm-serve` model-serving path.

`build_legacy_engine.sh` exists for a deliberately pinned TensorRT-LLM environment that still provides `trtllm-build`. It refuses to run when that command is absent. Precompiled engines are hardware/runtime/profile-specific and must be generated on the target NVIDIA class; they are not committed to Git.
