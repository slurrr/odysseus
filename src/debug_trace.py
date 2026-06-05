"""Local diagnostic trace capture for the /inspector modal.

This is intentionally lightweight and file-backed for the dev fork. Traces are
runtime diagnostics, not durable user data: app startup clears them.
"""
from __future__ import annotations

import contextvars
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from src.constants import DATA_DIR
from src.model_context import estimate_tokens

TRACE_ROOT = Path(DATA_DIR) / "debug" / "inspector_traces"
_current_trace: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("inspector_trace_id", default=None)
_MAX_GLOBAL_TRACES = 50
_MAX_PER_SESSION = 20


def startup_cleanup() -> None:
    """Delete old inspector traces on application startup/import."""
    try:
        shutil.rmtree(TRACE_ROOT, ignore_errors=True)
        TRACE_ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _now() -> float:
    return time.time()


def _safe_id(value: str) -> str:
    value = str(value or "").strip() or "unknown"
    return "".join(ch for ch in value if ch.isalnum() or ch in "-_.")[:160] or "unknown"


def _trace_path(trace_id: str) -> Optional[Path]:
    if not trace_id:
        return None
    for p in TRACE_ROOT.glob(f"*/{_safe_id(trace_id)}.json"):
        return p
    return None


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune() -> None:
    try:
        paths = sorted(TRACE_ROOT.glob("*/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in paths[_MAX_GLOBAL_TRACES:]:
            p.unlink(missing_ok=True)
        for sess_dir in TRACE_ROOT.iterdir():
            if not sess_dir.is_dir():
                continue
            sess_paths = sorted(sess_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for p in sess_paths[_MAX_PER_SESSION:]:
                p.unlink(missing_ok=True)
    except Exception:
        pass


def begin_trace(
    session_id: str,
    mode: str = "chat",
    owner: Optional[str] = None,
    *,
    incognito: bool = False,
    trace_type: str = "user_chat",
    label: str = "",
    parent_trace_id: Optional[str] = None,
) -> Optional[str]:
    """Start a trace unless this is incognito/nobody."""
    if incognito or (owner or "").strip().lower() == "nobody":
        _current_trace.set(None)
        return None
    TRACE_ROOT.mkdir(parents=True, exist_ok=True)
    trace_id = str(uuid.uuid4())
    data = {
        "trace_id": trace_id,
        "session_id": session_id,
        "turn_id": trace_id,
        "created_at": _now(),
        "updated_at": _now(),
        "owner": owner or "",
        "mode": mode or "chat",
        "trace_type": trace_type or "user_chat",
        "label": label or (trace_type or "Chat"),
        "parent_trace_id": parent_trace_id or "",
        "internal": bool(str(trace_type or "").startswith("internal")),
        "layers": [],
        "tools": {"events": []},
        "context": {},
        "provider_payload": {},
        "events": [],
        "status": "running",
    }
    _write(TRACE_ROOT / _safe_id(session_id) / f"{trace_id}.json", data)
    _current_trace.set(trace_id)
    _prune()
    return trace_id


def current_trace_id() -> Optional[str]:
    return _current_trace.get()


def set_current_trace(trace_id: Optional[str]) -> None:
    _current_trace.set(trace_id)


def _mutate(fn) -> None:
    trace_id = current_trace_id()
    if not trace_id:
        return
    path = _trace_path(trace_id)
    if not path:
        return
    data = _read(path)
    if not data:
        return
    try:
        fn(data)
        data["updated_at"] = _now()
        _write(path, data)
    except Exception:
        pass


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return "" if content is None else str(content)


def layer_from_message(name: str, msg: dict, *, source: str = "", status: str = "included") -> dict:
    content = _text_content(msg.get("content"))
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "role": msg.get("role", ""),
        "source": source,
        "trusted": not (msg.get("metadata") or {}).get("trusted") is False,
        "tokens": estimate_tokens([msg]),
        "chars": len(content),
        "status": status,
        "content": content,
    }


def add_layer(layer: dict) -> None:
    def op(data):
        data.setdefault("layers", []).append(layer)
    _mutate(op)


def set_context(info: dict) -> None:
    def op(data):
        data.setdefault("context", {}).update(info or {})
    _mutate(op)


def set_endpoint(info: dict) -> None:
    def op(data):
        data.setdefault("endpoint", {}).update(info or {})
    _mutate(op)


def set_preset(info: dict) -> None:
    def op(data):
        data.setdefault("preset", {}).update(info or {})
    _mutate(op)


def set_tools(info: dict) -> None:
    def op(data):
        data.setdefault("tools", {}).update(info or {})
    _mutate(op)


def add_tool_event(event: dict) -> None:
    def op(data):
        data.setdefault("tools", {}).setdefault("events", []).append(event or {})
    _mutate(op)


def set_provider_payload(info: dict) -> None:
    def op(data):
        data.setdefault("provider_payload", {}).update(info or {})
    _mutate(op)


def add_event(event_type: str, info: Optional[dict] = None) -> None:
    def op(data):
        data.setdefault("events", []).append({
            "ts": _now(),
            "type": event_type,
            **(info or {}),
        })
    _mutate(op)


def set_result(info: dict) -> None:
    def op(data):
        data.setdefault("result", {}).update(info or {})
    _mutate(op)


def set_final_messages(messages: list[dict], *, label: str = "final_messages") -> None:
    simple = []
    for i, m in enumerate(messages or []):
        content = _text_content(m.get("content"))
        simple.append({
            "index": i + 1,
            "role": m.get("role", ""),
            "tokens": estimate_tokens([m]),
            "chars": len(content),
            "has_tool_calls": bool(m.get("tool_calls")),
            "content": content,
        })
    def op(data):
        data[label] = simple
    _mutate(op)


def finish_trace(status: str = "done") -> None:
    def op(data):
        data["status"] = status
        data["finished_at"] = _now()
    _mutate(op)


def list_traces(session_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    root = TRACE_ROOT / _safe_id(session_id) if session_id else TRACE_ROOT
    paths = list(root.glob("*.json")) if session_id else list(TRACE_ROOT.glob("*/*.json"))
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in paths[: max(1, min(int(limit or 20), 100))]:
        d = _read(p)
        if not d:
            continue
        out.append({
            "trace_id": d.get("trace_id"),
            "session_id": d.get("session_id"),
            "created_at": d.get("created_at"),
            "mode": d.get("mode"),
            "trace_type": d.get("trace_type") or "user_chat",
            "label": d.get("label") or d.get("mode") or "Trace",
            "internal": bool(d.get("internal")),
            "parent_trace_id": d.get("parent_trace_id") or "",
            "status": d.get("status"),
            "model": (d.get("endpoint") or {}).get("model"),
            "tokens": (d.get("context") or {}).get("tokens_after_trim") or (d.get("context") or {}).get("tokens_after_compaction") or (d.get("context") or {}).get("tokens_before_compaction"),
            "context_length": (d.get("context") or {}).get("context_length"),
            "tools_sent": (d.get("tools") or {}).get("schema_count"),
            "compacted": (d.get("context") or {}).get("compacted"),
            "trimmed": (d.get("context") or {}).get("trimmed"),
        })
    return out


def get_trace(trace_id: str) -> Optional[dict]:
    path = _trace_path(trace_id)
    return _read(path) if path else None


def clear_traces() -> None:
    startup_cleanup()
