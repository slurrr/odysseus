# Odysseus Dev Fork Roadmap Notes

These are local working notes for hacking on this fork. They are not upstream docs yet.

## Current baseline

Working well enough to use:
- llama.cpp/GGUF serving through Cookbook with CUDA offload.
- Text serve auto-registration into model picker.
- Chat/session resume with the registered llama.cpp endpoint.
- Normal Cookbook Stop now leaves a stopped serve card for relaunch/edit; manual Remove deletes it.
- Serve recipes can be saved from the Serve tab, which is the right durable mechanism for known-good launch configs.
- `/inspector` is available for local diagnostic traces: prompt/context/provider payloads, responses/reasoning, auto-name, and tidy-session traces. Trace files live under `data/debug/inspector_traces` and are cleaned on startup.

## Main threads to work through

1. System prompt / instruction stack: map global/session/agent/research prompts and make them understandable/editable.
2. Tool calling / structured output: understand schemas, parsing, retries, and local-model-friendly improvements.
3. Deep Research defaults, same-endpoint behavior, and llama.cpp concurrency.
4. Voice: STT/TTS integration and external servers.
5. Cookbook model discovery / hardware fit accuracy.
6. Feasibility of tying Odysseus sessions to `agent-session-srv`, pi, and pi-collab.

Completed/current baseline:
- llama.cpp runtime hardening and sane launch defaults are documented in `poop/serving/llama-cpp-runtime-hardening.md`.
- `/inspector` backend + modal are implemented enough for day-to-day diagnosis; see `poop/poop-inspector-spec.md`.
- Repo orientation map for compactions/new sessions: `poop/repo-map.md`.

Current verified watch items:
- Monitor `/inspector` while exercising chat/agent/research before making more prompt/tool changes.
- Tidy-session cleanup now has a new-empty-session grace period; verify future `internal:tidy_sessions` traces before changing cleanup rules again.
- Auto-name now uses separate `internal:auto_name` traces; if title UI refresh lags, inspect response/result in that trace before patching UI.

## Suggested priority / dependency order

1. **Instruction stack / tracing validation** — use `/inspector` to map system/session/agent/research prompts and confirm actual provider payloads/responses before changing behavior. Backend/modal are in place; remaining work is refinement and observation.
2. **Tool calling** — inspect structured output/tool schemas and make a local-model-friendly path before leaning on agent workflows.
3. **Deep Research on current endpoint** — once prompts/tools are understood, make research use the current/default local model cleanly and tune concurrency.
4. **Voice endpoints** — integrate existing faster-whisper/Kokoro servers after endpoint identity and tool behavior are clearer.
5. **Hardware fit/model discovery** — useful for future model choices and profiles, but less blocking now that a working GGUF serve path exists.
6. **agent-session-srv / pi / pi-collab integration** — highest leverage long-term, but should come after sessions, prompts, tools, and endpoint identity are mapped.
