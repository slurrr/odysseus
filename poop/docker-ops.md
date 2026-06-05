# Docker / Container Ops for This Odysseus Fork

This repo is run with Docker Compose. The `odysseus` service is built from the repo, but most active source directories are bind-mounted into `/app`, so many Python/JS edits only need a container restart, not a full image rebuild.

## Current compose status

Validated after the upstream rebase:

```bash
docker compose config
```

Result: compose YAML is valid.

Current services:

```text
odysseus   app UI/API on 127.0.0.1:7000
chromadb   vector DB on 127.0.0.1:8100
searxng    search on 127.0.0.1:8080
ntfy       notifications on 127.0.0.1:8091
```

The app service requests GPU access through Compose device reservations.

## Important bind mounts

The app container bind-mounts active repo paths:

```text
app.py           -> /app/app.py
main.py          -> /app/main.py
src/             -> /app/src
routes/          -> /app/routes
static/          -> /app/static
scripts/         -> /app/scripts
data/            -> /app/data
logs/            -> /app/logs
~/models/hf      -> /app/.cache/huggingface
~/models/fastembed -> /app/.cache/fastembed
data/local       -> /app/.local
```

Implication:
- Python route/source changes usually need `docker compose restart odysseus`.
- Frontend JS/CSS changes usually need browser hard reload; if backend serves cached/static state oddly, restart app too.
- Dockerfile/dependency/apt/pip base-image changes need rebuild.

## Normal restart after source changes

From repo root:

```bash
docker compose restart odysseus
```

Then browser hard reload:

```text
Ctrl+Shift+R
```

Check status:

```bash
docker compose ps
```

Tail app logs:

```bash
docker compose logs -f --tail=120 odysseus
```

## Full rebuild after upstream sync or dependency changes

Use this when any of these changed:
- `Dockerfile`
- `requirements*.txt`
- package install logic
- system dependencies
- unexplained import/runtime errors after sync

```bash
docker compose build odysseus
docker compose up -d odysseus
```

If dependencies are very stale or Docker cache seems poisoned:

```bash
docker compose build --no-cache odysseus
docker compose up -d odysseus
```

## Start/stop the stack

Start everything:

```bash
docker compose up -d
```

Stop containers but keep volumes/data:

```bash
docker compose down
```

Do **not** use `--volumes` unless intentionally deleting Compose-managed data:

```bash
# dangerous / destructive for compose volumes
docker compose down --volumes
```

## After syncing `local/dev` with upstream

Recommended sequence:

```bash
# validate config first
docker compose config >/tmp/odysseus-compose-config.txt

# if only Python/JS/source changed
docker compose restart odysseus

# if Dockerfile/deps changed, or restart fails with import/dependency issues
docker compose build odysseus
docker compose up -d odysseus

# check health/logs
docker compose ps
docker compose logs --tail=120 odysseus
```

Browser:

```text
Ctrl+Shift+R
```

## llama.cpp/GGUF serving after restart

The app restart does not necessarily kill every Cookbook/tmux-launched model server, but if a serve card is stale, use Cookbook Stop/Restart or inspect tmux/logs.

Useful checks:

```bash
# app container health-ish check
curl -fsS http://127.0.0.1:7000/ >/dev/null && echo ok

# known llama-server endpoint, if running on 8001
docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/health

docker compose exec -u odysseus odysseus curl -fsS http://127.0.0.1:8001/v1/models

docker compose exec -u odysseus odysseus nvidia-smi
```

Startup logs for Cookbook serves:

```bash
ls -ltr logs/startup | tail
readlink -f logs/startup/latest.log
```

## Running clean and hacked branches at the same time

Usually avoid this. Use one running stack from `local/dev`.

If you intentionally need two stacks, give Compose a different project name and avoid port conflicts:

```bash
docker compose -p odysseus-dev up -d
```

But this repo's compose file publishes fixed localhost ports (`7000`, `8080`, `8091`, `8100`), so a second stack needs port edits or overrides.

## Quick recovery commands

Restart app only:

```bash
docker compose restart odysseus
```

Recreate app container without rebuilding image:

```bash
docker compose up -d --force-recreate odysseus
```

Rebuild/recreate app:

```bash
docker compose build odysseus && docker compose up -d odysseus
```

See recent app logs:

```bash
docker compose logs --tail=200 odysseus
```
