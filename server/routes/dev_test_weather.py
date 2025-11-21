from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from asfeslib.core.logger import Logger
from server.core.config import settings
from server.core.ratelimit_simple import rate_limit

logger = Logger(__name__)

router = APIRouter(tags=["dev"])


class WeatherTestSchema(BaseModel):
    city: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Za-zА-Яа-яёЁ -]+$")

@rate_limit(limit=5, period=60)
@router.post("/dev/test_weather")
async def dev_test_weather(request: Request, data: WeatherTestSchema):

    if not settings.DEV:
        return RedirectResponse(
            url="/",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    client = getattr(request.app.state, "weatherclient", None)
    if client is None:
        return JSONResponse(
            {"status": False, "msg": "Клиент куда-то потерялся жи ессе"},
            status_code=500
        )

    try:
        resp = await client.current(data.city)
        return {
            "status": True,
            "msg": "Успешно брат",
            "data": resp
        }

    except Exception as e:
        logger.error(f"Ошибка получения погоды: '{e}'")

        return JSONResponse(
            {
                "status": False,
                "msg": "Ошибка йоу, в консоль зайди по братски"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
