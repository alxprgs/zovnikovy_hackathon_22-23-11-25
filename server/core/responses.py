from __future__ import annotations
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional

def ok(data: Optional[Dict[str, Any]] = None, status_code: int = 200):
    payload = {"ok": True}
    if data:
        payload.update(data)
    return JSONResponse(payload, status_code=status_code)

def err(msg: str, status_code: int = 400, **extra):
    payload = {"ok": False, "error": msg}
    payload.update(extra)
    return JSONResponse(payload, status_code=status_code)
