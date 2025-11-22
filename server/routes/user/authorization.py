from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException, status
from server.routes.schemes import Login
from server.core.functions.hash_utils import verify_password
from server.core.functions.jwt_utils import create_jwt

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/auth")
async def auth(request: Request, data: Login):
    db = request.app.state.mongo_db

    user = await db["users"].find_one({"login": data.login, "deleted_at": None})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("blocked_at"):
        raise HTTPException(403, "User blocked")

    token = create_jwt(
        str(user["_id"]),
        user.get("permissions", []),
        company_id=str(user["company_id"]) if user.get("company_id") else None,
        is_ceo=bool(user.get("is_ceo")),
        is_root=bool(user.get("is_root")),
    )
    return {"ok": True, "token": token, "role": "root" if user.get("is_root") else "ceo" if user.get("is_ceo") else "employee"}
