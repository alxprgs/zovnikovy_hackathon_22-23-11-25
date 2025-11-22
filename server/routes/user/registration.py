from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from server.routes.schemes import RegisterCEO
from server.core.functions.hash_utils import hash_password
from server.core.functions.jwt_utils import create_jwt

router = APIRouter(prefix="/user", tags=["User"])

CEO_DEFAULT_PERMS = [
    "company.update",
    "users.create",
    "users.update",
    "warehouses.create",
    "warehouses.update",
    "warehouses.delete",
    "items.create",
    "items.update",
    "items.delete",
    "items.op",
    "supplies.create",
    "supplies.update",
    "supplies.delete",
    "camera.create_key",
]


@router.post("/register/ceo")
async def register_ceo(request: Request, data: RegisterCEO):
    db = request.app.state.mongo_db

    if await db["users"].find_one({"login": data.login}):
        raise HTTPException(409, "Такой логин уже существует.")

    if await db["companies"].find_one({"name": data.company_name}):
        raise HTTPException(409, "Компания с таким названием уже существует.")

    company = {
        "name": data.company_name,
        "inn": data.company_inn,
        "email": str(data.email),
        "created_at": datetime.now(timezone.utc),
        "blocked_at": None,
        "deleted_at": None
    }
    company_id = (await db["companies"].insert_one(company)).inserted_id

    ceo = {
        "login": data.login,
        "password": hash_password(data.password),
        "email": data.email,
        "post": "CEO",
        "permissions": CEO_DEFAULT_PERMS,
        "is_ceo": True,
        "is_root": False,
        "company_id": company_id,
        "created_at": datetime.now(timezone.utc),
        "blocked_at": None,
        "deleted_at": None
    }
    user_id = (await db["users"].insert_one(ceo)).inserted_id

    await db["companies"].update_one({"_id": company_id}, {"$set": {"ceo_user_id": user_id}})

    token = create_jwt(
        str(user_id),
        ceo["permissions"],
        company_id=str(company_id),
        is_ceo=True,
        is_root=False
    )

    return JSONResponse(
        {"ok": True, "token": token, "company_id": str(company_id)}
    )