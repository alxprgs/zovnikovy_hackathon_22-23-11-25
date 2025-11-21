from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from server.core.config import vk_settings, settings, jwt_settings
from server.core.functions.jwt_utils import create_jwt

router = APIRouter(prefix="/user/auth/vk", tags=["User"])


@router.get("/callback")
async def vk_callback(request: Request, response: Response, code: str, device_id: str):

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://id.vk.com/oauth2/token",
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
    id_token = token_data.get("id_token")

    if not access_token:
        raise HTTPException(401, "VK did not return access_token")

    if not user_data and id_token:
        import jwt as pyjwt
        unverified = pyjwt.decode(id_token, options={"verify_signature": False})
        vk_uid = unverified.get("sub")
        if vk_uid:
            user_data = {"id": vk_uid}

    if not user_data or "id" not in user_data:
        raise HTTPException(
            401,
            f"VK did not return user info: {token_data}",
        )

    vk_user_id = str(user_data["id"])
    db = request.app.state.mongo_db

    user = await db["users"].find_one({"vk_id": vk_user_id})

    if not user:
        user_doc = {
            "vk_id": vk_user_id,
            "login": f"vk_{vk_user_id}",
            "email": token_data.get("email"),
            "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
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
