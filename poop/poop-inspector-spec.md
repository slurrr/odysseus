# `/inspector` Diagnostic Inspector Spec

## Goal

Add a hidden/non-intrusive developer inspector for this local fork. It should be opened by a slash command:

```text
/inspector
```

The command opens one normal Odysseus-style modal window with tabs. The inspector captures and renders prompt/tool/context/runtime diagnostics without cluttering the regular chat UI.

This is local-dev instrumentation, not upstream product UI yet.

## Current implementation status

Implemented enough for active diagnosis:
- Slash command `/inspector` opens the modal.
- Backend trace module: `src/debug_trace.py`.
- API routes: `routes/inspector_routes.py` under `/api/inspector/*`.
- Frontend modal: `static/js/inspector.js`.
- Startup cleanup of `data/debug/inspector_traces`.
- Dev compose mounts include `app.py`, `main.py`, `src/`, `routes/`, and `static/`, so trace code changes are live after container restart.
- Trace types currently emitted:
  - `user_chat`
  - `internal:auto_name`
  - `internal:tidy_sessions`
- Captures provider-bound messages/payload, context/token/compaction summary, response/reasoning/result, auto-name outcome, and tidy keep/delete decisions.
- Incognito/nobody trace skip remains a hard requirement.

Recent bug found with tracing:
- Event-triggered chat tidy could delete brand-new empty sessions before the first stream persisted messages. `src/session_actions.py` now keeps new empty sessions for a grace period and traces `new_empty_grace_period`.

Known refinement items:
- Prompt Stack for direct internal calls such as `internal:auto_name` has no `build_chat_context` layers; provider messages/system are still visible via full-content controls.
- Make trace labels more visible in the selector/header if browser/UI still makes current trace identity unclear.
- Add/verify agent tool-call result events and native-vs-fenced parser details.
- Verify incognito/nobody content is not leaked to ordinary logs.

## Design principles

- **Invisible until asked for**: no sidebar button, no default toolbar icon.
- **Easy to open**: `/inspector` from chat input opens the modal.
- **Consistent UI**: use the existing `.modal`, `.modal-content`, `.modal-header`, `.modal-body`, tab button patterns, close/minimize behavior where practical.
- **Trace first, render second**: capture data at the backend prompt/tool dispatch points before building fancy UI.
- **Clean UI, no dumps**: do not render table dumps, JSON dumps, or giant raw blobs in the main inspector. Use clean key/value rows, small cards, chips, and short status lines.
- **Full content in secondary popup**: prompt/message contents are available through buttons such as “Show system”, “Show final messages”, or “Show provider payload”. These open a second modal/popup over the inspector with scrollable full text in actual order. Closing that popup returns to the inspector state.
- **Always available on this fork**: no feature flag, auth/admin gate, or dev-mode gate required for this local dev machine.
- **Clean traces at startup**: diagnostics are temporary runtime artifacts. Delete old traces when the app starts.
- **Full context capture by default**: store the full prompt/context/provider material for non-incognito turns, then cleanup on startup/retention.
- **Incognito/nobody means no trace/logging**: incognito turns must not create inspector traces. Also add a note/check to ensure `logs/` does not capture nobody/incognito content.
- **Read-only**: the inspector is purely diagnostic. No prompt editing from this modal.
- **No behavior change initially**: phase 1 should observe, not alter prompt/tool behavior.

## Modal layout

Route/command:

```text
/inspector
```

Window title:

```text
Inspector
```

Suggested modal dimensions:

```css
width: min(980px, 94vw);
height: min(760px, 92vh);
```

Secondary full-content popup dimensions:

```css
width: min(1080px, 96vw);
height: min(820px, 94vh);
```

The secondary popup should sit above the inspector, be scrollable, and close independently without resetting the inspector tab/trace selection.

Tabs:

1. **Prompt Stack**
2. **Tools**
3. **Compaction / Pruning**
4. **Provider Payload**
5. **Runtime / Endpoint** optional but useful because llama.cpp stability affects all of this

The first four map to the current debugging need. Runtime can be a light tab or delayed.

## Tab 1: Prompt Stack

Purpose: show what instructions/context the model actually received, by layer.

Each layer should render as a compact card or row with clean labels, not a table dump:

- Name: `Prompt safety policy`
- Role: `system`
- Source: `src/prompt_security.py`
- Tokens: `74`
- Status: `included`
- Trust: `trusted` / `untrusted`
- Action: `Show`

Example layers:

