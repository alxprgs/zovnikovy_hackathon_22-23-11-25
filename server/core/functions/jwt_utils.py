from __future__ import annotations

import time
from typing import Optional

import jwt
from fastapi import Request

from server.core.config import jwt_settings


def create_jwt(user_id: str, permissions: dict) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "permissions": permissions,
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
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_jwt_from_request(request: Request) -> Optional[str]:
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip() or None

    return None