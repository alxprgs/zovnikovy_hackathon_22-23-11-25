from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from server.routes.schemes import CreateSupply, UpdateSupplyStatus
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id
from server.core.notifications import create_notification

router = APIRouter(prefix="/supplies", tags=["Supplies"])


def _ensure_company_access(wh, current):
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этой компании.")


def _ensure_not_blocked_for_write(wh, current):
    if wh.get("blocked_at") and not current.get("is_root"):
        raise HTTPException(403, "Этот склад заблокирован.")


@router.post("/create")
async def create_supply(
    request: Request,
    data: CreateSupply,
    current=require_permission("supplies.create"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    item = await db["items"].find_one({"_id": oid(data.item_id), "warehouse_id": wh["_id"]})
    if not item:
        raise HTTPException(404, "Товар не найден на этом складе.")

    now = datetime.now(timezone.utc)
    doc = {
        "warehouse_id": wh["_id"],
        "item_id": item["_id"],
        "amount": data.amount,
        "expected_at": data.expected_at,
        "note": data.note,
        "status": "waiting",
        "overdue_notified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    _id = (await db["supplies"].insert_one(doc)).inserted_id

    await create_notification(
        db,
        company_id=wh["company_id"],
        warehouse_id=wh["_id"],
        supply_id=_id,
        item_id=item["_id"],
        ntype="supply_created",
        title="Создана поставка",
        message=f"Ожидается поставка «{item['name']}» ({doc['amount']} {item.get('unit','')}) к {doc['expected_at']}.",
        by_user_id=current["_id"],
    )

    return JSONResponse(
        {"ok": True, "supply": public_id({**doc, "_id": _id, "item_name": item.get("name")})}
    )


@router.get("/list/{warehouse_id}")
async def list_supplies(
    request: Request,
    warehouse_id: str,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "expected_at",
    order: int = 1,
    current=require_permission("supplies.update"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)

    q: Dict[str, Any] = {"warehouse_id": wh["_id"]}
    if status and status != "all":
        q["status"] = status

    cursor = db["supplies"].find(q)
    if sort in {"expected_at", "created_at", "updated_at", "amount", "status"}:
        cursor = cursor.sort(sort, order)

    supplies_raw = [s async for s in cursor]

    item_ids = list({s.get("item_id") for s in supplies_raw if s.get("item_id")})
    items_map: Dict[Any, Dict[str, Any]] = {}
    if item_ids:
        async for it in db["items"].find({"_id": {"$in": item_ids}}):
            items_map[it["_id"]] = it

    now = datetime.now(timezone.utc)
    out: List[Dict[str, Any]] = []

    for s in supplies_raw:
        item_doc = items_map.get(s.get("item_id"))
        item_name = item_doc.get("name") if item_doc else "—"

        exp = s.get("expected_at")
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        overdue = bool(exp and s.get("status") == "waiting" and exp < now)

        if overdue and not s.get("overdue_notified_at"):
            await db["supplies"].update_one({"_id": s["_id"]}, {"$set": {"overdue_notified_at": now}})
            await create_notification(
                db,
                company_id=wh["company_id"],
                warehouse_id=wh["_id"],
                supply_id=s["_id"],
                item_id=s.get("item_id"),
                ntype="supply_overdue",
                title="Просроченная поставка",
                message=f"Поставка «{item_name}» ожидалась {exp.isoformat() if exp else '—'}, статус waiting.",
            )

        doc = {**s, "item_name": item_name, "overdue": overdue}
        out.append(public_id(doc))

    if search:
        sl = search.lower()
        out = [x for x in out if sl in (x.get("item_name") or "").lower()]

    return JSONResponse({"ok": True, "supplies": out})


@router.post("/status")
async def update_supply_status(
    request: Request,
    data: UpdateSupplyStatus,
    current=require_permission("supplies.update"),
):
    db = request.app.state.mongo_db
    sup = await db["supplies"].find_one({"_id": oid(data.supply_id)})
    if not sup:
        raise HTTPException(404, "Поставка не найдена.")

    wh = await db["warehouses"].find_one({"_id": sup["warehouse_id"], "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    now = datetime.now(timezone.utc)
    await db["supplies"].update_one(
        {"_id": sup["_id"]},
        {"$set": {"status": data.status, "updated_at": now}},
    )

    item = await db["items"].find_one({"_id": sup["item_id"]})
    item_name = item.get("name") if item else "—"

    if data.status == "done":
        await db["items"].update_one(
            {"_id": sup["item_id"]},
            {"$inc": {"count": sup["amount"]}, "$set": {"updated_at": now}},
        )
        await db["history"].insert_one(
            {
                "item_id": sup["item_id"],
                "warehouse_id": sup["warehouse_id"],
                "type": "income",
                "amount": sup["amount"],
                "ts": now,
                "by_user_id": current["_id"],
                "note": "auto from supply",
            }
        )

    await create_notification(
        db,
        company_id=wh["company_id"],
        warehouse_id=wh["_id"],
        supply_id=sup["_id"],
        item_id=sup["item_id"],
        ntype="supply_status",
        title="Статус поставки обновлён",
        message=f"«{item_name}» → {data.status}",
        by_user_id=current["_id"],
    )

    return JSONResponse({"ok": True})
