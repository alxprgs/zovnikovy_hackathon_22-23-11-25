from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["health"])

@router.get(
    "/healthz",
    response_class=PlainTextResponse,
    summary="Проверка работоспособности",
    description="Возвращает 'ok', если сервис запущен и принимает запросы.",
    responses={200: {"content": {"text/plain": {"example": "ok"}}}},
)
async def health_check() -> str:
    return PlainTextResponse("ok", media_type="text/plain; charset=utf-8")