- preset/persona system prompt
- prompt-safety policy from `src/prompt_security.py`
- agent date/time block
- agent/tool rules
- active document context
- relevant skills
- memory pinned/recalled
- RAG documents
- web search results
- YouTube transcript/instruction
- conversation summary
- recent chat history
- current user message

Useful controls:

- `System only`
- `Untrusted context`
- `Dropped/truncated`
- `Show full prompt`
- `Show system`
- `Show current user message`

`Show full prompt` opens the secondary popup and renders the whole effective prompt/message sequence in actual order with section headers. It should be readable prose/code-block style, not JSON.

## Tab 2: Tools

Purpose: explain what tool affordances the model saw and what path was used.

Show clean key/value groups:

- Mode: chat / agent / research
- Native schemas: yes/no
- Fenced prompt tools: yes/no
- Disabled by UI: chips/list
- Disabled globally: chips/list
- Auto-escalated: yes/no
- Relevant tools: chips/list
- Sent tools: chips/list
- Schema estimate: token count
- Tool events: short chronological cards
- Parse/validation errors: short error cards

Important question to answer with this tab:

> When a tool is disabled, was its schema actually omitted, or only discouraged?

This is critical for local quantized models and prompt bloat.

## Tab 3: Compaction / Pruning

Purpose: make context behavior visible.

Show per turn as clean metric cards/key-values:

- Context length
- Before compaction
- Compaction threshold
- Compaction ran
- Messages summarized
- Summary tokens
- After compaction
- Before trim
- After trim
- Reserve tokens
- Dropped messages
- Dropped/truncated layers
- Protected messages survived

Also show a compact recent-traces list, not a dump/table. Each item can read like:

```text
Turn 14 · 3,820 → 3,120 tokens · compacted no · trimmed yes · dropped 2
```

Important rough edge to surface:

- `trim_for_context(...)` currently keeps the first system message as essential and may drop later system messages. In agent mode, that can affect the agent/tool prompt under pressure.

## Tab 4: Provider Payload

Purpose: show the final provider-bound request shape after sanitization/consolidation.

Show clean key/value groups:

- Provider: OpenAI-compatible / Anthropic / Ollama / etc.
- Target URL/base
- Model id
- Temperature
- Max tokens
- Stream
- Message count
- System consolidation
- Tool count/names

Provide buttons:

- `Show provider prompt`
- `Show final messages`
- `Show tool schemas`

These open the secondary full-content popup. Main tab should not show raw JSON by default.

For Anthropic:
- show top-level `system` text/block summary
- show messages after conversion
- show tools after conversion

For llama.cpp/OpenAI-compatible:
- show final `messages` and `tools` JSON shape

## Optional Tab 5: Runtime / Endpoint

Purpose: keep local-serving facts adjacent to prompt debugging.

Show lightweight endpoint facts:

- selected session endpoint URL/base
- model id
- `/v1/models` result if cached
- last activity age
- context length used by Odysseus
- last known usage metrics
- llama.cpp health/slots info if available later
- startup log path if launched by Cookbook

This can be phase 4+.

## Backend trace model

Implemented as a small file-backed trace capture module:

```text
src/debug_trace.py
```

Current/target API shape:

```python
def begin_trace(session_id: str, turn_id: str, mode: str, user: str | None) -> str: ...
def add_layer(trace_id: str, layer: dict) -> None: ...
def add_context_event(trace_id: str, event: dict) -> None: ...
def add_tool_event(trace_id: str, event: dict) -> None: ...
def set_provider_payload(trace_id: str, payload: dict) -> None: ...
def finish_trace(trace_id: str, status: str = "done") -> None: ...
def list_traces(session_id: str | None = None, limit: int = 20) -> list[dict]: ...
def get_trace(trace_id: str) -> dict | None: ...
```

Storage:

Uses JSON files:

```text
data/debug/inspector_traces/<session_id>/<turn_id>.json
```

Pros:
- easy to inspect manually
- no DB migrations
- local-dev friendly

Startup cleanup:
- delete `data/debug/inspector_traces` on app startup
- recreate it empty
- implemented in `src.app_initializer.initialize_managers()`

Retention during runtime:
- keep a practical recent ring buffer, e.g. last 50 globally or last 20 per session
- full non-incognito content is stored during runtime and removed on cleanup

No DB storage planned unless this becomes much more permanent.

## Trace schema sketch

