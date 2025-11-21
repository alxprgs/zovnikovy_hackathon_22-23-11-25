from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from server.core.functions.permissions import require_permission
from .schemes import UpdateUserSchema

router = APIRouter(prefix="/user", tags=["User"])


def _contains_forbidden_mongo_operators(obj) -> bool:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("$"):
                return True
            if _contains_forbidden_mongo_operators(v):
                return True
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            if _contains_forbidden_mongo_operators(item):
                return True
    return False


@router.put("/update")
async def update_user(
    request: Request,
    data: UpdateUserSchema,
    current_user=Depends(require_permission("user_update")),
):
    db = request.app.state.mongo_db

    if _contains_forbidden_mongo_operators(data.updates):
        return JSONResponse(
            {"status": False, "msg": "Mongo operators are forbidden"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = await db["users"].update_one(
        {"login": data.login},
        {"$set": data.updates},
    )

    if result.matched_count == 0:
        return JSONResponse(
            {"status": False, "msg": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return JSONResponse({"status": True, "msg": "User updated"})