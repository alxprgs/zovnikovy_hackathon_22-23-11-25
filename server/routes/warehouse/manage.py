from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone
import secrets
from server.routes.schemes import CreateWarehouse, UpdateWarehouse
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/warehouse", tags=["Warehouse"])

@router.post("/create")
async def create_warehouse(request: Request, data: CreateWarehouse, current= require_permission("warehouses.create")):
    db = request.app.state.mongo_db

    api_key = secrets.token_urlsafe(24)

    doc = {
        "company_id": current["company_id"],
        "name": data.name,
        "notification_emails": data.notification_emails,
        "low_stock_default": data.low_stock_default,
        "camera_api_key": api_key,
        "created_at": datetime.now(timezone.utc),
        "blocked_at": None,
        "deleted_at": None
    }
    _id = (await db["warehouses"].insert_one(doc)).inserted_id
    return {"ok": True, "warehouse": public_id({**doc, "_id": _id})}

@router.get("/list")
async def list_warehouses(request: Request, current= require_permission("warehouses.update")):
    db = request.app.state.mongo_db
    q = {"company_id": current["company_id"], "deleted_at": None}
    ws = [public_id(w) async for w in db["warehouses"].find(q)]
    return {"ok": True, "warehouses": ws}

@router.post("/update")
async def update_warehouse(request: Request, data: UpdateWarehouse, current= require_permission("warehouses.update")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id)})
    if not wh:
        raise HTTPException(404, "Warehouse not found")
    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company warehouse")

    upd = {}
    if data.name is not None:
        upd["name"] = data.name
    if data.notification_emails is not None:
        upd["notification_emails"] = data.notification_emails
    if data.low_stock_default is not None:
        upd["low_stock_default"] = data.low_stock_default

    await db["warehouses"].update_one({"_id": wh["_id"]}, {"$set": upd})
    return {"ok": True}

@router.delete("/delete/{warehouse_id}")
async def delete_warehouse(request: Request, warehouse_id: str, current= require_permission("warehouses.delete")):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id)})
    if not wh:
        raise HTTPException(404, "Warehouse not found")

    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "Not your company warehouse")

    await db["warehouses"].update_one({"_id": wh["_id"]}, {"$set": {"deleted_at": datetime.now(timezone.utc)}})
    return {"ok": True}
