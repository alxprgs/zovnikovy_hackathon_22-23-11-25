from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates

from server.core.config import settings, mail_settings, mongodb_settings
from server.core.paths import STATIC_DIR, TEMPLATES_DIR
from asfeslib.net.mail import MailConfig
from asfeslib.databases.MongoDB import connect_mongo, MongoConnectScheme
from asfeslib.weather.client import WeatherApiClient

MongoDB = MongoConnectScheme(db_url=mongodb_settings.URL)
Weather = WeatherApiClient(api_key=settings.WEATHER_API_KEY, lang="ru")

def create_mail_config() -> MailConfig:
    return MailConfig(
        host=mail_settings.SERVER_SMTP,
        port=mail_settings.PORT_SMTP,
        username=mail_settings.USERNAME or "noreply@asfes.ru",
        password=mail_settings.PASSWORD or "testpass123",
        from_name="ASFES Mailer",
        retry_count=3,
        retry_delay=1.0,
        rate_limit=0.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mailcfg = create_mail_config()
    app.state.weatherclient = Weather

    client, db, status = await connect_mongo(MongoDB)
    app.state.mongo_client = client
    app.state.mongo_db = db
    app.state.mongo_status = status

    if not status:
        print("MongoDB connection failed")

    yield

    try:
        client.close()
    except:
        pass


app = FastAPI(
    title="Зовниковы победят!",
    debug=settings.DEV,
    lifespan=lifespan,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEV else None,
    redoc_url="/redoc" if settings.DEV else None,
    openapi_url="/api/v1/openapi.json" if settings.DEV else None,
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.headers.get("X-Forwarded-Proto", "") == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=15552000; includeSubDomains"
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

from server.routes import (
    health,
    test_mail,
    )

for router in (
    health.router,
    test_mail.router
):
    app.include_router(router)
