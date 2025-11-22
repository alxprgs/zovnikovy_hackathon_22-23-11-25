from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from server.core.functions.permissions import require_permission
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/root/companies", tags=["Root"])

@router.get("/list")
async def list_companies(request: Request, current= require_permission("*")):
    if not current.get("is_root"):
        raise HTTPException(403, "root only")
    db = request.app.state.mongo_db
    cs = [public_id(c) async for c in db["companies"].find({"deleted_at": None})]
    return JSONResponse({"ok": True, "companies": cs})

@router.post("/block/{company_id}")
async def block_company(request: Request, company_id: str, current= require_permission("*")):
    if not current.get("is_root"):
        raise HTTPException(403, "root only")
    db = request.app.state.mongo_db
    await db["companies"].update_one({"_id": oid(company_id)}, {"$set": {"blocked_at": datetime.now(timezone.utc)}})
    await db["users"].update_many({"company_id": oid(company_id)}, {"$set": {"blocked_at": datetime.now(timezone.utc)}})
    return JSONResponse({"ok": True})

@router.post("/unblock/{company_id}")
async def unblock_company(request: Request, company_id: str, current= require_permission("*")):
    if not current.get("is_root"):
        raise HTTPException(403, "root only")
    db = request.app.state.mongo_db
    await db["companies"].update_one({"_id": oid(company_id)}, {"$set": {"blocked_at": None}})
    await db["users"].update_many({"company_id": oid(company_id)}, {"$set": {"blocked_at": None}})
    return JSONResponse({"ok": True})

@router.delete("/delete/{company_id}")
async def delete_company(request: Request, company_id: str, current= require_permission("*")):
    if not current.get("is_root"):
        raise HTTPException(403, "root only")

    db = request.app.state.mongo_db
    now = datetime.now(timezone.utc)
    cid = oid(company_id)

    await db["companies"].update_one({"_id": cid}, {"$set": {"deleted_at": now}})

    wh_ids = [w["_id"] async for w in db["warehouses"].find({"company_id": cid})]

    await db["warehouses"].update_many({"company_id": cid}, {"$set": {"deleted_at": now}})

    await db["users"].update_many({"company_id": cid}, {"$set": {"deleted_at": now}})

    if wh_ids:
        await db["items"].update_many({"warehouse_id": {"$in": wh_ids}}, {"$set": {"deleted_at": now}})
        await db["supplies"].update_many({"warehouse_id": {"$in": wh_ids}}, {"$set": {"deleted_at": now}})
        await db["history"].update_many({"warehouse_id": {"$in": wh_ids}}, {"$set": {"deleted_at": now}})

    return JSONResponse({"ok": True})
