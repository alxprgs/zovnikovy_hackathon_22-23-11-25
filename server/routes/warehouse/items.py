from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from server.routes.schemes import CreateItem, UpdateItem, ItemOp
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id
from server.core.mailer import send_low_stock_email
from server.core.notifications import create_notification

router = APIRouter(prefix="/items", tags=["Items"])


def _ensure_company_access(wh, current):
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этой компании.")


def _ensure_not_blocked_for_write(wh, current):
    if wh.get("blocked_at") and not current.get("is_root"):
        raise HTTPException(403, "Этот склад заблокирован.")


async def _check_low_stock(db, item: Dict[str, Any], warehouse: Dict[str, Any], *, company_id, by_user_id):
    low_limit = item.get("low_limit")
    if low_limit is None:
        low_limit = warehouse.get("low_stock_default", 1)

    now = datetime.now(timezone.utc)

    if item["count"] <= low_limit:
        if not item.get("low_notified_at"):
            await db["items"].update_one(
                {"_id": item["_id"]},
                {"$set": {"low_notified_at": now}}
            )

            if warehouse.get("notification_emails"):
                await send_low_stock_email(
                    request_app=None,
                    to_list=warehouse["notification_emails"],
                    item_name=item["name"],
                    count=item["count"],
                    low_limit=low_limit,
                    warehouse_name=warehouse["name"],
                )

            await create_notification(
                db,
                company_id=company_id,
                warehouse_id=warehouse["_id"],
                item_id=item["_id"],
                ntype="low_stock",
                title=f"Низкий остаток: {item['name']}",
                message=f"На складе «{warehouse['name']}» осталось {item['count']} {item.get('unit','')}. Порог: {low_limit}.",
                by_user_id=by_user_id,
            )
    else:
        if item.get("low_notified_at"):
            await db["items"].update_one(
                {"_id": item["_id"]},
                {"$set": {"low_notified_at": None}}
            )


