from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from server.core.functions.permissions import require_permission
from server.core.db_utils import public_id

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary(request: Request, current=require_permission("warehouses.update")):
    db = request.app.state.mongo_db

    company_q: Dict[str, Any] = {}
    if not current.get("is_root"):
        company_q = {"company_id": current["company_id"]}

    wh_q = {**company_q, "deleted_at": None}
    warehouses = [w async for w in db["warehouses"].find(wh_q)]
    wh_ids = [w["_id"] for w in warehouses]
    wh_map = {w["_id"]: w for w in warehouses}

    items_q = (
        {"warehouse_id": {"$in": wh_ids}, "deleted_at": None}
        if wh_ids
        else {"_id": {"$exists": False}}
    )
    total_items = await db["items"].count_documents(items_q)

    low_items = 0
    categories: Dict[str, int] = {}
    total_stock = 0

    async for it in db["items"].find(items_q):
        total_stock += int(it.get("count", 0))
        categories[it.get("category", "other")] = categories.get(it.get("category", "other"), 0) + 1

        wh = wh_map.get(it["warehouse_id"], {})
        low_limit = it.get("low_limit")
        if low_limit is None:
            low_limit = wh.get("low_stock_default", 1)
        if int(it.get("count", 0)) <= int(low_limit):
            low_items += 1

    supplies_q = (
        {"warehouse_id": {"$in": wh_ids}}
        if wh_ids
        else {"_id": {"$exists": False}}
    )

    waiting_supplies = await db["supplies"].count_documents({**supplies_q, "status": "waiting"})
    done_supplies = await db["supplies"].count_documents({**supplies_q, "status": "done"})
    canceled_supplies = await db["supplies"].count_documents({**supplies_q, "status": "canceled"})

    now = datetime.now(timezone.utc)
    overdue_supplies = 0
    upcoming_raw: List[Dict[str, Any]] = []

    cursor = db["supplies"].find({**supplies_q, "status": "waiting"}).sort("expected_at", 1).limit(5)
    async for s in cursor:
        exp = s.get("expected_at")
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp < now:
            overdue_supplies += 1
        upcoming_raw.append(s)

    item_ids = list({s.get("item_id") for s in upcoming_raw if s.get("item_id")})
    items_map: Dict[Any, str] = {}
    if item_ids:
        async for it in db["items"].find({"_id": {"$in": item_ids}}):
            items_map[it["_id"]] = it.get("name", "—")

    upcoming = [
        public_id(
            {
                **s,
                "item_name": items_map.get(s.get("item_id"), "—"),
                "overdue": bool(
                    s.get("expected_at")
                    and s["expected_at"].replace(tzinfo=timezone.utc) < now
                ),
            }
        )
        for s in upcoming_raw
    ]

    return JSONResponse(
        {
            "ok": True,
            "summary": {
                "warehouses": len(warehouses),
                "total_items": total_items,
                "low_items": low_items,
                "total_stock": total_stock,
                "categories": categories,
                "supplies": {
                    "waiting": waiting_supplies,
                    "done": done_supplies,
                    "canceled": canceled_supplies,
                    "overdue": overdue_supplies,
                },
                "upcoming_supplies": upcoming,
            },
        }
    )
