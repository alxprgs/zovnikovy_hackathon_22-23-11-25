from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, status, HTTPException
from fastapi.responses import JSONResponse

from server.core.config import vk_settings, settings

router = APIRouter(prefix="/dev/vk", tags=["VK Debug"])


@router.get("/raw")
async def vk_debug_raw(request: Request, code: str, device_id: str):
    if not settings.DEV:
        raise HTTPException(status_code=403, detail="VK Debug доступен только при DEV=True")

    async with httpx.AsyncClient() as client:
        raw_resp = await client.post(
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

    try:
        json_data = raw_resp.json()
    except Exception:
        json_data = {"raw_text": raw_resp.text}

    return JSONResponse(
        {
            "status_code": raw_resp.status_code,
            "headers": dict(raw_resp.headers),
            "data": json_data,
        },
        status_code=200,
    )