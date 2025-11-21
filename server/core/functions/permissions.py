from __future__ import annotations

from fastapi import Request, HTTPException, status
from .jwt_utils import get_jwt_from_request, decode_jwt


async def get_current_user(request: Request) -> dict:
    token = get_jwt_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    if "permissions" not in payload or not isinstance(payload["permissions"], dict):
        payload["permissions"] = {}

    return payload


def require_permission(permission_name: str):
    async def checker(request: Request):
        user = await get_current_user(request)
        perms = user.get("permissions", {})

        if perms.get("root"):
            return user

        if not perms.get(permission_name, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        return user

    return checker