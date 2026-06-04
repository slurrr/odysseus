# Current Goal
Make Docker usage feel local by persisting app state and sharing one HF cache/model cache across container recreates.

# Current State
- `docker-compose.yml` now mounts a host HF cache at `/app/.cache/huggingface` and FastEmbed cache at `/app/.cache/fastembed`.
- Container env now pins `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, and `FASTEMBED_CACHE_PATH` to those container paths.
- Host cache dirs exist at `/home/poop/models/hf` and `/home/poop/models/fastembed`.
- UI state already persists via `./data` mounts (`settings.json`, `cookbook_state.json`, DB, etc.).
- HF token is stored and working from Cookbook state; downloads/dep discovery are fine.
- GPU passthrough is working now.
- vLLM failures are due to launch-shape differences, not the driver: first VRAM headroom, then Gemma4 multimodal profiling when the run is not text-only.
- The working agentmux reference stack (`mem_gem_hs*`) uses `language_model_only = true`, `enable_prefix_caching = true`, `kv_cache_dtype = fp8_e4m3`, `chat_template_content_format = "openai"`, `--no-trust-request-chat-template`, and lower `gpu_memory_utilization`.

# Decisions
- Use Docker’s mounted volumes for persistence; do not rely on the UI to write `.env`.
- Keep one shared HF cache on the host instead of per-container downloads.
- Keep serve engines (`vllm`, `llama.cpp`) installed inside the container and persisted under `./data/local`.

# Open Problems
- Need to port the known-good Gemma4 vLLM launch shape into Odysseus (especially `language_model_only`, fp8 KV cache, and conservative GPU utilization).
- Speculative decoding with Gemma4 remains coupled to the text-only launch shape and assistant draft model from the agentmux stack.

# Resume Instructions
Compare the current Odysseus serve command against `/home/poop/code/dev/agentmux/mux/lab/mem_gem_e4b_hindsight.toml` and `/home/poop/code/dev/agentmux/mux/lab/mem_gem_e4b_hindsight_external.toml`. The key delta to port is `language_model_only = true` (plus the fp8 KV cache / prefix cache / chat template flags). If you want the exact next step, make an Odysseus preset or command that mirrors that stack and retry with `--gpu-memory-utilization 0.8`.
