# Odysseus Repo Map

Local orientation map for agent handoffs/compactions. Keep this high-level and update when major flows move.

## Runtime shape
- `docker-compose.yml` runs the main `odysseus` FastAPI app plus `chromadb`, `searxng`, `ntfy`.
- Dev mounts currently overlay `app.py`, `main.py`, `src/`, `routes/`, `static/`, `scripts/`, `data/`, `logs/` into `/app`.
- App entry: `app.py` builds the FastAPI app, managers, route registrations, startup lifecycle.
- CLI/service entry: `main.py` / `docker/entrypoint.sh`.
- Persistent runtime state: `data/` and `logs/`.

## Backend layout
- `app.py` — app construction, middleware, route registration, startup/shutdown.
- `core/` — database/auth/session primitives.
  - `core/database.py` SQLAlchemy models / `SessionLocal`.
  - `core/session_manager.py` cached session manager + DB sync.
  - `core/auth.py` auth config/session-cookie backend.
- `routes/` — FastAPI route modules, usually `setup_*_routes(...)` factories registered in `app.py`.
  - `routes/chat_routes.py` `/api/chat_stream`, `/api/chat`, stream lifecycle, mode gates.
  - `routes/chat_helpers.py` shared chat context/preset/auto-name/finalize helpers.
  - `routes/session_routes.py` sessions/history/rename/fork/archive/delete.
  - `routes/model_routes.py` model endpoints, `/api/models`, `/api/default-chat`.
  - `routes/cookbook_routes.py` model download/serve/tmux/runtime endpoints.
  - `routes/inspector_routes.py` `/api/inspector/*` diagnostic trace API.
- `src/` — service/business logic.
  - `src/llm_core.py` provider calls and streaming parser/fallbacks.
  - `src/debug_trace.py` file-backed inspector traces in `data/debug/inspector_traces`.
  - `src/chat_processor.py` context preface construction.
  - `src/context_compactor.py` context compaction/trimming.
  - `src/agent_loop.py` agent/tool loop.
  - `src/agent_runs.py` detached SSE replay buffers.
  - `src/session_actions.py` chat tidy/folder sort.
  - `src/builtin_actions.py` scheduled task action implementations.
  - `src/task_scheduler.py` scheduled/event task runner.
  - `src/endpoint_resolver.py`, `src/task_endpoint.py` endpoint/model selection helpers.

## Frontend layout
- `static/index.html` main shell.
- `static/js/chat.js` send/stream/render orchestration.
- `static/js/sessions.js` sidebar sessions, selecting/loading history, model picker integration.
- `static/js/modelPicker.js` chat input model picker.
- `static/js/inspector.js` `/inspector` modal.
- `static/js/cookbook*.js` Cookbook UI; `cookbookRunning.js` Running tab cards/actions.
- `static/js/slashCommands.js` slash command registry, including `/inspector`.
- `static/style.css` global UI styles.

## Chat request path
1. User sends from `static/js/chat.js` to `POST /api/chat_stream`.
2. `routes/chat_routes.py` parses form/body, verifies owner/model/privileges, starts user trace.
3. `routes/chat_helpers.build_chat_context(...)` applies preset, memory/RAG/web/docs/skills, compaction/trimming, records prompt/context trace.
4. Normal chat calls `src/llm_core.stream_llm_with_fallback(...)`; agent mode calls `src/agent_loop.py` then provider calls through `src/llm_core.py`.
5. `src/llm_core.py` records provider payload/final messages and now response/reasoning/result.
6. `routes/chat_helpers.finalize_chat_response(...)` persists messages, usage, webhooks, and schedules `auto_name_session(...)` when needed.
7. `auto_name_session(...)` now creates a separate `internal:auto_name` trace.

## Session/UI history path
- Session list: `GET /api/sessions` from `routes/session_routes.py` + `SessionManager.get_sessions_for_user(...)`.
- History: `GET /api/history/{sid}` from `routes/session_routes.py`.
- UI load/select: `static/js/sessions.js::loadSessions()` and `selectSession()`.
- Rename: `PATCH /api/session/{sid}` or `session_manager.update_session_name(...)`; frontend may need `loadSessions()`/history refresh to show it.

## Inspector
- Trace root: `data/debug/inspector_traces`.
- Cleanup: `src.app_initializer.initialize_managers()` calls `debug_trace.startup_cleanup()` on app startup.
- API: `routes/inspector_routes.py`.
- UI: `static/js/inspector.js` via `/inspector` in `static/js/slashCommands.js`.
- Trace types currently used:
  - `user_chat`
  - `internal:auto_name`
  - `internal:tidy_sessions`
- Incognito/nobody should not trace.

## Cookbook serving
- Main backend: `routes/cookbook_routes.py`, helpers in `routes/cookbook_helpers.py`.
- Running UI: `static/js/cookbookRunning.js`.
- State: `data/cookbook_state.json`.
- Startup logs: `logs/startup/*.log`.
- llama.cpp build currently lives inside container at `/app/llama.cpp` unless persisted; recreating the container can force rebuild.

## Tidy/task path
- Event creation fires `src.event_bus.fire_event("session_created", owner)` from session creation.
- Task runner: `src/task_scheduler.py`.
- Built-in action: `src/builtin_actions.py::action_tidy_sessions`.
- Tidy logic: `src/session_actions.py::run_auto_sort`.
- Important guard: tidy now has a grace period for brand-new empty sessions so event-triggered cleanup cannot delete a chat before first stream persistence.

## Common diagnostics
```bash
docker compose logs -f odysseus
docker compose exec -T odysseus python -m py_compile routes/chat_routes.py routes/chat_helpers.py src/llm_core.py
find data/debug/inspector_traces -type f -printf '%T@ %p\n' | sort -nr | head
sqlite3 data/app.db '.tables'
```
