from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from server.core.config import vk_settings, settings, jwt_settings
from server.core.functions.jwt_utils import create_jwt

router = APIRouter(prefix="/user/auth/vk", tags=["User"])


@router.get("/callback")
async def vk_callback(request: Request, response: Response, code: str, device_id: str):
    """
    Callback для VK ID (OneTap / OAuth 2.0).
    Принимает ?code=...&device_id=...
    Делает обмен кода на токен и данные пользователя.
    Авторизует юзера в системе.
    """

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://id.vk.com/oauth2/auth",
            data={
                "grant_type": "authorization_code",
                "client_id": vk_settings.CLIENT_ID,
                "client_secret": vk_settings.CLIENT_SECRET,
                "redirect_uri": vk_settings.REDIRECT_URI,
                "code": code,
                "device_id": device_id,
            },
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"VK auth error: {token_resp.text}",
        )

    token_data = token_resp.json()

    access_token = token_data.get("access_token")
    user_data = token_data.get("user")

    if not access_token or not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid VK response",
        )

    vk_user_id = str(user_data["id"])
    first_name = user_data.get("first_name", "")
    last_name = user_data.get("last_name", "")
    email = user_data.get("email")

    db = request.app.state.mongo_db

    user = await db["users"].find_one({"vk_id": vk_user_id})

    if not user:
        user_doc = {
            "vk_id": vk_user_id,
            "login": f"vk_{vk_user_id}",
            "email": email,
            "name": f"{first_name} {last_name}".strip(),
            "permissions": {"user": True},
        }
        result = await db["users"].insert_one(user_doc)
        user_id = str(result.inserted_id)
        permissions = user_doc["permissions"]

    else:
        user_id = str(user["_id"])
        permissions = user.get("permissions", {})

    jwt_token = create_jwt(user_id, permissions)

    resp = JSONResponse({"status": True, "msg": "Authorized via VK"})
    resp.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=not settings.DEV,
        samesite="lax",
        max_age=jwt_settings.TOKEN_EXPIRE_SEC,
    )

    return resp