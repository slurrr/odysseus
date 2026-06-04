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
    assert ": (live.status === 'error'" in source
    assert "? 'error'" in source
    assert "_saveTasks(localTasks);" in source
    assert "completedDeps.forEach(t => _refreshDepsAfterInstall(t));" in source


def test_local_windows_session_commands_use_local_powershell_log_dir():
    source = _read("static/js/cookbookRunning.js")

    assert "const host = task.remoteHost;" in source
    assert "host ? '$env:TEMP\\\\odysseus-sessions' : '$env:TEMP\\\\odysseus-tmux'" in source
    assert "return host ? `ssh ${pf}${host}" in source
    assert ": `powershell -Command \"${ps}\"`;" in source


def test_dep_install_success_recognized_from_exit_sentinel():
    """A pip dependency install reports success via the runner's exit-0
    sentinel / pip's "Successfully installed" line, not the HuggingFace
    download markers. The shared helper must key off those, so an install
    whose tmux pane is gone isn't misread as crashed."""
    source = _read("static/js/cookbookRunning.js")

    assert "function _depInstallSucceeded(output) {" in source
    assert "=== Process exited with code" in source
    assert "Successfully installed" in source


def test_session_gone_heuristic_honors_dep_install_success():
    """The reconnect loop's session-gone branch (download tasks need an HF
    marker to look successful) must also accept a finished dependency install,
    otherwise a clean pip install with no HF markers is marked crashed."""
    source = _read("static/js/cookbookRunning.js")

    assert "const depInstallSucceeded = !!task.payload?._dep && _depInstallSucceeded(lastOutput);" in source
    assert (
        "const looksSuccessful = depInstallSucceeded "
        "|| (task.type === 'download' ? downloadLooksSuccessful : serveLooksReady);"
    ) in source


def test_background_poll_recovers_done_for_stopped_dependency_install():
    """When the backend reports a finished dependency install as "stopped"
    (its pip package is never in the HF cache the dead-session check inspects),
    the reconciler must recover "done" from the retained output instead of
    downgrading the card to crashed."""
    source = _read("static/js/cookbookRunning.js")

    assert "const depDone = !!task.payload?._dep && _depInstallSucceeded(task.output);" in source
    assert "depDone ? 'done' : (task.type === 'download' ? 'crashed' : 'stopped')" in source


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
