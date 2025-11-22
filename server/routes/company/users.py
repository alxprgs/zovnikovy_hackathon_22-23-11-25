from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from server.routes.schemes import CreateEmployee, UpdateEmployeePerms
from server.core.functions.permissions import require_permission
from server.core.functions.hash_utils import hash_password
from server.core.db_utils import oid, public_id

router = APIRouter(prefix="/company/users", tags=["Company Users"])


def _ceo_or_root(current):
    if not current.get("is_ceo") and not current.get("is_root"):
        raise HTTPException(403, "Only CEO or root allowed")


@router.post("/create")
async def create_employee(
    request: Request,
    data: CreateEmployee,
    current=require_permission("users.create"),
):
    db = request.app.state.mongo_db
    _ceo_or_root(current)

    if current.get("is_root") and not current.get("company_id"):
        raise HTTPException(400, "root has no company context for create")

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
        "created_at": datetime.now(timezone.utc),
        "blocked_at": None,
        "deleted_at": None,
    }
    _id = (await db["users"].insert_one(doc)).inserted_id
    return JSONResponse({"ok": True, "user": public_id({**doc, "_id": _id})})


@router.get("/list")
async def list_employees(
    request: Request,
    current=require_permission("users.update"),
):
    db = request.app.state.mongo_db

    if current.get("is_root"):
        q = {"is_root": False, "deleted_at": None}
    else:
        q = {"company_id": current["company_id"], "is_root": False, "deleted_at": None}

    users = [public_id(u) async for u in db["users"].find(q)]
    return JSONResponse({"ok": True, "users": users})


@router.post("/update")
async def update_employee(
    request: Request,
    data: UpdateEmployeePerms,
    current=require_permission("users.update"),
):
    db = request.app.state.mongo_db

    target = await db["users"].find_one({"_id": oid(data.user_id)})
    if not target or target.get("deleted_at"):
        raise HTTPException(404, "User not found")

    if target.get("is_root") and not current.get("is_root"):
        raise HTTPException(403, "root user only editable by root")

    if not current.get("is_root") and target.get("company_id") != current.get("company_id"):
        raise HTTPException(403, "Not your company user")

    upd = {}
    if data.post is not None:
        upd["post"] = data.post
    if data.permissions is not None:
        upd["permissions"] = data.permissions
    if data.blocked is not None:
        upd["blocked_at"] = datetime.now(timezone.utc) if data.blocked else None

    if upd:
        await db["users"].update_one({"_id": target["_id"]}, {"$set": upd})

    return JSONResponse({"ok": True})


@router.delete("/delete/{user_id}")
async def delete_employee(
    request: Request,
    user_id: str,
    current=require_permission("users.update"),
):
    db = request.app.state.mongo_db
    _ceo_or_root(current)

    target = await db["users"].find_one({"_id": oid(user_id)})
    if not target or target.get("deleted_at"):
        raise HTTPException(404, "User not found")

    if target.get("is_root"):
        raise HTTPException(403, "Cannot delete root user")

    if not current.get("is_root") and target.get("is_ceo"):
        raise HTTPException(403, "CEO cannot delete CEO user")

    if not current.get("is_root") and target.get("company_id") != current.get("company_id"):
        raise HTTPException(403, "Not your company user")

    now = datetime.now(timezone.utc)
    await db["users"].update_one(
        {"_id": target["_id"]},
        {"$set": {"deleted_at": now, "blocked_at": now}},
    )

    return JSONResponse({"ok": True})
