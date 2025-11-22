from .schemes import AddItem

from fastapi import APIRouter, Request, Depends, status
from server.core.functions.permissions import require_permission
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


@router.post("/add")
async def warehouse_add(
    request: Request,
    data: AddItem,
    current_user=Depends(require_permission("db_warehouse"))
):
    pass