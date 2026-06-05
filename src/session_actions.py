"""
session_actions.py

Reusable session actions that can be called from both REST routes
and the task scheduler / builtin actions system.
"""

import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Names that indicate a throwaway/test session
_THROWAWAY_NAMES = {
    "test", "testing", "asdf", "asd", "hello", "hi", "hey",
    "yo", "sup", "hola", "hii", "hiii", "heyo",
    "foo", "bar", "baz", "tmp", "temp", "scratch", "untitled",
    "new chat", "delete", "remove", "junk", "trash", "xxx",
    "abc", "qwerty", "blah", "stuff", "whatever", "idk",
    "ok", "lol", "bruh", "hmm", "hm", "meh",
}
_THROWAWAY_MAX_MESSAGES = 4
# Event-triggered tidy can run immediately after a session is created, before
# the chat stream has persisted the first user/assistant messages. Never delete
# brand-new empty rows; otherwise a live chat can vanish while its request is
# still in flight.
_FRESH_EMPTY_SESSION_GRACE = timedelta(minutes=10)
_NEW_EMPTY_SESSION_GRACE = _FRESH_EMPTY_SESSION_GRACE


async def run_auto_sort(owner: str, skip_llm: bool = False, delete_throwaway: bool = True) -> str:
    """Run session cleanup + (optional) AI folder sort for the given owner.

    Args:
        owner: user whose sessions to process
        skip_llm: when True, do only Phase 1 (delete empty/throwaway sessions);
            skip Phase 2 (AI folder assignment). Used by the built-in daily
            background sweep so it never burns LLM tokens.
        delete_throwaway: when False, only empty/incognito sessions are deleted.

    Returns a human-readable summary of what was done.
    """
    from core.database import SessionLocal, Session as DbSession, ChatMessage as DbMsg
    from src.llm_core import llm_call_async
    from src.task_endpoint import resolve_task_endpoint
    try:
        from src import debug_trace as _trace
        _trace.begin_trace(
            f"task:tidy_sessions:{owner or 'all'}",
            mode="internal",
            owner=owner,
            trace_type="internal:tidy_sessions",
            label="Tidy chats",
        )
        _trace.add_event("tidy_started", {"owner": owner or "", "skip_llm": bool(skip_llm)})
    except Exception:
        _trace = None

    db = SessionLocal()
    try:
        # ── Phase 1: Delete empty/throwaway sessions ──
        deleted_empty = 0
        deleted_throwaway = 0

        rows = db.query(DbSession).filter(
            DbSession.archived == False,
            *([DbSession.owner == owner] if owner else []),
        ).all()
        if _trace is not None:
            _trace.add_event("tidy_scanned", {"count": len(rows)})

        for row in rows:
            if getattr(row, 'is_important', False):
                if _trace is not None:
                    _trace.add_event("tidy_kept", {"session_id": row.id, "name": row.name or "", "reason": "important"})
                continue
            created_at = row.created_at or row.updated_at or datetime.utcnow()
            is_fresh = (datetime.utcnow() - created_at) < _FRESH_EMPTY_SESSION_GRACE
            if (row.name or "").strip() == "Incognito":
                deleted_throwaway += 1
                if _trace is not None:
                    _trace.add_event("tidy_delete_candidate", {"session_id": row.id, "name": row.name or "", "reason": "incognito"})
                db.delete(row)
                continue

            reason = ""

            msg_count = db.query(DbMsg.id).filter(
                DbMsg.session_id == row.id
            ).limit(_THROWAWAY_MAX_MESSAGES + 1).count()
            created_at = getattr(row, "created_at", None)
            age = (datetime.utcnow() - created_at.replace(tzinfo=None)) if created_at else None
            if msg_count == 0 and age is not None and age < _NEW_EMPTY_SESSION_GRACE:
                if _trace is not None:
                    _trace.add_event("tidy_kept", {
                        "session_id": row.id,
                        "name": row.name or "",
                        "message_count": msg_count,
                        "reason": "new_empty_grace_period",
                        "age_seconds": round(age.total_seconds(), 2),
                    })
                continue
            should_delete = False

            if msg_count == 0:
                if is_fresh:
                    continue
                should_delete = True
                reason = "empty"
                deleted_empty += 1
            elif delete_throwaway and msg_count <= _THROWAWAY_MAX_MESSAGES:
                name = (row.name or "").strip().lower()
                first_msg = db.query(DbMsg.content).filter(
                    DbMsg.session_id == row.id, DbMsg.role == "user"
                ).order_by(DbMsg.timestamp).first()
                first_text = (first_msg[0] or "").strip().lower() if first_msg else ""
                assistant_count = db.query(DbMsg.id).filter(
                    DbMsg.session_id == row.id, DbMsg.role == "assistant"
                ).limit(1).count()

                if name in _THROWAWAY_NAMES or name.startswith("chat:") or first_text in _THROWAWAY_NAMES:
                    should_delete = True
                    reason = "throwaway_name_or_first_message"
                    deleted_throwaway += 1
                elif msg_count == 1 and assistant_count == 0:
                    should_delete = True
                    reason = "single_user_no_assistant"
                    deleted_throwaway += 1
                elif msg_count <= 4 and first_text and len(first_text.split()) <= 8 and len(first_text) <= 80:
                    # Short trivial chats — e.g. "write hi to a friend" → "Hi!"
                    should_delete = True
                    reason = "short_trivial_chat"
                    deleted_throwaway += 1
                else:
                    # Aggressive: total message text under 250 chars combined = trivial
                    msg_rows = db.query(DbMsg.content).filter(
                        DbMsg.session_id == row.id
                    ).all()
                    total_chars = sum(len(m[0] or "") for m in msg_rows)
                    if total_chars <= 250:
                        should_delete = True
                        reason = "small_total_text"
                        deleted_throwaway += 1

            if should_delete:
                if _trace is not None:
                    _trace.add_event("tidy_delete_candidate", {
                        "session_id": row.id,
                        "name": row.name or "",
                        "message_count": msg_count,
                        "reason": reason or "matched_cleanup_rule",
                    })
                db.delete(row)
            elif _trace is not None:
                _trace.add_event("tidy_kept", {
                    "session_id": row.id,
                    "name": row.name or "",
                    "message_count": msg_count,
                    "reason": "did_not_match_cleanup_rules",
                })

        if deleted_empty or deleted_throwaway:
            db.commit()
            logger.info(f"Auto-sort: deleted {deleted_empty} empty + {deleted_throwaway} throwaway sessions")

        # ── Phase 2: AI folder assignment ──
        remaining = db.query(DbSession).filter(
            DbSession.archived == False,
            *([DbSession.owner == owner] if owner else []),
        ).all()

        session_list = []
        for row in remaining:
            if row.name == "Incognito":
                continue
            session_list.append({
                "id": row.id,
                "name": row.name or "(unnamed)",
                "current_folder": row.folder,
            })

        if len(session_list) < 2:
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions. Too few remaining to sort."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list)})
                _trace.finish_trace("done")
            return result_msg

        # Background built-in sweep skips folder-sort to stay pure infra.
        if skip_llm:
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions (folder sort skipped)."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "folder_sort_skipped": True})
                _trace.finish_trace("done")
            return result_msg

        url, model, headers = resolve_task_endpoint()
        if not url:
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions. No model endpoint available for sorting."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "folder_sort_skipped": True, "reason": "no_endpoint"})
                _trace.finish_trace("done")
            return result_msg

        names_text = "\n".join(f'  "{s["id"][:8]}": "{s["name"]}"' for s in session_list)
        prompt = (
            "You are a session organizer. Group these chat sessions into folders by topic.\n\n"
            "Rules:\n"
            "- Be aggressive about grouping — put EVERY session in a folder\n"
            "- Use short folder names (2-4 words max)\n"
            "- Use the 8-char ID prefixes exactly as given\n"
            "- Output ONLY raw JSON, no markdown fences, no explanation\n\n"
            "Required JSON format:\n"
            '{"folders": {"Folder Name": ["id_prefix1", "id_prefix2"], "Other Folder": ["id_prefix3"]}}\n\n'
            f"Sessions (id_prefix: name):\n{{\n{names_text}\n}}"
        )

        try:
            # 16384 (was 4096): large folder JSON + reasoning-model thinking
            # overflowed 4096 and truncated the JSON, so it never parsed.
            raw = await llm_call_async(url, model, [{"role": "user", "content": prompt}],
                                       temperature=0.3, max_tokens=16384, headers=headers, timeout=120)
        except Exception as e:
            logger.warning(f"Auto-sort LLM call failed: {e}")
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions. Folder sort skipped (model unreachable)."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "folder_sort_skipped": True, "error": str(e)})
                _trace.finish_trace("done")
            return result_msg

        # Parse JSON from response
        text = raw.strip()
        result = None
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            pass
        if result is None:
            fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
            if fence_match:
                try:
                    result = json.loads(fence_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
        if result is None:
            brace_start = text.find('{')
            brace_end = text.rfind('}')
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    result = json.loads(text[brace_start:brace_end + 1])
                except json.JSONDecodeError:
                    pass
        if result is None:
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions. AI returned unparseable response."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "folder_sort_skipped": False, "reason": "unparseable_ai_response"})
                _trace.finish_trace("done")
            return result_msg

        folders = result.get("folders", {})
        if not folders:
            result_msg = f"Cleaned {deleted_empty + deleted_throwaway} sessions. No folder groupings found."
            if _trace is not None:
                _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "folder_sort_skipped": False, "reason": "no_folder_groupings"})
                _trace.finish_trace("done")
            return result_msg

        # Apply assignments
        id_prefix_map = {s["id"][:8]: s["id"] for s in session_list}
        updated = 0
        for folder_name, ids in folders.items():
            for sid_or_prefix in ids:
                full_id = None
                if sid_or_prefix in id_prefix_map.values():
                    full_id = sid_or_prefix
                else:
                    prefix = sid_or_prefix.rstrip(".").rstrip(" ")
                    if prefix in id_prefix_map:
                        full_id = id_prefix_map[prefix]
                    else:
                        for p, fid in id_prefix_map.items():
                            if fid.startswith(prefix) or prefix.startswith(p):
                                full_id = fid
                                break
                if full_id:
                    db_sess = db.query(DbSession).filter(DbSession.id == full_id).first()
                    if db_sess:
                        db_sess.folder = folder_name
                        db_sess.updated_at = datetime.utcnow()
                        updated += 1
        db.commit()

        folder_summary = ", ".join(f"{k} ({len(v)})" for k, v in folders.items())
        result_msg = f"Deleted {deleted_empty} empty + {deleted_throwaway} throwaway. Sorted {updated} sessions into: {folder_summary}"
        if _trace is not None:
            _trace.set_result({"message": result_msg, "deleted_empty": deleted_empty, "deleted_throwaway": deleted_throwaway, "remaining": len(session_list), "sorted": updated, "folders": folders})
            _trace.finish_trace("done")
        return result_msg

    except Exception as e:
        if _trace is not None:
            try:
                _trace.set_result({"error": str(e)})
                _trace.finish_trace("error")
            except Exception:
                pass
        raise

    finally:
        db.close()
