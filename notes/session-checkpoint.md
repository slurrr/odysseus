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
- Local notes scaffold expanded: `poop/README.md`, `poop/repo-map.md`, `poop/roadmap.md`, `poop/system-prompt.md`, `poop/tool-calling.md`, `poop/poop-inspector-spec.md`, `poop/serving/README.md`, `poop/serving/llama-cpp.md`, `poop/serving/llama-cpp-runtime-hardening.md`, `poop/serving/voice-stt-tts.md`, `poop/serving/model-discovery-hwfit.md`, `poop/serving/deep-research.md`, `poop/integration-agent-session-srv.md`.
- `/inspector` is implemented for active monitoring: `src/debug_trace.py`, `routes/inspector_routes.py`, `static/js/inspector.js`, trace types `user_chat`, `internal:auto_name`, `internal:tidy_sessions`, provider payloads, response/reasoning/result capture, startup cleanup.
- `docker-compose.yml` now mounts host `/home/poop/models` into the container at `/models` so Cookbook can scan local quants outside HF cache. Recreated `odysseus` container to apply the volume; verified `/models`, `/models/hf`, and `/models/local` exist inside container.
- Tidy race found and fixed: event-triggered chat tidy could delete brand-new empty sessions before first stream persisted messages. `src/session_actions.py` now keeps new empty sessions during a grace period and traces `new_empty_grace_period`.

# Decisions
- Keep serving notes and repo forensics in `poop/` as local dev docs, not upstream docs yet.
- Prefer native `llama-server` over `llama-cpp-python` for modern GGUF chat templates and CUDA offload.
- Use `-c 4096` for the known-good Gemma 31B GGUF baseline; larger contexts need KV/cache tuning and should not fall back to CPU.
- Text model serves should be auto-registered as OpenAI-compatible endpoints, same conceptual UX as manual endpoint registration.

# Open Problems
- Cookbook Running/servable state could still use a clearer design: ephemeral live tasks vs durable serve presets/history. Current practical combo is saveable Serve recipes + stopped cards.
- User marked runtime baseline done; roadmap now starts with instruction stack, then tool calling, Deep Research, voice, hwfit, agent-session-srv/pi integration.
- Initial system prompt / instruction stack map completed in `poop/system-prompt.md`: no single global editable prompt; presets/personas are system prompts, inject prefix/suffix are user-message wrappers, agent prompt is large/separate, research has separate prompts, context trimming uses crude first-system-message priority.
- `/inspector` spec/status updated in `poop/poop-inspector-spec.md`: slash command opens hidden dev modal with tabs for Prompt Stack, Tools, Compaction/Pruning, Provider Payload, Runtime. Main UI uses clean key/value/cards/chips, no dumps/tables. Full content opens in secondary scrollable popup. Always available, traces cleaned at startup, full non-incognito context captured, incognito/nobody never traced, read-only. Current remaining polish: better identity/header display, deeper exact pruning diagnostics, agent tool-call event detail.
- Need map tool calling / structured output: schemas, parsing, retry/repair, local-model-friendly reduced tool mode.
- Need investigate voice endpoint mode with user's existing faster-whisper/Kokoro HTTP servers.
- Need investigate hwfit/model discovery because manual 24GB CUDA override may not filter recommendations as expected.
- Need inspect Deep Research endpoint/model fallback so single-GPU local runs use current/default llama.cpp endpoint instead of unexplained defaults.
- Need explore feasibility of `agent-session-srv` / pi / pi-collab integration after session schema is mapped.
- Continuing an old chat after relaunch can fail while fresh chat works; likely stale endpoint id/model id mismatch (`repo_id` vs GGUF basename) or cached endpoint metadata.
- `/api/models` cache may take up to 30s to reflect auto-registered endpoints; may need explicit invalidation or probe after auto-register.

# Resume Instructions
1. Start by reading `poop/repo-map.md`, `poop/roadmap.md`, and this checkpoint to regain orientation after compaction.
2. Use `/inspector` while exercising chat/agent/research. Trace files are under `data/debug/inspector_traces`; trace types currently include `user_chat`, `internal:auto_name`, and `internal:tidy_sessions`.
3. Verify a fresh chat no longer disappears when event-triggered tidy runs; tidy traces should show `new_empty_grace_period` for brand-new empty sessions.
4. Verify incognito/nobody creates no inspector trace, and later review `logs/` for incognito/nobody content leakage.
5. Keep product UI/design intact; only patch verified bugs. Model picker style/behavior changes were reverted.
6. For local quants, add Cookbook search paths using container paths such as `/models/local`, `/models/local/quants`, or `/models/local/quants/llm-compressor-artifacts`; do not use host `~/models/...` paths inside the container.
7. Next major thread: tool calling. Inspect `src/agent_loop.py`, `src/tool_schemas.py`, `src/tool_implementations.py`, `src/tool_index.py` and identify native OpenAI tools vs fenced/custom parser/repair paths; see `poop/tool-calling.md`.
7. Then Deep Research: inspect/tune current-endpoint behavior and concurrency. `_resolve_research_endpoint(sess)` already falls back to session endpoint/model when research settings are blank.
8. Then voice: list existing ModelEndpoints/settings and test external faster-whisper/Kokoro OpenAI-compatible `/audio/transcriptions` and `/audio/speech`; see `poop/serving/voice-stt-tts.md`.
9. Then hwfit: capture `/api/hwfit/system?fresh=true` and `/api/hwfit/models?...manual 24GB...` responses and compare frontend params; see `poop/serving/model-discovery-hwfit.md`.
10. Then integration: map session/fork storage in `routes/session_routes.py`, `core/session_manager.py`, and DB tables; see `poop/integration-agent-session-srv.md`.