```json
{
  "trace_id": "...",
  "session_id": "...",
  "turn_id": "...",
  "message_id": "...",
  "created_at": "2026-06-03T...Z",
  "owner": "...",
  "mode": "chat|agent|research",
  "compare_mode": false,
  "incognito": false,
  "endpoint": {
    "url": "http://localhost:8001/v1/chat/completions",
    "base_url": "http://localhost:8001/v1",
    "provider": "openai-compatible",
    "model": "gemma-4-31B-it-UD-Q3_K_XL.gguf"
  },
  "preset": {
    "preset_id": "custom",
    "character_name": "",
    "temperature": 0.7,
    "max_tokens": 0,
    "has_system_prompt": true,
    "has_inject_prefix": false,
    "has_inject_suffix": false
  },
  "layers": [
    {
      "id": "safety-policy",
      "name": "Prompt safety policy",
      "role": "system",
      "source": "src/prompt_security.py:UNTRUSTED_CONTEXT_POLICY",
      "trusted": true,
      "tokens": 74,
      "chars": 312,
      "status": "included",
      "content_ref": "layer:safety-policy"
    }
  ],
  "tools": {
    "agent_mode": true,
    "native_tools_sent": true,
    "fenced_prompt_used": false,
    "disabled_tools": ["bash", "python"],
    "sent_tool_names": ["manage_notes", "list_sessions"],
    "schema_count": 2,
    "schema_tokens_est": 900,
    "events": []
  },
  "context": {
    "context_length": 4096,
    "tokens_before_compaction": 3500,
    "compacted": false,
    "tokens_after_compaction": 3500,
    "tokens_after_trim": 3300,
    "dropped_layers": [],
    "truncated_layers": []
  },
  "provider_payload": {
    "target_url": "http://localhost:8001/v1/chat/completions",
    "headers_redacted": true,
    "payload_summary": {
      "message_count": 12,
      "tools_count": 2,
      "stream": true
    },
    "payload_ref": "provider_payload"
  }
}
```

Large content can be stored inline initially but rendered only in the secondary popup. If traces get too large, move content to `content_blobs` keyed by ref.

## Privacy / incognito rules

This fork runs on a local dev machine. Do not spend implementation effort on redaction for now.

Hard rule:
- incognito/nobody mode should not create inspector traces.
- add a specific review item to ensure `logs/` does not contain incognito/nobody message content.

Normal non-incognito traces can include full prompt/context/provider content and are cleaned at startup.

## Backend instrumentation points

### 1. `routes/chat_helpers.build_chat_context(...)`

Capture:
- preset info
- preface layers before session history
- memory/RAG/web/YouTube layer summaries
- context length
- whether compaction/trim ran

May require adding trace hooks around:

```python
preface, rag_sources, web_sources = chat_processor.build_context_preface(...)
messages, context_length, was_compacted = await maybe_compact(...)
messages = trim_for_context(messages, context_length)
```

Better long-term: make `maybe_compact` and `trim_for_context` optionally return diagnostics.

### 2. `src/chat_processor.build_context_preface(...)`

Best place to label layers precisely:
- preset system prompt
- safety policy
- pinned memory
- recalled memory
- RAG
- web
- fetched URL
- skills index

Current return only includes messages and sources. For non-invasive phase 1, infer layers from message order/content. For better phase 2, return optional `preface_debug` metadata.

### 3. `src/agent_loop._build_system_prompt(...)`

Capture:
- agent prompt token count
- compact/full prompt mode
- relevant tools
- disabled tools
- MCP schema count
- skills message injected yes/no
- active document message injected yes/no

### 4. `src/llm_core.stream_llm(...)` / `llm_call_async(...)`

Capture final provider-bound payload after:
- `_sanitize_llm_messages(...)`
- system-message consolidation
- provider adapter conversion
- tools attached

This is the source of truth for Provider Payload tab.

### 5. Tool execution path in `src/agent_loop.py`

Capture:
- model-emitted tool calls
- parser path/native vs fenced
- validation errors
- execution result summary
- retry/repair events later

## API routes

Add local/debug routes, e.g.:

```text
GET /api/inspector/traces?session_id=<id>&limit=20
GET /api/inspector/traces/{trace_id}
DELETE /api/inspector/traces
GET /api/inspector/status
```

Gating:
- always available in this local fork
- still avoid cross-user leaks if auth data is easy to preserve, but do not overbuild auth/redaction here
- never return incognito traces because they should not exist

## Frontend files

Suggested new module:

```text
static/js/inspector.js
```

Responsibilities:
- create/reuse modal
- fetch trace list
- fetch selected trace details
- render tabs
- open secondary full-content popup
- handle refresh

Slash command hook:
- add `/inspector` to `static/js/slashCommands.js`
- command calls `inspector.open()`

HTML approach:
- create modal dynamically in JS, or add a static modal block to `static/index.html`
- dynamic is less intrusive and fits “hidden until used” better

