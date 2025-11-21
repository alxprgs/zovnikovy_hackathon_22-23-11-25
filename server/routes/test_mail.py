from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

from asfeslib.net.mail import MailMessage, MailClient
from asfeslib.core.logger import Logger
from server.core.config import settings, mail_settings
from server.core.ratelimit_simple import rate_limit

logger = Logger(__name__)

router = APIRouter(tags=["dev"])


class MailTestSchema(BaseModel):
    email: EmailStr

@rate_limit(limit=5, period=60)
@router.post("/dev/test_mail")
async def dev_test_mail(request: Request, data: MailTestSchema):
    if settings.DEV is not True:
        return RedirectResponse(
            url="/", status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    logger.debug(f"MAIL_USERNAME={mail_settings.USERNAME!r}")
    logger.debug(f"MAIL_PASSWORD length={len(mail_settings.PASSWORD or '')}")

    cfg = getattr(request.app.state, "mailcfg", None)
    if cfg is None:
        return JSONResponse(
            {"status": False, "msg": "Нету конфига бля"},
            status_code=500
        )

    msg = MailMessage(
        to=[data.email],
        subject="Dev mail test - ASFES",
        body="Тест успешен чи не",
    )

    try:
        async with MailClient(cfg, timeout=10) as client:
            await client.send(msg, log=settings.DEV)

        return JSONResponse(
            {"status": True, "msg": "С кайфом"},
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        logger.error(f"Ошибка отправки почты: '{e}'")

        return JSONResponse(
            {"status": False, "msg": "Ошибка йоу, в консоль зайди по братски"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
