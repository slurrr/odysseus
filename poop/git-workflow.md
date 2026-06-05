# Git Workflow for This Odysseus Fork

Goal: keep a clean mirror of upstream `main`, while still having one or more local hacked branches that can be rebased/salvaged as upstream moves fast.

## Remotes

```text
upstream = https://github.com/pewdiepie-archdaemon/odysseus.git
origin   = https://github.com/slurrr/odysseus.git
```

Rules:
- `upstream/main` is the real project.
- `origin/main` should mirror `upstream/main`.
- local hacked work lives on branches like `local/dev` in `origin`.
- never push to `upstream` directly.

Push to upstream is disabled locally:

```bash
git remote set-url --push upstream DISABLED
```

## Branches to keep

### `main`

Clean mirror branch.

Use for:
- tracking upstream
- comparing what changed
- resetting your fork's `main`

Do not hack here.

### `local/dev`

Main hacked branch.

Use for:
- local runtime fixes
- UI survival patches
- local docs/traces
- experiments you still want carried forward

This branch rebases onto `upstream/main` when upstream changes.

### Optional: `local/super-hacked`

Only create if `local/dev` needs to stay semi-stable and you want a messier scratch branch.

```bash
git switch -c local/super-hacked local/dev
git push -u origin local/super-hacked
```

### Optional preservation branch

Before a risky rebase, one temporary backup branch is enough:

```bash
git branch backup/local-dev-before-rebase-$(date +%Y-%m-%d) local/dev
git push origin backup/local-dev-before-rebase-$(date +%Y-%m-%d)
```

These are not part of the normal workflow. They can be deleted later after the rebase is known good.

## Do we need a separate `odysseus-clean` workspace?

No, not strictly.

A second worktree is convenient for inspecting clean upstream while `local/dev` is checked out, but it is optional. If it feels confusing, do not use it.

Without a clean worktree, just switch branches:

```bash
git switch main
# inspect clean upstream
git switch local/dev
# return to hacked branch
```

If using a clean worktree, treat it as read-only convenience:

```text
~/code/dev/odysseus        = local/dev hacked branch
~/code/dev/odysseus-clean  = main clean upstream mirror
```

## Normal sync procedure

### 1. Fetch everything

```bash
git fetch upstream
git fetch origin
```

### 2. Update clean `main` to upstream

Make local `main` exactly match upstream:

```bash
git switch main
git reset --hard upstream/main
```

Update your fork's `main` to match too:

```bash
git push --force-with-lease origin main
```

This is safe only because `main` is treated as a mirror, not a hacking branch.

### 3. Rebase hacked branch onto upstream

```bash
git switch local/dev
git rebase upstream/main
```

If there are no conflicts:

```bash
git push --force-with-lease origin local/dev
```

If there are conflicts:

```bash
git status
# edit conflicted files
rg -n '<<<<<<<|=======|>>>>>>>'
git add <resolved-files>
git rebase --continue
```

Repeat until done, then:

```bash
git push --force-with-lease origin local/dev
```

## Conflict strategy

Default posture:

1. Prefer upstream structure and security fixes.
2. Re-apply only local changes that still matter.
3. Keep local runtime fixes that unblock this workstation.
4. Keep local docs/traces under `poop/` unless intentionally dropping them.
5. Avoid large UI rewrites while upstream UI is churning.

Think of `local/dev` as a patch stack on top of upstream:

```text
upstream/main
  + local runtime fixes
  + local docs/traces
  + local debug helpers
  + local UI survival patches
= local/dev
```

## If a rebase gets ugly

Abort safely:

```bash
git rebase --abort
```

Then either try again later, or make a fresh branch from upstream and cherry-pick only wanted commits:

```bash
git switch -c local/dev-next upstream/main
git cherry-pick <commit-you-want>
```

If `local/dev-next` becomes the new working branch:

```bash
git branch -m local/dev local/dev-old
git branch -m local/dev-next local/dev
git push --force-with-lease origin local/dev
```

## Current recommended minimal setup

Keep only these as active concepts:

```text
main       clean mirror of upstream/main
local/dev  normal hacked branch
local/super-hacked optional chaos branch if needed
```

Everything else is temporary backup/reference and can be deleted once no longer useful.
