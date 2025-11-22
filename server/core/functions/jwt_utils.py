from __future__ import annotations

import time
from typing import Optional, List, Any, Dict

import jwt
from fastapi import Request

from server.core.config import jwt_settings


def create_jwt(
    user_id: str,
    permissions: List[str],
    company_id: Optional[str] = None,
    is_ceo: bool = False,
    is_root: bool = False,
) -> str:
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": user_id,
        "permissions": permissions,
        "company_id": company_id,
        "is_ceo": is_ceo,
        "is_root": is_root,
        "iat": now,
        "exp": now + jwt_settings.TOKEN_EXPIRE_SEC,
    }
    return jwt.encode(payload, jwt_settings.SECRET_KEY, algorithm=jwt_settings.ALGORITHM)


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            jwt_settings.SECRET_KEY,
            algorithms=[jwt_settings.ALGORITHM],
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_jwt_from_request(request: Request) -> Optional[str]:
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip() or None

    return None
