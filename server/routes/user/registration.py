from __future__ import annotations

from fastapi import APIRouter, Request, status, Response
from fastapi.responses import JSONResponse

from server.core.functions.hash_utils import hash_password
from server.core.ratelimit_simple import rate_limit
from server.core.functions.jwt_utils import create_jwt
from server.core.config import settings, jwt_settings

from .schemes import AuthSchema

router = APIRouter(prefix="/user", tags=["User"])


@rate_limit(limit=5, period=60)
@router.post("/register")
async def register_user(
    request: Request,
    data: AuthSchema,
    response: Response,
):
    db = request.app.state.mongo_db

    exists = await db["users"].find_one({"login": data.login})
    if exists:
        return JSONResponse(
            {"status": False, "msg": "Login already exists"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user_doc = {
        "login": data.login,
        "password": hash_password(data.password),
        "permissions": {"user": True},
    }

    result = await db["users"].insert_one(user_doc)

    jwt_token = create_jwt(str(result.inserted_id), user_doc["permissions"])

    response = JSONResponse({"status": True, "msg": "Registration successful"}, status_code=status.HTTP_200_OK,)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=not settings.DEV,
        samesite="lax",
        max_age=jwt_settings.TOKEN_EXPIRE_SEC,
    )

    return response