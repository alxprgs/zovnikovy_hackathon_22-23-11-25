from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Any, Dict

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/list")
async def list_notifications(
    request: Request,
    unread_only: bool = False,
    limit: int = 50,
    current=require_permission("warehouses.update"),
):
    db = request.app.state.mongo_db
    q: Dict[str, Any] = {}
    if not current.get("is_root"):
        q["company_id"] = current["company_id"]
    if unread_only:
        q["read"] = False

    cursor = db["notifications"].find(q).sort("created_at", -1).limit(limit)
    items = [public_id(x) async for x in cursor]
    return JSONResponse({"ok": True, "notifications": items})


@router.post("/read/{notification_id}")
async def mark_notification_read(
    request: Request,
    notification_id: str,
    current=require_permission("warehouses.update"),
):
    db = request.app.state.mongo_db
    n = await db["notifications"].find_one({"_id": oid(notification_id)})
    if not n:
        raise HTTPException(404, "Уведомление не найдено.")
    if not current.get("is_root") and n.get("company_id") != current.get("company_id"):
        raise HTTPException(403, "У вас нет доступа к этой компании.")

    now = datetime.now(timezone.utc)
    await db["notifications"].update_one(
        {"_id": n["_id"]},
        {"$set": {"read": True, "read_at": now, "read_by_user_id": current["_id"]}},
    )
    return JSONResponse({"ok": True})