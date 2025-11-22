from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import secrets

from server.routes.schemes import CreateWarehouse, UpdateWarehouse
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/warehouse", tags=["Warehouse"])


def _root_only(current):
    if not current.get("is_root"):
        raise HTTPException(403, "Доступ только для root пользователя.")


@router.post("/create")
async def create_warehouse(
    request: Request,
    data: CreateWarehouse,
    current=require_permission("warehouses.create"),
):
    db = request.app.state.mongo_db

    if current.get("is_root") and not current.get("company_id"):
        raise HTTPException(400, "У root нет контекста компании для создания склада.")

    api_key = secrets.token_urlsafe(24)

    doc = {
        "company_id": current["company_id"],
        "name": data.name,
        "notification_emails": data.notification_emails,
        "low_stock_default": data.low_stock_default,
        "camera_api_key": api_key,
        "created_at": datetime.now(timezone.utc),
        "blocked_at": None,
        "deleted_at": None,
    }
    _id = (await db["warehouses"].insert_one(doc)).inserted_id
    return JSONResponse({"ok": True, "warehouse": public_id({**doc, "_id": _id})})


@router.get("/list")
async def list_warehouses(
    request: Request,
    current=require_permission("warehouses.update"),
):
    db = request.app.state.mongo_db

    q = {"deleted_at": None}
    if not current.get("is_root"):
        q["company_id"] = current["company_id"]

    ws = [public_id(w) async for w in db["warehouses"].find(q)]
    return JSONResponse({"ok": True, "warehouses": ws})


@router.post("/update")
async def update_warehouse(
    request: Request,
    data: UpdateWarehouse,
    current=require_permission("warehouses.update"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(data.warehouse_id)})
    if not wh or wh.get("deleted_at"):
        raise HTTPException(404, "Склад не найден.")

    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этому складу компании.")

    upd = {}
    if data.name is not None:
        upd["name"] = data.name
    if data.notification_emails is not None:
        upd["notification_emails"] = data.notification_emails
    if data.low_stock_default is not None:
        upd["low_stock_default"] = data.low_stock_default

    if upd:
        await db["warehouses"].update_one({"_id": wh["_id"]}, {"$set": upd})

    return JSONResponse({"ok": True})


@router.delete("/delete/{warehouse_id}")
async def delete_warehouse(
    request: Request,
    warehouse_id: str,
    current=require_permission("warehouses.delete"),
):
    db = request.app.state.mongo_db
    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id)})
    if not wh or wh.get("deleted_at"):
        raise HTTPException(404, "Склад не найден.")

    if not current.get("is_root") and wh["company_id"] != current["company_id"]:
        raise HTTPException(403, "У вас нет доступа к этому складу компании.")

    await db["warehouses"].update_one(
        {"_id": wh["_id"]},
        {"$set": {"deleted_at": datetime.now(timezone.utc)}},
    )
    return JSONResponse({"ok": True})


@router.post("/block/{warehouse_id}")
async def block_warehouse(
    request: Request,
    warehouse_id: str,
    current=require_permission("*"),
):
    _root_only(current)
    db = request.app.state.mongo_db

    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    now = datetime.now(timezone.utc)
    await db["warehouses"].update_one({"_id": wh["_id"]}, {"$set": {"blocked_at": now}})
    return JSONResponse({"ok": True})


@router.post("/unblock/{warehouse_id}")
async def unblock_warehouse(
    request: Request,
    warehouse_id: str,
    current=require_permission("*"),
):
    _root_only(current)
    db = request.app.state.mongo_db

    wh = await db["warehouses"].find_one({"_id": oid(warehouse_id), "deleted_at": None})
    if not wh:
        raise HTTPException(404, "Склад не найден.")

    await db["warehouses"].update_one({"_id": wh["_id"]}, {"$set": {"blocked_at": None}})
    return JSONResponse({"ok": True})