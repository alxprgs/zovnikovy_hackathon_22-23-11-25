from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel

from server.core.db_utils import oid
from server.routes.schemes import CameraAuth, CameraDetectPayload

router = APIRouter(tags=["Camera HTTP"])


class CameraDetectRequest(BaseModel):
    auth: CameraAuth
    payload: CameraDetectPayload


@router.post("/camera")
async def camera_http(request: Request, data: CameraDetectRequest):
    app = request.app
    db = app.state.mongo_db

    auth = data.auth
    payload = data.payload

    try:
        wh_oid = oid(auth.warehouse_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный warehouse_id."
        )

    wh = await db["warehouses"].find_one({
        "_id": wh_oid,
        "deleted_at": None,
        "camera_api_key": auth.api_key
    })
    if not wh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка авторизации камеры."
        )

    company = await db["companies"].find_one({
        "_id": wh["company_id"],
        "deleted_at": None
    })
    if not company or company.get("name") != auth.company:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Компания не совпадает."
        )

    now = datetime.now(timezone.utc)

    for det in payload.detect:
        item = await db["items"].find_one({
            "warehouse_id": wh["_id"],
            "name": det.type,
            "deleted_at": None
        })

        if not item:
            item_doc = {
                "warehouse_id": wh["_id"],
                "name": det.type,
                "category": "auto",
                "unit": "шт",
                "count": det.count,
                "low_limit": None,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None
            }
            item_id = (await db["items"].insert_one(item_doc)).inserted_id

            await db["history"].insert_one({
                "item_id": item_id,
                "warehouse_id": wh["_id"],
                "type": "camera_update",
                "amount": det.count,
                "ts": now,
                "by_user_id": None
            })
            continue

        old_count = item["count"]
        new_count = det.count

        if new_count != old_count:
            await db["items"].update_one(
                {"_id": item["_id"]},
                {"$set": {"count": new_count, "updated_at": now}}
            )

            await db["history"].insert_one({
                "item_id": item["_id"],
                "warehouse_id": wh["_id"],
                "type": "camera_update",
                "amount": new_count - old_count,
                "ts": now,
                "by_user_id": None
            })

            low_limit = item.get("low_limit")
            if low_limit is None:
                low_limit = wh.get("low_stock_default", 1)

            if new_count <= low_limit and wh.get("notification_emails"):
                from server.core.mailer import send_low_stock_email
                await send_low_stock_email(
                    request_app=app,
                    to_list=wh["notification_emails"],
                    item_name=item["name"],
                    count=new_count,
                    low_limit=low_limit,
                    warehouse_name=wh["name"]
                )

    return {
        "ok": True,
        "warehouse": wh["name"],
        "updated": len(payload.detect)
    }
