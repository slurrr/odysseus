"""Local /inspector diagnostic routes."""
from fastapi import APIRouter, Query, HTTPException

from src.debug_trace import list_traces, get_trace, clear_traces, TRACE_ROOT


def setup_inspector_routes() -> APIRouter:
    router = APIRouter(prefix="/api/inspector", tags=["inspector"])

    @router.get("/status")
    async def status():
        return {"available": True, "trace_root": str(TRACE_ROOT)}

    @router.get("/traces")
    async def traces(session_id: str = "", limit: int = Query(20, ge=1, le=100)):
        return {"traces": list_traces(session_id=session_id or None, limit=limit)}

    @router.get("/traces/{trace_id}")
    async def trace(trace_id: str):
        data = get_trace(trace_id)
        if not data:
            raise HTTPException(404, "Trace not found")
        return data

    @router.delete("/traces")
    async def clear():
        clear_traces()
        return {"ok": True}

    return router
