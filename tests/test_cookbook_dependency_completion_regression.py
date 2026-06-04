from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_backend_status_treats_download_exit_zero_as_completed():
    source = _read("routes/cookbook_routes.py")

    assert "exit_match = re.search(r\"=== process exited with code\\s+(-?\\d+)\"" in source
    assert "elif has_exit and task_type == \"download\":" in source
    assert "status = \"completed\" if exit_code == 0 else \"error\"" in source


def test_background_status_poll_reconciles_into_local_tasks():
    source = _read("static/js/cookbookRunning.js")

    assert "const statusById = new Map(tasks.map(t => [t.session_id, t]));" in source
    assert "const nextStatus = live.status === 'completed'" in source
    assert "? 'done'" in source
    assert ": (live.status === 'error' ? 'error' : null);" in source
    assert "_saveTasks(localTasks);" in source
    assert "completedDeps.forEach(t => _refreshDepsAfterInstall(t));" in source


def test_dependency_install_payload_keeps_env_path_for_refresh():
    source = _read("static/js/cookbook.js")

    assert "env_path: _envState.envPath || ''" in source


def test_model_serve_writes_durable_startup_log():
    source = _read("routes/cookbook_routes.py")

    assert 'Path(BASE_DIR) / "logs" / "startup"' in source
    assert 'ODYSSEUS_STARTUP_ALL_LOG="$ODYSSEUS_STARTUP_DIR/all.log"' in source
    assert 'ODYSSEUS_STARTUP_INDEX="$ODYSSEUS_STARTUP_DIR/index.log"' in source
    assert 'latest.log' in source
    assert 'exec > >(tee -a "$ODYSSEUS_STARTUP_LOG" "$ODYSSEUS_STARTUP_ALL_LOG") 2>&1' in source
    assert 'echo "[odysseus] startup log: $ODYSSEUS_STARTUP_DISPLAY_LOG"' in source
    assert '"log_path": startup_log_path' in source


def test_running_task_persists_startup_log_path():
    source = _read("static/js/cookbookRunning.js")

    assert "log_path: data.log_path || undefined" in source
    assert "task.payload.log_path = live.log_path;" in source
    assert "Copy startup log" in source


def test_odysseus_logs_discovers_startup_logs():
    source = _read("scripts/odysseus-logs")

    assert '_STARTUP_LOGS = _APP_LOGS / "startup"' in source
    assert "(_STARTUP_LOGS, _APP_LOGS, _TMUX_LOGS)" in source


def test_local_dependency_probe_refreshes_user_site_visibility():
    source = _read("routes/shell_routes.py")

    assert "importlib.invalidate_caches()" in source
    assert "user_site = site.getusersitepackages()" in source
    assert "if user_site and os.path.isdir(user_site) and user_site not in sys.path:" in source
