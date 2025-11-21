from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from asfeslib.net.mail import MailMessage, MailClient
from asfeslib.core.logger import Logger
from server.core.config import settings, mail_settings

logger = Logger(__name__)

router = APIRouter(tags=["dev"])


class MailTestSchema(BaseModel):
    email: EmailStr


@router.post("/dev/test_mail", response_class=JSONResponse)
async def dev_test_mail(request: Request, data: MailTestSchema):
    if settings.DEV is not True:
        return JSONResponse(
            {"msg": "Брат, у тебя DEV режим не включён"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    logger.info(f"MAIL_USERNAME={mail_settings.USERNAME!r}")
    logger.info(f"MAIL_PASSWORD length={len(mail_settings.PASSWORD or '')}")

    cfg = request.app.state.mailcfg

    msg = MailMessage(
        to=[data.email],
        subject="Dev mail test - ASFES",
        body="Тест успешен чи не",
    )

    try:
        async with MailClient(cfg) as client:
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
