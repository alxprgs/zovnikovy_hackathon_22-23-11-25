from __future__ import annotations

from fastapi import APIRouter, Response, HTTPException, status, Request
from fastapi.responses import JSONResponse

from server.core.ratelimit_simple import rate_limit
from server.core.functions.hash_utils import verify_password
from server.core.functions.jwt_utils import create_jwt
from server.core.config import settings, jwt_settings

from .schemes import AuthSchema

router = APIRouter(prefix="/user", tags=["User"])


@rate_limit(limit=5, period=60)
@router.post("/auth")
async def authorize_user(
    request: Request,
    data: AuthSchema,
    response: Response,
):
    db = request.app.state.mongo_db

    user = await db["users"].find_one({"login": data.login})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    jwt_token = create_jwt(str(user["_id"]), user.get("permissions", {}))

    response = JSONResponse({"status": True, "msg": "Authorized"})
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=not settings.DEV,
        samesite="lax",
        max_age=jwt_settings.TOKEN_EXPIRE_SEC,
    )

    return response