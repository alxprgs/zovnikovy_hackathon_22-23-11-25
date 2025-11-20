import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from server.routes.health import router


@pytest.mark.asyncio
async def test_health_check():
    app = FastAPI()
    app.include_router(router)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/healthz")

    assert response.status_code == 200
    assert response.text == "ok"
