from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from server.core.functions.permissions import require_permission
from server.core.config import root_user_settings

router = APIRouter(prefix="/user", tags=["User"])


@router.delete("/delete")
async def delete_user(
    request: Request,
    login: str,
    current_user=Depends(require_permission("user_delete")),
):
    db = request.app.state.mongo_db

    user = await db["users"].find_one({"login": login})
    if not user:
        return JSONResponse(
            {"status": False, "msg": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    perms = user.get("permissions", {})
    if perms.get("root") or login == root_user_settings.LOGIN:
        return JSONResponse(
            {"status": False, "msg": "Cannot delete root user"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if str(user["_id"]) == str(current_user["sub"]):
        return JSONResponse(
            {"status": False, "msg": "You cannot delete yourself"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result = await db["users"].delete_one({"_id": user["_id"]})

    if result.deleted_count == 0:
        return JSONResponse(
            {"status": False, "msg": "User not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return JSONResponse({"status": True, "msg": "User deleted"})