# Current Goal
Tighten Odysseus local model serving, starting with llama.cpp/GGUF in Docker, and keep local contributor/agent notes under `poop/`.

# Current State
- Native CUDA `llama-server` now builds inside the Odysseus container using pip-installed NVIDIA CUDA wheels from vLLM under `/app/.local/lib/python3.12/site-packages/nvidia/cu13`.
- llama.cpp CUDA bootstrap fixes are in `routes/cookbook_helpers.py`: CUDA wheel compatibility symlinks, `CUDAToolkit_ROOT`, `LD_LIBRARY_PATH`, and `CCCL_DISABLE_CTK_COMPATIBILITY_CHECK`.
- llama.cpp launch preflight fixes are in `routes/cookbook_routes.py`: CUDA wheel `LD_LIBRARY_PATH` is set even when an existing `llama-server` skips rebuild.
- Added auto-registration in `routes/cookbook_routes.py` for OpenAI-compatible text serves (`llama-server`, `llama_cpp.server`, `vllm serve`, `sglang.launch_server`) so UI launches should create/update a `ModelEndpoint` without manual endpoint registration.
- Manual verified working run used `serve-gemma31b-cuda` on port `8001`, CUDA0 RTX 4090, ~18 GiB VRAM, `/health`, `/v1/models`, and `/v1/chat/completions` OK.
- User verified UI launch/session resume/model auto-registration are now solid.
- Changed `static/js/cookbookRunning.js` so normal Stop keeps a stopped serve card for relaunch/edit instead of removing/tombstoning it; manual Remove still deletes the card.
- Local notes scaffold expanded: `poop/README.md`, `poop/roadmap.md`, `poop/system-prompt.md`, `poop/tool-calling.md`, `poop/serving/README.md`, `poop/serving/llama-cpp.md`, `poop/serving/llama-cpp-runtime-hardening.md`, `poop/serving/voice-stt-tts.md`, `poop/serving/model-discovery-hwfit.md`, `poop/serving/deep-research.md`, `poop/integration-agent-session-srv.md`.

# Decisions
- Keep serving notes and repo forensics in `poop/` as local dev docs, not upstream docs yet.
- Prefer native `llama-server` over `llama-cpp-python` for modern GGUF chat templates and CUDA offload.
- Use `-c 4096` for the known-good Gemma 31B GGUF baseline; larger contexts need KV/cache tuning and should not fall back to CPU.
- Text model serves should be auto-registered as OpenAI-compatible endpoints, same conceptual UX as manual endpoint registration.

# Open Problems
- Cookbook Running/servable state could still use a clearer design: ephemeral live tasks vs durable serve presets/history. Current practical combo is saveable Serve recipes + stopped cards.
- Roadmap order updated: runtime baseline → instruction stack → tool calling → Deep Research → voice → hwfit → agent-session-srv/pi integration.
- Need map system prompt / instruction stack: global, session, agent, research, compare, memory/skills, tool harness.
- Need map tool calling / structured output: schemas, parsing, retry/repair, local-model-friendly reduced tool mode.
- Need investigate voice endpoint mode with user's existing faster-whisper/Kokoro HTTP servers.
- Need investigate hwfit/model discovery because manual 24GB CUDA override may not filter recommendations as expected.
- Need inspect Deep Research endpoint/model fallback so single-GPU local runs use current/default llama.cpp endpoint instead of unexplained defaults.
- Need explore feasibility of `agent-session-srv` / pi / pi-collab integration after session schema is mapped.
- Continuing an old chat after relaunch can fail while fresh chat works; likely stale endpoint id/model id mismatch (`repo_id` vs GGUF basename) or cached endpoint metadata.
- `/api/models` cache may take up to 30s to reflect auto-registered endpoints; may need explicit invalidation or probe after auto-register.

# Resume Instructions
1. For runtime, keep validating llama.cpp baseline and note any KV/cache/concurrency changes; see `poop/serving/llama-cpp-runtime-hardening.md`.
2. For system prompt, map instruction injection paths in `src/llm_core.py`, `src/chat_handler.py`, `src/chat_processor.py`, `src/agent_loop.py`, `src/tool_schemas.py`, and `src/deep_research.py`; see `poop/system-prompt.md`.
3. For tool calling, inspect `src/agent_loop.py`, `src/tool_schemas.py`, `src/tool_implementations.py`, `src/tool_index.py` and identify whether calls use native OpenAI tools, custom JSON, or parser repair; see `poop/tool-calling.md`.
4. For Deep Research, inspect `routes/research_routes.py` endpoint/model resolution and make blank research settings fall back to current/default chat endpoint if needed.
5. For voice, list existing ModelEndpoints and settings, then test whether external faster-whisper/Kokoro servers expose OpenAI-compatible `/audio/transcriptions` and `/audio/speech` paths; see `poop/serving/voice-stt-tts.md`.
6. For hwfit, capture `/api/hwfit/system?fresh=true` and `/api/hwfit/models?...manual 24GB...` responses and compare frontend params; see `poop/serving/model-discovery-hwfit.md`.
7. For integration, map session/fork storage in `routes/session_routes.py`, `src/session_manager.py`, and `data/sessions.json`; see `poop/integration-agent-session-srv.md`.
