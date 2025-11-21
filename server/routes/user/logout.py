from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from server.core.functions.permissions import get_current_user
from server.core.config import settings

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/logout")
async def logout_user(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):

    response = JSONResponse({"status": True, "msg": "Logged out successfully"})
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=not settings.DEV,
        samesite="lax",
    )

    return response