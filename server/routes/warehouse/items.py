from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
from server.routes.schemes import CreateItem, UpdateItem, ItemOp
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id
from server.core.mailer import send_low_stock_email

router = APIRouter(prefix="/items", tags=["Items"])

async def _check_low_stock(db, item, warehouse):
    low_limit = item.get("low_limit")
    if low_limit is None:
        low_limit = warehouse.get("low_stock_default", 1)

    if item["count"] <= low_limit and warehouse.get("notification_emails"):
        await send_low_stock_email(
            request_app=None,
            to_list=warehouse["notification_emails"],
            item_name=item["name"],
            count=item["count"],
            low_limit=low_limit,
            warehouse_name=warehouse["name"],
        )

@router.post("/create")
async def create_item(request: Request, data: CreateItem, current= require_permission("items.create")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company warehouse")

    doc = {
        "warehouse_id": wh["_id"],
        "name": data.name,
        "category": data.category,
        "unit": data.unit,
        "count": data.count,
        "low_limit": data.low_limit,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": None
    }
    _id = (await db["items"].insert_one(doc)).inserted_id

    await db["history"].insert_one({
        "item_id": _id,
        "warehouse_id": wh["_id"],
        "type": "income" if data.count > 0 else "create",
        "amount": data.count,
        "ts": datetime.now(timezone.utc),
        "by_user_id": current["_id"]
    })

    return {"ok": True, "item": public_id({**doc, "_id": _id})}

@router.get("/list/{warehouse_id}")
async def list_items(request: Request, warehouse_id: str, current= require_permission("items.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company warehouse")

    items = [public_id(i) async for i in db["items"].find({"warehouse_id": wh["_id"], "deleted_at": None})]
    return {"ok": True, "items": items}

@router.post("/update")
async def update_item(request: Request, data: UpdateItem, current= require_permission("items.update")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Item not found")

    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"]})
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    upd = {k: v for k, v in data.model_dump(exclude={"item_id"}).items() if v is not None}
    upd["updated_at"] = datetime.now(timezone.utc)
    await db["items"].update_one({"_id": item["_id"]}, {"$set": upd})
    return {"ok": True}

@router.post("/income")
async def income(request: Request, data: ItemOp, current= require_permission("items.op")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Item not found")
    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"]})
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    await db["items"].update_one({"_id": item["_id"]}, {"$inc": {"count": data.amount}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    await db["history"].insert_one({
        "item_id": item["_id"],
        "warehouse_id": wh["_id"],
        "type": "income",
        "amount": data.amount,
        "ts": datetime.now(timezone.utc),
        "by_user_id": current["_id"]
    })

    item = await db["items"].find_one({"_id": item["_id"]})
    return {"ok": True, "count": item["count"]}

@router.post("/outcome")
async def outcome(request: Request, data: ItemOp, current= require_permission("items.op")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(data.item_id), "deleted_at": None})
    if not item:
        raise HTTPException(404, "Item not found")
    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"]})
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    if item["count"] < data.amount:
        raise HTTPException(400, "Not enough stock")

    await db["items"].update_one({"_id": item["_id"]}, {"$inc": {"count": -data.amount}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    await db["history"].insert_one({
        "item_id": item["_id"],
        "warehouse_id": wh["_id"],
        "type": "outcome",
        "amount": data.amount,
        "ts": datetime.now(timezone.utc),
        "by_user_id": current["_id"]
    })

    item = await db["items"].find_one({"_id": item["_id"]})
    await _check_low_stock(db, item, wh)
    return {"ok": True, "count": item["count"]}

@router.get("/history/{item_id}")
async def item_history(request: Request, item_id: str, current= require_permission("items.update")):
    db = request.app.state.mongo_db
    item = await db["items"].find_one({"_id": oid(item_id)})
    if not item:
        raise HTTPException(404, "Item not found")
    wh = await db["warehouses"].find_one({"_id": item["warehouse_id"]})
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    hist = [public_id(h) async for h in db["history"].find({"item_id": item["_id"]}).sort("ts", -1).limit(20)]
    return {"ok": True, "history": hist}

@router.get("/low_stock/{warehouse_id}")
async def low_stock(request: Request, warehouse_id: str, current= require_permission("items.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id)})
    if not wh:
        raise HTTPException(404, "Warehouse not found")

    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    items = []
    async for i in db["items"].find({"warehouse_id": wh["_id"], "deleted_at": None}):
        low = i.get("low_limit")
        if low is None:
            low = wh.get("low_stock_default", 1)
        if i["count"] <= low:
            items.append(public_id(i))
    return {"ok": True, "items": items}
