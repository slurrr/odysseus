# Poop Workspace Notes

This directory is for local development notes, repo maps, launch recipes, and bug forensics that are useful while hacking on this Odysseus fork but are not upstream-ready docs yet.

Keep notes concise and operational:
- what was observed
- what changed
- exact commands/paths/ports
- open bugs and next tests

Key files:
- `git-workflow.md` — procedure for keeping `main` as an upstream mirror while carrying `local/dev` hacks.
- `docker-ops.md` — how to restart/rebuild/manage the Docker Compose stack after edits or syncs.
- `repo-map.md` — high-level repo/runtime map for fresh sessions and compactions.
- `roadmap.md` — current local-dev priorities and watch items.
- `poop-inspector-spec.md` — `/inspector` trace design, implementation status, and next refinements.
- `system-prompt.md` / `tool-calling.md` — prompt/tool investigation notes.

Subdirectories:
- `serving/` — local model serving notes for vLLM, llama.cpp, endpoints, GPU/runtime issues.
