from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, EmailStr

from server.core.config import settings
from server.core.functions.permissions import require_permission
from server.core.mailer import send_low_stock_email

router = APIRouter(prefix="/dev", tags=["Dev"])


class LowStockMailTest(BaseModel):
    to: EmailStr = Field(...)
    item_name: str = Field("Тестовый товар")
    count: int = Field(0, ge=0)
    low_limit: int = Field(1, ge=0)
    warehouse_name: str = Field("Тестовый склад")


@router.post("/test_low_stock_email")
async def test_low_stock_email(
    request: Request,
    data: LowStockMailTest,
):
    if not settings.DEV:
        raise HTTPException(404, "Not found")

    await send_low_stock_email(
        request.app,
        [str(data.to)],
        data.item_name,
        data.count,
        data.low_limit,
        data.warehouse_name,
    )

    return {"ok": True, "sent_to": str(data.to)}
