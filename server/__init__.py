from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates

from server.core.config import settings, mail_settings, mongodb_settings
from server.core.paths import STATIC_DIR, TEMPLATES_DIR
from asfeslib.net.mail import MailConfig
from fastapi.responses import FileResponse
from asfeslib.databases.MongoDB import connect_mongo, MongoConnectScheme
from asfeslib.weather.client import WeatherApiClient
from server.core.inti_root_user import init_root_user

import logging
from asfeslib.core.logger import Logger
from server.core.paths import LOG_DIR

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

LOG_LEVEL = logging.DEBUG if settings.DEV else logging.INFO

log = Logger(
    name="hackathon-api",
    log_to_file=True,
    log_file=str(LOG_DIR / "server.log"),
    level=LOG_LEVEL,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.log = log
    log.info("Starting app... DEV=%s", settings.DEV)

    app.state.mailcfg = create_mail_config()
    app.state.weatherclient = Weather
    log.debug("Mail + Weather clients prepared")

    client, db, status = await connect_mongo(MongoDB)
    app.state.mongo_client = client
    app.state.mongo_db = db
    app.state.mongo_status = status

    if status:
        log.info("MongoDB connected")
    else:
        log.error("MongoDB connection failed")

    await init_root_user(log=settings.DEV)

    yield

    try:
        client.close()
        log.info("MongoDB client closed")
    except Exception as e:
        log.warning("Mongo close error: %s", e)


app = FastAPI(
    title="Зовниковы победят!",
    debug=settings.DEV,
    lifespan=lifespan,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEV else None,
    redoc_url="/redoc" if settings.DEV else None,
    openapi_url="/api/v1/openapi.json" if settings.DEV else None,
)

class SecurityHeadersMiddleware:
    async def __call__(self, scope, receive, send):

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"permissions-policy"] = b"geolocation=(), microphone=(), camera=()"

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_wrapper)

    def __init__(self, app):
        self.app = app

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", include_in_schema=False)
async def root_index():
    return FileResponse(STATIC_DIR / "app" / "index.html")

from server.routes.health import router as health_router
from server.routes.user.registration import router as registration_router
from server.routes.user.authorization import router as auth_router
from server.routes.company.users import router as company_users_router
from server.routes.warehouse.manage import router as warehouse_manage_router
from server.routes.warehouse.items import router as items_router
from server.routes.warehouse.supplies import router as supplies_router
from server.routes.warehouse.camera_ws import router as camera_ws_router
from server.routes.root.companies import router as root_companies_router

for r in (
    health_router,
    registration_router,
    auth_router,
    company_users_router,
    warehouse_manage_router,
    items_router,
    supplies_router,
    camera_ws_router,
    root_companies_router,
):
    app.include_router(r)
