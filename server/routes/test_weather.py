from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from asfeslib.core.logger import Logger
from server.core.config import settings

logger = Logger(__name__)

router = APIRouter(tags=["dev"])


class WeatherTestSchema(BaseModel):
    city: str = Field(..., min_length=1)


@router.post("/dev/test_weather")
async def test_weather(request: Request, data: WeatherTestSchema):

    if not settings.DEV:
        return RedirectResponse(
            url="/",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    client = request.app.state.weatherclient

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
