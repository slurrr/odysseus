# System Prompt / Persona / Instruction Stack Notes

## Status

Initial map complete. No behavior changes yet.

The instruction stack is split across several layers rather than one obvious “global system prompt”. Normal chat, agent mode, research, compare, group chat, scheduled tasks, memory extraction, skill extraction, and email/vision helpers all build their own prompts.

## High-level answer

There is **not** one global editable default system prompt for all chat.

What exists:
- Prompt/persona presets in `data/presets.json`.
- A custom persona/prompt UI wired through `static/js/presets.js` and `/api/presets/*`.
- A mandatory prompt-safety system policy injected into normal chat context.
- A large agent/tool system prompt injected only in agent mode.
- Deep Research uses its own task-specific prompts, mostly as user messages to the research model.
- Compare mode mostly reuses the normal `/api/chat_stream` path, with `compare_mode=true` and optional `preset_id`.
- Group chat has its own frontend-built system prompt in `static/js/group.js`.

## Normal chat instruction path

Main files:
- `routes/chat_routes.py`
- `routes/chat_helpers.py`
- `src/chat_handler.py`
- `src/chat_processor.py`
- `src/llm_core.py`
- `src/preset_manager.py`
- `data/presets.json`
- `static/js/presets.js`
- `static/js/chat.js`

Flow:

1. Frontend sends `/api/chat_stream` with:
   - `message`
   - `session`
   - optional `preset_id`
   - toggles like `use_web`, `use_rag`, `use_research`, `mode`, `incognito`

2. `routes/chat_helpers.build_chat_context(...)`:
   - extracts selected preset via `chat_handler.validate_and_extract_preset(...)`
   - preprocesses attachments/YouTube/images
   - stores the user message in session history
   - calls `chat_processor.build_context_preface(...)`

3. `src/chat_processor.ChatProcessor.build_context_preface(...)` builds preface messages:
   - if preset selected: adds preset `system_prompt` as `role: system`
   - always adds `UNTRUSTED_CONTEXT_POLICY` as `role: system`
   - memory/RAG/web/URL/YouTube content is added as `role: user` through `untrusted_context_message(...)`, not system
   - skills index can be included only in agent mode and only as untrusted context

4. Final chat messages are:

```text
[preset system prompt, if any]
[prompt-safety system policy]
[untrusted memory/RAG/web/etc context]
[session history, including current user message]
```

5. `src/llm_core.py` sanitizes and sends to provider.
   - Multiple system messages are consolidated into one first system message.
   - For Anthropic, system messages are moved to Anthropic's top-level `system` field.
   - For OpenAI-compatible endpoints, including llama.cpp, messages remain OpenAI-style.

## Presets / personas

Preset storage:
- `data/presets.json`
- defaults in `src/preset_manager.py`

Current built-ins:
- `code_analyze`
- `brainstorm`
- `reason`
- `custom`

Custom preset fields:
- `name`
- `character_name`
- `temperature`
- `max_tokens`
- `system_prompt`
- `inject_prefix`
- `inject_suffix`
- `enabled`

Important distinction:
- `system_prompt` is sent server-side as system prompt when `preset_id=custom` or another preset is active.
- `inject_prefix` / `inject_suffix` are applied client-side in `static/js/chat.js` by modifying the user message text before send.
- The backend stores `inject_prefix`/`inject_suffix`, but normal chat prompt assembly does not use them directly.

Implication:
- A “prompt injection” preset is not actually a system prompt; it is user-message wrapping.
- A “character/persona” preset is a real system prompt.

## Prompt safety / untrusted context

File:
- `src/prompt_security.py`

`UNTRUSTED_CONTEXT_POLICY` is always inserted as a system message in normal chat preface.

External or user-editable data is wrapped by `untrusted_context_message(...)`, producing:

```json
{
  "role": "user",
  "content": "UNTRUSTED SOURCE DATA ...",
  "metadata": {"trusted": false, "source": "..."}
}
```

Used for:
- memory
- RAG documents
- web search results
- fetched URLs
- YouTube transcripts
- active editor document in agent mode
- relevant skills / skills index
- research context injected into a normal chat response

This is good architecture: retrieved/user-editable text is mostly kept out of trusted system role.

## Agent mode instruction path

Main file:
- `src/agent_loop.py`

Key pieces:
- `_AGENT_PREAMBLE`
- `_AGENT_RULES`
- `_API_AGENT_RULES`
- `TOOL_SECTIONS`
- `_assemble_prompt(...)`
- `_build_system_prompt(...)`
- `AGENT_SYSTEM_PROMPT`

Flow:

1. Normal chat context is built first, same as above.
2. `routes/chat_routes.py` calls `stream_agent_loop(...)` when mode is `agent`.
3. `src/agent_loop._build_system_prompt(...)` inserts the agent prompt after any existing leading system messages.
4. Consecutive system messages are merged.

Effective agent system order is roughly:

```text
[preset persona, if selected]
[prompt-safety policy]
[agent date/time block]
[agent/tool rules + tool instructions]
```

Dynamic additions:
- current date/time is prepended to the agent prompt every request
- active document/email/PDF-form context is inserted as untrusted user-role data near the latest user message
- relevant skills are inserted as untrusted user-role data near the latest user message
- email writing style may be appended to the trusted agent system prompt when email tools or an email document are active
- email document format guidance may be appended to the trusted agent system prompt when email tools are relevant

