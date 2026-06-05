# System Prompt / Persona / Instruction Stack Notes

## Goal

Understand and eventually make controllable the instruction stack that shapes model behavior.

This should cover:
- global system prompt
- per-chat/session prompt
- agent-mode/tool-harness prompt
- research prompt(s)
- compare prompt(s)
- memory/skills injected context
- provider/model-specific chat template behavior

## Why this matters

The app has strong local-agent behavior, but it is not yet obvious from the UI where the model's governing instructions come from or how to edit them safely.

For local models, especially llama.cpp/GGUF, prompt shape matters a lot:
- chat template compatibility
- tool-call formatting
- thinking/reasoning channel behavior
- context usage
- whether old sessions can continue after changing endpoint/model

## Questions to answer later

- Is there a global system prompt setting?
- Is there a per-session/persona prompt?
- Are agent-mode instructions separate from normal chat instructions?
- Where are tool schemas/tool harness instructions injected?
- Does Deep Research use a separate prompt stack?
- Does Compare use a separate prompt stack?
- How does memory/skills retrieval get inserted?
- How much of the system/tool prompt is counted in the context meter?
- Can users create named prompt profiles/recipes like Serve recipes?

## Files likely involved

Start with:
- `src/llm_core.py`
- `src/chat_handler.py`
- `src/chat_processor.py`
- `src/agent_loop.py`
- `src/tool_schemas.py`
- `src/tool_implementations.py`
- `src/deep_research.py`
- `static/js/chat.js`
- settings under `data/settings.json`

## Desired outcome

Eventually provide a clear “instruction stack” map and maybe UI controls for:
- default chat system prompt
- agent prompt/profile
- research prompt/profile
- model-specific prompt overrides
- safe prompt reset/export/import

No implementation yet; this is a roadmap item.
