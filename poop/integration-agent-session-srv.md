# Agent Session Server / pi / pi-collab Integration Notes

## Goal

Explore whether Odysseus can become a local AI homebase while still connecting to:

- `agent-session-srv`
- pi session trees
- pi-collab cross-session workflows
- existing voice/STT/TTS infrastructure

## Why this looks feasible

Odysseus already has concepts that map well:

- persistent chat sessions
- forkable sessions
- agent mode with tool harness
- tmux-backed model serve/download tasks
- endpoint registry for external services
- Deep Research jobs with status/resume UI

The session model appears more structured than a simple chat log, but the exact schema still needs inspection.

## Things to inspect

Session/chat backend:
- `routes/session_routes.py`
- `src/session_manager.py`
- `data/sessions.json`
- DB tables in `data/app.db`
- frontend session tree/fork UI in `static/js/sessions.js`

Agent loop/tooling:
- `src/agent_loop.py`
- `src/tool_implementations.py`
- `src/tool_schemas.py`
- `src/tool_index.py`

Task/process orchestration:
- `routes/cookbook_routes.py`
- `static/js/cookbookRunning.js`
- tmux session handling and logs under `/tmp/odysseus-tmux` and `logs/startup`

## Integration ideas

### 1. Endpoint-level integration first

Keep Odysseus as UI/homebase and register external services as endpoints:
- LLM endpoints
- STT/TTS endpoints
- maybe agent-session-srv as a tool/API endpoint

This is lowest risk because it uses existing ModelEndpoint/settings patterns.

### 2. Cross-session message bridge

Expose or consume a small event API:
- new message
- agent started/stopped
- tool call/result
- research started/done
- serve started/stopped

Could let pi-collab monitor or inject messages without owning Odysseus internals.

### 3. Session tree adapter

Map Odysseus session/fork structure to pi session trees.
Need inspect actual schema first.

### 4. tmux/process adapter

Odysseus already launches model serves via tmux. agent-session-srv/pi may be able to attach/adopt these sessions or consume their logs.

## Risks / unknowns

- Auth/owner scoping: tool calls and UI sessions may see different session sets.
- Odysseus logs are scattered: app logs, startup logs, tmux capture, DB/session state.
- Session identity might not be stable enough for external tree sync without an explicit adapter.
- Voice may be better handled by existing external servers rather than merged into Odysseus runtime.

## Next test plan

1. Map session storage and fork representation.
2. Identify the minimal API needed for cross-session messages.
3. Check whether agent-session-srv can be registered as a tool endpoint before deeper integration.
4. Decide if voice should integrate via OpenAI-compatible endpoint mode or agent-session-srv bridge.