@router.post("/create")
async def create_item(request: Request, data: CreateItem, current=require_permission("items.create")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    now = datetime.now(timezone.utc)
    doc = {
        "warehouse_id": wh["_id"],
        "name": data.name,
        "category": data.category,
        "unit": data.unit,
        "count": data.count,
        "low_limit": data.low_limit,
        "low_notified_at": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _id = (await db["items"].insert_one(doc)).inserted_id

    await db["history"].insert_one(
        {
            "item_id": _id,
            "warehouse_id": wh["_id"],
            "type": "income" if data.count > 0 else "create",
            "amount": data.count,
            "ts": now,
            "by_user_id": current["_id"],
        }
    )

    item_doc = {**doc, "_id": _id}
    await _check_low_stock(db, item_doc, wh, company_id=wh["company_id"], by_user_id=current["_id"])

    return JSONResponse({"ok": True, "item": public_id(item_doc)}, status_code=200)


@router.get("/list/{warehouse_id}")
async def list_items(
    request: Request,
    warehouse_id: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    low_only: bool = False,
    sort: str = "name",
    order: int = 1,
    current=require_permission("items.update"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)

    q: Dict[str, Any] = {"warehouse_id": wh["_id"], "deleted_at": None}
    if search:
        q["name"] = {"$regex": search, "$options": "i"}
    if category:
        q["category"] = category

    cursor = db["items"].find(q)
    if sort in {"name", "count", "category", "created_at", "updated_at"}:
        cursor = cursor.sort(sort, order)

    items = [public_id(i) async for i in cursor]

    if low_only:
        default_low = wh.get("low_stock_default", 1)

        def is_low(i):
            low = i.get("low_limit")
            if low is None:
                low = default_low
            return i.get("count", 0) <= low

        items = [i for i in items if is_low(i)]

    return JSONResponse({"ok": True, "items": items}, status_code=200)


@router.post("/update")
async def update_item(request: Request, data: UpdateItem, current=require_permission("items.update")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Товар не найден.")

    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"], "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    upd = {k: v for k, v in data.model_dump(exclude={"item_id"}).items() if v is not None}
    upd["updated_at"] = datetime.now(timezone.utc)
    await db["items"].update_one({"_id": item["_id"]}, {"$set": upd})

    item2 = await db["items"].find_one({"_id": item["_id"]})
    await _check_low_stock(db, item2, wh, company_id=wh["company_id"], by_user_id=current["_id"])

    return JSONResponse({"ok": True}, status_code=200)


@router.post("/income")
async def income(request: Request, data: ItemOp, current=require_permission("items.op")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Товар не найден.")

    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"], "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    now = datetime.now(timezone.utc)
    await db["items"].update_one(
        {"_id": item["_id"]},
        {"$inc": {"count": data.amount}, "$set": {"updated_at": now}},
    )
    await db["history"].insert_one(
        {
            "item_id": item["_id"],
            "warehouse_id": wh["_id"],
            "type": "income",
            "amount": data.amount,
            "ts": now,
            "by_user_id": current["_id"],
        }
    )

    item2 = await db["items"].find_one({"_id": item["_id"]})
    await _check_low_stock(db, item2, wh, company_id=wh["company_id"], by_user_id=current["_id"])

    return JSONResponse({"ok": True, "count": item2["count"]}, status_code=200)


@router.post("/outcome")
async def outcome(request: Request, data: ItemOp, current=require_permission("items.op")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Товар не найден.")

    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"], "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)
    _ensure_not_blocked_for_write(wh, current)

    if item["count"] < data.amount:
        raise HTTPException(400, "Недостаточно товара на складе.")

    now = datetime.now(timezone.utc)
    await db["items"].update_one(
        {"_id": item["_id"]},
        {"$inc": {"count": -data.amount}, "$set": {"updated_at": now}},
    )
    await db["history"].insert_one(
        {
            "item_id": item["_id"],
            "warehouse_id": wh["_id"],
            "type": "outcome",
            "amount": data.amount,
            "ts": now,
            "by_user_id": current["_id"],
        }
    )

    item2 = await db["items"].find_one({"_id": item["_id"]})
    await _check_low_stock(db, item2, wh, company_id=wh["company_id"], by_user_id=current["_id"])

    return JSONResponse({"ok": True, "count": item2["count"]}, status_code=200)


@router.get("/history/{item_id}")
async def item_history(request: Request, item_id: str, current=require_permission("items.update")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(item_id)})
    if not item:
        raise HTTPException(404, "Товар не найден.")

    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"], "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)

    hist = [
        public_id(h)
        async for h in db["history"].find({"item_id": item["_id"]}).sort("ts", -1).limit(20)
    ]
    return JSONResponse({"ok": True, "history": hist}, status_code=200)


@router.get("/history/warehouse/{warehouse_id}")
async def warehouse_history(
    request: Request,
    warehouse_id: str,
    limit: int = 100,
    current=require_permission("items.update"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)

    hist_raw = [
        h async for h in db["history"]
        .find({"warehouse_id": wh["_id"]})
        .sort("ts", -1)
        .limit(limit)
    ]

    item_ids = list({h.get("item_id") for h in hist_raw if h.get("item_id")})
    items_map: Dict[Any, str] = {}
    if item_ids:
        async for it in db["items"].find({"_id": {"$in": item_ids}}):
            items_map[it["_id"]] = it.get("name", "—")

    hist = [
        public_id({**h, "item_name": items_map.get(h.get("item_id"), "—")})
        for h in hist_raw
    ]
    return JSONResponse({"ok": True, "history": hist}, status_code=200)


@router.get("/low_stock/{warehouse_id}")
async def low_stock(request: Request, warehouse_id: str, current=require_permission("items.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    _ensure_company_access(wh, current)

    items: List[Dict[str, Any]] = []
    default_low = wh.get("low_stock_default", 1)

    async for i in db["items"].find({"warehouse_id": wh["_id"], "deleted_at": None}):
        low = i.get("low_limit")
        if low is None:
            low = default_low
        if i.get("count", 0) <= low:
            items.append(public_id(i))

    return JSONResponse({"ok": True, "items": items}, status_code=200)