# ORB Inference Runtime Strategy

## Product boundary

The ORB is the product. Inference engines are replaceable power plants. Website ORBs, desktop ORBs, Weaver cognition, Site World retrieval, and the Stage Governor never bind directly to llama.cpp, Aphrodite, TensorRT-LLM, or Ollama.

All articulation requests pass through the ORB Inference Gateway. Deterministic doctrine, allowed actions, workflow state, and safety decisions remain outside the language-model runtime.

## Runtime opportunity

### Universal distribution — llama.cpp

The universal lane makes a downloadable ORB viable across CPU-only, partial-offload, and NVIDIA systems. GGUF, mmap, adjustable GPU layers, and a compact headless server support the widest hardware range.

### Hosted recurring revenue — Aphrodite

The scale lane is intended for shared hosted inference, continuous batching, concurrent Website ORB visitors, and efficient use of a server GPU. Customer Site Worlds and permissions remain isolated even when an approved base model is shared.

### Enterprise acceleration — TensorRT-LLM

The accelerated lane is intended for frozen NVIDIA deployment profiles: showrooms, kiosks, call centers, dealership servers, and dedicated appliances. Current model-serving and deliberately pinned precompiled-engine deployments are separate profiles.

## Routing doctrine

1. The gateway receives a request using an Ollama-compatible or OpenAI-compatible contract.
2. The requested lane establishes provider priority.
3. Health checks exclude unavailable providers.
4. The first healthy provider is called.
5. A failed non-streaming call falls through to the next healthy provider.
6. Latency and failures are recorded in `vault_system/runtime/inference_gateway/`.
7. No inference provider may create a parallel persistent memory store for Orb Weaver.

## Hot-path doctrine

- Keep normal Website ORB prompts short.
- Keep one small articulation model resident.
- Do not load all GPU runtimes simultaneously on a 6 GB GPU.
- Keep TPC, Stage Governor, pointer permissions, and verified actions deterministic.
- Escalate to scale or acceleration lanes only when the workload justifies it.
- Benchmark time-to-first-response and complete voice-turn latency, not only tokens per second.
