from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from server.routes.schemes import CreateEmployee, UpdateEmployeePerms
from server.core.functions.permissions import require_permission
from server.core.functions.hash_utils import hash_password
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/company/users", tags=["Company Users"])

@router.post("/create")
async def create_employee(request: Request, data: CreateEmployee, current= require_permission("users.create")):
    db = request.app.state.mongo_db
    if not current.get("is_ceo") and not current.get("is_root"):
        raise HTTPException(403, "Only CEO can create employees")

    if await db["users"].find_one({"login": data.login}):
        raise HTTPException(409, "Login exists")

    doc = {
        "login": data.login,
        "password": hash_password(data.password),
        "email": data.email,
        "post": data.post,
        "permissions": data.permissions,
        "is_ceo": False,
        "is_root": False,
        "company_id": current["company_id"],
        "created_at": datetime.utcnow(),
        "blocked_at": None,
        "deleted_at": None
    }
    _id = (await db["users"].insert_one(doc)).inserted_id
    return {"ok": True, "user": public_id({**doc, "_id": _id})}

@router.get("/list")
async def list_employees(request: Request, current= require_permission("users.update")):
    db = request.app.state.mongo_db
    q = {"company_id": current["company_id"], "is_root": False, "deleted_at": None}
    users = [public_id(u) async for u in db["users"].find(q)]
    return {"ok": True, "users": users}

@router.post("/update")
async def update_employee(request: Request, data: UpdateEmployeePerms, current= require_permission("users.update")):
    db = request.app.state.mongo_db

    target = await db["users"].find_one({"_id": oid(data.user_id)})
    if not target:
        raise HTTPException(404, "User not found")

    if not current.get("is_root") and target.get("company_id") != current.get("company_id"):
        raise HTTPException(403, "Not your company user")

    upd = {}
    if data.post is not None:
        upd["post"] = data.post
    if data.permissions is not None:
        upd["permissions"] = data.permissions
    if data.blocked is not None:
        upd["blocked_at"] = datetime.utcnow() if data.blocked else None

    await db["users"].update_one({"_id": target["_id"]}, {"$set": upd})
    return {"ok": True}