Important split:
- For API/native-tool models, compact rules plus tool schemas are sent.
- For non-native/fenced-block path, large fenced code-block tool instructions are put in the prompt.

This matters for small quantized models: the agent prompt can be very large and tool-heavy.

## Deep Research instruction path

Main files:
- `routes/research_routes.py`
- `routes/chat_routes.py`
- `services/research/research_handler.py`
- `src/deep_research.py`

Endpoint/model resolution:
- `_resolve_research_endpoint(sess)` calls `resolve_endpoint("research", fallback_url=sess.endpoint_url, fallback_model=sess.model, fallback_headers=sess.headers)`.
- This means blank research settings should fall back to the current session endpoint/model.

Prompt behavior:
- Deep Research mostly builds task prompts inside `src/deep_research.py` and sends them as `role: user`, not as reusable global system prompts.
- It uses prompt constants such as planning/query/extraction/synthesis/final-report prompts.
- The first in-chat research message may inject a temporary system prompt asking for 2-3 clarification questions before actual research starts.

Implication:
- Research has a separate prompt stack from normal chat/persona.
- A selected chat persona may not govern research internals unless the research query synthesis path or endpoint context explicitly includes it.

## Compare mode

Main files:
- `static/js/compare/stream.js`
- `routes/chat_routes.py`

Compare sends to `/api/chat_stream` with:
- `compare_mode=true`
- optional `preset_id`
- mode-dependent toggles

So compare generally reuses normal chat/agent prompt paths, but strips or disables many tools depending on compare type.

## Group chat

Main file:
- `static/js/group.js`

Group chat is separate. It builds a frontend-side system prompt like:
- assigned character/persona
- speaker/name conventions
- concise group-chat behavior

It then sends direct chat-completion-style requests from the frontend group module.

This should be treated as a separate prompt stack.

## Context trimming / compaction interaction

Main file:
- `src/context_compactor.py`

Behavior:
- `maybe_compact(...)` splits out all system messages, summarizes older conversation, and preserves system messages.
- `trim_for_context(...)` keeps only the **first** system message as “essential” if context is too large, and may drop/truncate later system messages.

Important subtlety:
- Before `llm_core` consolidates system messages, the first system message may be the preset prompt if a preset exists.
- If no preset exists, the first system message is the prompt-safety policy.
- In agent mode, agent prompt is inserted after leading system messages, so under severe trimming it may be more vulnerable to being dropped/truncated than the first system prompt.

This is a possible bug/rough edge for small-context local models.

## Rough edges found

1. No obvious global default system prompt.
   - Normal chat with no preset gets only prompt-safety policy, not a user-configurable assistant identity/style prompt.

2. `inject_prefix` / `inject_suffix` are named like prompt controls but act as user-message wrappers.
   - This is useful, but should be clearly labeled as user-message injection, not system instructions.

3. Agent prompt is huge and mixed-purpose.
   - It includes general policy, tool usage rules, UI conventions, Cookbook-specific corrections, email rules, etc.
   - This may be too much for small quantized models and directly relates to tool-call reliability.

4. System-message priority during trimming is crude.
   - “First system message wins” can accidentally privilege persona or safety policy over agent/tool instructions depending on mode and context pressure.

5. Research has separate prompts and does not obviously inherit the selected persona/system prompt.
   - This is probably correct for research quality, but the UI should make that clear.

6. Many utility/background tasks have separate prompts.
   - Auto-title, memory extraction, skills, email triage, vision helpers, document review, etc. are independent instruction stacks.

## Suggested next improvements

### 1. Add an instruction-stack inspector first

Before changing behavior, add a developer/debug view or API that reports:
- selected preset id
- actual system messages before provider consolidation
- whether agent prompt was added
- rough token count per layer
- whether context trimming dropped any system/context messages

This would make local model failures much easier to debug.

### 2. Create a named “default chat system prompt” setting

Add a real global/default chat instruction that applies when no persona is selected.

Possible order:

```text
[app safety/system invariants]
[default assistant system prompt]
[selected persona/system prompt, if any]
[mode-specific prompt: agent/research/etc]
```

Need decide whether persona overrides or complements default.

### 3. Split agent prompt into smaller profiles

For local quantized models:
- compact agent rules
- fewer tool descriptions
- retrieved relevant tools only
- concise examples for exact expected tool-call format

This belongs with `poop/tool-calling.md`.

### 4. Improve system-message priority for trimming

Mark system messages by purpose/priority instead of relying on position:
- safety invariants
- selected persona
- agent/tool protocol
- conversation summary
- optional context hints

### 5. Clarify UI wording

In the prompt/persona UI:
- “System prompt/persona” = trusted system instruction.
- “Inject prefix/suffix” = user-message wrapper.
- “Research prompt” = separate workflow prompt, not normal chat persona.

## Next files to inspect if implementing

- `src/context_compactor.py` for priority-aware trimming.
- `src/agent_loop.py` for local-model compact agent prompt.
- `static/js/presets.js` and `static/js/chat.js` for prompt UI wording and injection behavior.
- `routes/preset_routes.py` and `src/preset_manager.py` for adding global/default system prompt storage.
- `src/llm_core.py` for an optional debug dump of final provider-bound messages.
