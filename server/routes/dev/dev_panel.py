from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse

from server.core.config import settings, vk_settings

router = APIRouter(tags=["dev"])


def _ensure_dev():
    if not settings.DEV:
        return RedirectResponse(
            url="/",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return None


@router.get("/dev", response_class=HTMLResponse)
async def dev_panel(request: Request):
    if (redirect := _ensure_dev()) is not None:
        return redirect

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "dev_panel.html",
        {
            "request": request,
            "dev": settings.DEV,
            "vk_client_id": vk_settings.CLIENT_ID,
            "vk_redirect_url": vk_settings.REDIRECT_URI,
        },
    )