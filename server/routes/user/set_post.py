from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from server.core.functions.permissions import require_permission
from .schemes import UpdateUserSetPost

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

@router.put("/update/set_post")
async def update_set_post(
    request: Request, 
    data: UpdateUserSetPost, 
    current_user=Depends(require_permission("user_set_post"))
):
    db = request.app.state.mongo_db
    result = await db["users"].update_one(
        {"login": data.login},
        {
            "$set": {
                f"post.{data.post}": data.status
            }
        }
    )
    if result.matched_count == 0:
        return JSONResponse(
            {"status": False, "msg": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return JSONResponse({"status": True, "msg": "User updated"})