Modal registration:
- if using `modalManager.js`, register `poop-inspector-modal` with close/minimize behavior
- no rail/sidebar button needed

## Suggested UI rendering

Left/top area:
- trace selector dropdown/list: latest turn first
- refresh button
- current session filter checkbox

Top summary cards:

```text
Mode: agent
Model: gemma...
Input tokens: 3,281 / 4,096
Tools sent: 7
Compacted: no
Trimmed: yes
```

Tabs below.

Use compact cards/key-value rows/chips. Do not render tables or raw JSON dumps in the main inspector.

Full content goes in the secondary popup:
- `Show full prompt`
- `Show system`
- `Show provider prompt`
- `Show tool schemas`

Secondary popup content can use readable section headers and preformatted text, but should still avoid raw JSON unless absolutely necessary for provider payload debugging.

## Phased implementation

### Phase 0 — spec — done

- Added this spec.
- No feature flag needed.
- Inspector remains local-dev/read-only.

### Phase 1 — backend trace capture — done enough for active use

Delivered:
- `src/debug_trace.py`
- startup cleanup of `data/debug/inspector_traces`
- trace JSON for non-incognito user chat and selected internal calls
- routes to list/get/delete/status traces
- trace labels/types for `user_chat`, `internal:auto_name`, and `internal:tidy_sessions`

Still validate periodically:
- send incognito turn, confirm no trace file is created
- check ordinary logs for incognito/nobody content leakage

### Phase 2 — provider payload, response, and compaction diagnostics — mostly done

Delivered:
- final provider payload summary from `src/llm_core.py`
- provider messages/full prompt controls
- response/reasoning/result capture for streaming and non-stream calls
- context length and before/after compaction/trim token summaries

Remaining:
- deeper compaction diagnostics: exact dropped/truncated messages/layers
- optional structured diagnostics from `maybe_compact` / `trim_for_context` instead of inferred summaries

Validation:
- compare final provider payload with expected llama.cpp OpenAI-compatible shape
- force small context or long prompt and confirm dropped/truncated layers are recorded

### Phase 3 — `/inspector` modal UI — done enough for active use

Delivered:
- `static/js/inspector.js`
- `/inspector` slash command
- modal with tabs:
  - Prompt Stack
  - Tools
  - Compaction / Pruning
  - Provider Payload
  - Runtime
- trace list and refresh
- secondary popup for full content
- response/reasoning reveal controls

Remaining polish:
- make selected trace identity/label visible everywhere, especially before tab switching
- improve empty-state copy for internal traces that have provider messages but no prompt layers
- optional copy/export controls

Validation:
- `/inspector` opens modal
- latest trace loads
- tabs render without freezing on large prompts
- no dumps/tables in main UI
- full prompt opens in secondary popup and closing it returns to the inspector

### Phase 4 — prompt-bloat and tool-call tuning support — next major use

After inspector proves what is bloated:
- add agent prompt profile setting:
  - `full`
  - `compact`
  - `local_lean`
- verify disabled tools are truly omitted from schemas/prompt
- move Cookbook/email/UI conventions into relevant-tool conditional sections
- add token budget targets per prompt layer

### Phase 5 — polish

- optional “Open trace” link in message metrics popup if it stays subtle
- add export trace button if useful
- add diff between two traces if useful
- add warnings:
  - agent prompt > X tokens
  - schemas sent for disabled tools
  - system prompt dropped/truncated
  - research using different endpoint/model than chat

## Success criteria

Current status:
- `/inspector` opens one hidden dev modal with tabs.
- A normal chat turn shows prompt stack and provider payload summary.
- Provider response/reasoning/result are captured for current diagnosis.
- Internal auto-name and tidy-session traces are separated from user chat traces.
- No normal UI clutter.
- Full prompt popup shows content in actual order and is independently closable.
- Traces are cleaned at startup.

Still to verify/improve:
- Agent turn shows actual tools/schemas sent and disabled tools omitted/included status clearly.
- Long-context turn shows exact compaction/pruning decisions, including dropped/truncated messages.
- Incognito/nobody creates no traces and does not leak message content to regular logs.

## Decisions

- Slash command is `/inspector`, not `/poop`.
- Inspector is always available on this local fork.
- Traces are cleaned at startup.
- Full context is captured for normal non-incognito turns.
- Incognito/nobody turns are never traced; add a review item to ensure `logs/` also avoids message-content logging there.
- Inspector is read-only.
- Main UI uses clean key/value/cards/chips only — no table dumps, no JSON dumps.
- Full content appears in a secondary scrollable popup and preserves actual prompt/message order.
