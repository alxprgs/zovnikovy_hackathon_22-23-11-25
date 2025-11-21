from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from server.core.config import vk_settings, settings, jwt_settings
from server.core.functions.jwt_utils import create_jwt

router = APIRouter(prefix="/user/auth/vk", tags=["User"])


@router.get("/callback")
async def vk_callback(
    request: Request,
    code: str,
    device_id: str,
    state: str | None = None,
    code_verifier: str | None = None,
):
    cookie_state = request.cookies.get("vk_state")
    if state and cookie_state and state != cookie_state:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid VK state",
        )

    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(
            "https://id.vk.com/oauth2/auth",
            data={
                "grant_type": "authorization_code",
                "client_id": vk_settings.CLIENT_ID,
                "client_secret": vk_settings.CLIENT_SECRET,
                "redirect_uri": vk_settings.REDIRECT_URI,
                "code": code,
                "device_id": device_id,
                **({"code_verifier": code_verifier} if code_verifier else {}),
            },
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"VK auth error: {token_resp.text}",
        )

    token_data = token_resp.json()
    access_token: str | None = token_data.get("access_token")
    id_token: str | None = token_data.get("id_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"VK did not return access_token: {token_data}",
        )

    user_data: dict = {}
    async with httpx.AsyncClient(timeout=20) as client:
        info_resp = await client.get(
            "https://id.vk.com/oauth2/public_info",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if info_resp.status_code == 200:
        info_json = info_resp.json() or {}
        user_data = info_json.get("user") or {}
    else:
        user_data = {}

    vk_uid = None
    if "user_id" in user_data:
        vk_uid = user_data.get("user_id")
    elif id_token:
        try:
            import jwt as pyjwt  # type: ignore
            unverified = pyjwt.decode(id_token, options={"verify_signature": False})
            vk_uid = unverified.get("sub")
        except Exception:
            vk_uid = None

    if not vk_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"VK did not return user id. token_data={token_data}, user_data={user_data}",
        )

    vk_user_id = str(vk_uid)

    db = request.app.state.mongo_db
    user = await db["users"].find_one({"vk_id": vk_user_id})

    if not user:
        first_name = (user_data.get("first_name") or "").strip()
        last_name = (user_data.get("last_name") or "").strip()
        full_name = (first_name + " " + last_name).strip() or f"vk_{vk_user_id}"

        user_doc = {
            "vk_id": vk_user_id,
            "login": f"vk_{vk_user_id}",
            "email": user_data.get("email") or token_data.get("email"),
            "name": full_name,
            "avatar": user_data.get("avatar") or user_data.get("photo") or None,
            "permissions": {"user": True},
        }
        result = await db["users"].insert_one(user_doc)
        user_id = str(result.inserted_id)
        permissions = user_doc["permissions"]
    else:
        user_id = str(user["_id"])
        permissions = user.get("permissions", {}) or {}

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

    if cookie_state:
        resp.delete_cookie("vk_state", path="/")

    return resp