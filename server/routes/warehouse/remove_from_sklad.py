from .schemes import RemoveItem

from fastapi import APIRouter, Request, Depends, status
from server.core.functions.permissions import require_permission
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.post("/remove")
async def warehouse_remove(
    request: Request,
    data: RemoveItem,
    current_user=Depends(require_permission("db_warehouse"))
):
    db: AsyncIOMotorDatabase = request.app.state.mongo_db

    warehouse = current_user.get("warehouse_data")
    if not warehouse:
        return JSONResponse(
            {"status": False, "msg": "Отсутствует warehouse_data."},
            status_code=status.HTTP_403_FORBIDDEN
        )

    company = warehouse.get("company")
    warehouse_ids = warehouse.get("warehouse_ids", [])

    if company != data.company:
        return JSONResponse(
            {"status": False, "msg": "У вас нет доступа к этой компании."},
            status_code=status.HTTP_403_FORBIDDEN
        )

    if data.warehouse_id not in warehouse_ids:
        return JSONResponse(
            {"status": False, "msg": "У вас нет доступа к этому складу."},
            status_code=status.HTTP_403_FORBIDDEN
        )

    query = {
        "company": data.company,
        "warehouse_id": data.warehouse_id,
        "type": data.type,
    }

    exists = await db["warehouse"].find_one(query)

    if not exists:
        return JSONResponse(
            {"status": False, "msg": "Товар не найден на складе"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if exists["count"] < data.count:
        return JSONResponse(
            {"status": False, "msg": "Недостаточно товара на складе"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    updated = await db["warehouse"].find_one_and_update(
        query,
        {"$inc": {"count": -data.count}},
        return_document=ReturnDocument.AFTER
    )

    return {
        "status": True,
        "msg": "Количество уменьшено",
        "data": updated
    }
