# Tool Calling / Structured Output Notes

## Goal

Review how Odysseus tools work and improve reliability for local quantized models.

The immediate issue: with the current small quantized local model, tool use mostly works but is brittle:
- model hallucinated a couple of tool calls in one turn
- one tool call failed
- a later turn succeeded as an API call
- success was not cleanly structured from the model side

This suggests the backend can execute useful actions, but the model/tool-call protocol may be too demanding or insufficiently constrained for this runtime.

## Why this matters

Tool reliability is a foundation for several other roadmap items:
- system prompt/instruction stack
- Deep Research
- voice-driven operation
- agent-session-srv/pi integration
- cross-session messages/actions
- Cookbook operations from chat

If tool calls are fragile, higher-level agent behavior will also be fragile.

## Things to understand

Likely relevant files:
- `src/agent_loop.py`
- `src/tool_schemas.py`
- `src/tool_implementations.py`
- `src/tool_index.py`
- `routes/skills_routes.py`
- `routes/task_routes.py`
- `routes/cookbook_routes.py`
- `static/js/chat.js`
- `static/js/assistant.js`

Questions:
- Is tool calling implemented via OpenAI native `tools` / `tool_calls`, JSON-mode prompting, or custom structured output parsing?
- Are schemas sent in full every turn, or selected/retrieved first?
- Is there a retry/repair path for malformed tool calls?
- Does the model get examples of correct tool-call structure?
- Are failed tool calls summarized back to the model in a way it can fix?
- Are tools grouped/routed, or does the model see too many choices at once?
- Does llama.cpp endpoint expose enough OpenAI-compatible tool-call behavior for this flow?
- Are tool calls validated before execution with clear errors?

## Constraints

Current local model is a smaller quantized model, and KV cache is being tested at q4.

Implications:
- do not assume frontier-model tool discipline
- minimize tool schema/token load
- prefer simple, repairable formats
- use narrow tool sets when possible
- avoid requiring perfect nested JSON on the first try
- preserve context for the actual task, not just tool descriptions

## Potential improvements

### 1. Tool router / staged tool selection

Instead of exposing all tools directly:
1. first ask model to choose a tool category or intent
2. then expose only a small schema set for that category

This may help quantized models by reducing schema clutter.

### 2. Schema simplification

For common local workflows, provide small wrapper tools with simple arguments rather than huge generic schemas.

Example categories:
- Cookbook: list models, serve model, stop model, check status
- Sessions: list/fork/rename/archive
- Research: start/cancel/status/open report
- Voice: transcribe/speak/status
- App API: keep as escape hatch, but not first choice

### 3. Structured-output repair loop

If model emits malformed tool JSON:
- do not immediately fail the user-visible turn
- feed back a concise validation error
- ask for only corrected JSON/tool call
- cap retries to avoid loops

### 4. Few-shot tool examples

Add short examples for the exact tool-call format expected by Odysseus/llama.cpp.

Especially useful if the endpoint does not provide native tool-call enforcement.

### 5. Tool result normalization

Return compact, model-friendly results:
- success/failure
- important IDs
- next suggested action
- avoid dumping huge raw JSON unless requested

### 6. Skills/procedures layer

For repeatable workflows, add skill-like procedures above raw tools:
- “serve a local GGUF safely”
- “adopt an existing tmux server”
- “start deep research using current model”
- “test STT endpoint”

This can reduce planning burden on the model.

### 7. Local-model profile

Introduce model/runtime-specific agent settings:
- smaller tool inventory
- lower max parallel tool attempts
- stricter JSON repair
- shorter schemas
- tool examples on
- lower temperature for tool-call turns

## KV cache note

q4 KV cache may be fine for chat quality, but tool-call syntax could be more sensitive than normal prose. Track whether malformed tool calls correlate with:
- q4 vs q8/f16 KV
- context length
- long schema/tool prompts
- temperature
- number of available tools
- llama.cpp parallel slots

## Desired outcome

A clear map of the tool pipeline plus a local-model-friendly tool mode:
- fewer hallucinated calls
- better malformed-call repair
- smaller schemas in context
- clearer tool errors
- reliable Cookbook/session/research actions from chat

No implementation yet; this is a roadmap item.
