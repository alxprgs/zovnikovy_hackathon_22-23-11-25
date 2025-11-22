from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
from server.routes.schemes import CreateSupply, UpdateSupplyStatus
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/supplies", tags=["Supplies"])

@router.post("/create")
async def create_supply(request: Request, data: CreateSupply, current= require_permission("supplies.create")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    item = await db["items"].find_one({"_id": oid(data.item_id), "warehouse_id": wh["_id"]})
    if not item:
        raise HTTPException(404, "Item not in this warehouse")

    doc = {
        "warehouse_id": wh["_id"],
        "item_id": item["_id"],
        "amount": data.amount,
        "expected_at": data.expected_at,
        "note": data.note,
        "status": "waiting",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    _id = (await db["supplies"].insert_one(doc)).inserted_id
    return {"ok": True, "supply": public_id({**doc, "_id": _id})}

@router.get("/list/{warehouse_id}")
async def list_supplies(request: Request, warehouse_id: str, current= require_permission("supplies.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id)})
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    s = [public_id(x) async for x in db["supplies"].find({"warehouse_id": wh["_id"]}).sort("expected_at", 1)]
    return {"ok": True, "supplies": s}

@router.post("/status")
async def update_supply_status(request: Request, data: UpdateSupplyStatus, current= require_permission("supplies.update")):
    db = request.app.state.mongo_db
    sup = await db["supplies"].find_one({"_id": oid(data.supply_id)})
    if not sup:
        raise HTTPException(404, "Supply not found")

    wh = await db["warehouses"].find_one({"_id": sup["warehouse_id"]})
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company")

    await db["supplies"].update_one({"_id": sup["_id"]}, {"$set": {"status": data.status, "updated_at": datetime.now(timezone.utc)}})

    if data.status == "done":
        await db["items"].update_one({"_id": sup["item_id"]}, {"$inc": {"count": sup["amount"]}, "$set": {"updated_at": datetime.now(timezone.utc)}})
        await db["history"].insert_one({
            "item_id": sup["item_id"],
            "warehouse_id": sup["warehouse_id"],
            "type": "income",
            "amount": sup["amount"],
            "ts": datetime.now(timezone.utc),
            "by_user_id": current["_id"],
            "note": "auto from supply"
        })

    return {"ok": True}
