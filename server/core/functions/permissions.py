from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from server.core.functions.jwt_utils import decode_jwt
from server.core.db_utils import oid


def has_perm(user: dict, perm: str) -> bool:
    if user.get("is_root"):
        return True
    perms = set(user.get("permissions", []))
    return "*" in perms or perm in perms


def require_permission(perm: str):
    async def dep(request: Request):
        token = request.headers.get("authorization")
        if not token or not token.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing token")

        token = token.split(" ", 1)[1].strip()
        payload = decode_jwt(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        db = request.app.state.mongo_db
        user = await db["users"].find_one({"_id": oid(user_id), "deleted_at": None})

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.get("blocked_at"):
            raise HTTPException(status_code=403, detail="User blocked")

        if not has_perm(user, perm):
            raise HTTPException(status_code=403, detail=f"No permission: {perm}")

        return user

    return Depends(dep)
