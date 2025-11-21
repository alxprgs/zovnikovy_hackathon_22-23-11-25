from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from server.core.functions.hash_utils import hash_password
from server.core.functions.permissions import require_permission

from .schemes import CreateUserSchema

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/create")
async def create_user(
    request: Request,
    data: CreateUserSchema,
    current_user=Depends(require_permission("user_create")),
):
    db = request.app.state.mongo_db

    if await db["users"].find_one({"login": data.login}):
        return JSONResponse(
            {"status": False, "msg": "Login already exists"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(data.permissions, dict):
        return JSONResponse(
            {"status": False, "msg": "Invalid permissions format"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if data.permissions.get("root") and not current_user["permissions"].get("root"):
        return JSONResponse(
            {"status": False, "msg": "Only root can create root users"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    await db["users"].insert_one({
        "login": data.login,
        "password": hash_password(data.password),
        "permissions": data.permissions,
    })

    return JSONResponse({"status": True, "msg": "User created"}, status_code=status.HTTP_201_CREATED)