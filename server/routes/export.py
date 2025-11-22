from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from server.core.functions.permissions import require_permission
from server.core.db_utils import oid

router = APIRouter(prefix="/export", tags=["Export"])


def _stream_csv(filename: str, header: List[str], rows: List[List[Any]]):
    def gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for r in rows:
            writer.writerow(r)
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        gen(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _iso(dt):
    if not dt:
        return ""
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@router.get("/items/{warehouse_id}")
async def export_items(request: Request, warehouse_id: str, current=require_permission("items.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этой компании.")

    rows: List[List[Any]] = []
    async for i in db["items"].find({"warehouse_id": wh["_id"], "deleted_at": None}):
        low = i.get("low_limit")
        if low is None:
            low = wh.get("low_stock_default", 1)
        rows.append(
            [
                i.get("name"),
                i.get("category"),
                i.get("unit"),
                i.get("count"),
                low,
                _iso(i.get("created_at")),
                _iso(i.get("updated_at")),
            ]
        )

    header = ["name", "category", "unit", "count", "low_limit", "created_at", "updated_at"]
    return _stream_csv(f"items_{warehouse_id}.csv", header, rows)


@router.get("/supplies/{warehouse_id}")
async def export_supplies(request: Request, warehouse_id: str, current=require_permission("supplies.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этой компании.")

    supplies = [s async for s in db["supplies"].find({"warehouse_id": wh["_id"]})]

    item_ids = list({s.get("item_id") for s in supplies if s.get("item_id")})
    items_map: Dict[Any, str] = {}
    if item_ids:
        async for it in db["items"].find({"_id": {"$in": item_ids}}):
            items_map[it["_id"]] = it.get("name", "—")

    now = datetime.now(timezone.utc)
    rows: List[List[Any]] = []
    for s in supplies:
        exp = s.get("expected_at")
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        overdue = bool(exp and s.get("status") == "waiting" and exp < now)
        rows.append(
            [
                items_map.get(s.get("item_id"), "—"),
                s.get("amount"),
                _iso(exp),
                s.get("status"),
                s.get("note") or "",
                "yes" if overdue else "no",
                _iso(s.get("created_at")),
                _iso(s.get("updated_at")),
            ]
        )

    header = ["item_name", "amount", "expected_at", "status", "note", "overdue", "created_at", "updated_at"]
    return _stream_csv(f"supplies_{warehouse_id}.csv", header, rows)


@router.get("/history/{warehouse_id}")
async def export_history(request: Request, warehouse_id: str, current=require_permission("items.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этой компании.")

    hist = [h async for h in db["history"].find({"warehouse_id": wh["_id"]}).sort("ts", -1)]

    item_ids = list({h.get("item_id") for h in hist if h.get("item_id")})
    items_map: Dict[Any, str] = {}
    if item_ids:
        async for it in db["items"].find({"_id": {"$in": item_ids}}):
            items_map[it["_id"]] = it.get("name", "—")

    rows = [
        [
            items_map.get(h.get("item_id"), "—"),
            h.get("type"),
            h.get("amount"),
            _iso(h.get("ts")),
            h.get("note") or "",
            str(h.get("by_user_id") or ""),
        ]
        for h in hist
    ]

    header = ["item_name", "type", "amount", "ts", "note", "by_user_id"]
    return _stream_csv(f"history_{warehouse_id}.csv", header, rows)