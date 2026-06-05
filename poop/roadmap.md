# Odysseus Dev Fork Roadmap Notes

These are local working notes for hacking on this fork. They are not upstream docs yet.

## Current baseline

Working well enough to use:
- llama.cpp/GGUF serving through Cookbook with CUDA offload.
- Text serve auto-registration into model picker.
- Chat/session resume with the registered llama.cpp endpoint.
- Normal Cookbook Stop now leaves a stopped serve card for relaunch/edit; manual Remove deletes it.
- Serve recipes can be saved from the Serve tab, which is the right durable mechanism for known-good launch configs.

## Main threads to work through

1. llama.cpp runtime hardening and sane launch defaults.
2. System prompt / instruction stack: map global/session/agent/research prompts and make them understandable/editable.
3. Tool calling / structured output: understand schemas, parsing, retries, and local-model-friendly improvements.
4. Deep Research defaults, same-endpoint behavior, and llama.cpp concurrency.
5. Voice: STT/TTS integration and external servers.
6. Cookbook model discovery / hardware fit accuracy.
7. Feasibility of tying Odysseus sessions to `agent-session-srv`, pi, and pi-collab.

## Suggested priority / dependency order

1. **Runtime baseline** — keep llama.cpp serving stable first. Everything else depends on a sane local endpoint.
2. **Instruction stack** — map system/session/agent/research prompts next, because prompt shape affects normal chat, tools, and research.
3. **Tool calling** — inspect structured output/tool schemas and make a local-model-friendly path before leaning on agent workflows.
4. **Deep Research on current endpoint** — once prompts/tools are understood, make research use the current/default local model cleanly and tune concurrency.
5. **Voice endpoints** — integrate existing faster-whisper/Kokoro servers after endpoint identity and tool behavior are clearer.
6. **Hardware fit/model discovery** — useful for future model choices and profiles, but less blocking now that a working GGUF serve path exists.
7. **agent-session-srv / pi / pi-collab integration** — highest leverage long-term, but should come after sessions, prompts, tools, and endpoint identity are mapped.
