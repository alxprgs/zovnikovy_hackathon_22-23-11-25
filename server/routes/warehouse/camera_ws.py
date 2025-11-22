from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from server.core.db_utils import oid
from server.routes.schemes import CameraAuth, CameraDetectPayload

router = APIRouter(tags=["Camera WS"])

@router.websocket("/ws/warehouse/{warehouse_id}/camera")
async def camera_ws(ws: WebSocket, warehouse_id: str):
    await ws.accept()
    app = ws.app
    db = app.state.mongo_db

    try:
        auth_msg = await ws.receive_json()
        auth = CameraAuth(**auth_msg)
        if auth.warehouse_id != warehouse_id:
            await ws.send_json({"ok": False, "error": "warehouse_id_mismatch"})
            await ws.close()
            return

        wh = await db["warehouses"].find_one({
            "_id": oid(auth.warehouse_id),
            "deleted_at": None,
            "camera_api_key": auth.api_key
        })
        if not wh:
            await ws.send_json({"ok": False, "error": "auth_failed"})
            await ws.close()
            return

        company = await db["companies"].find_one({"_id": wh["company_id"], "deleted_at": None})
        if not company or company["name"] != auth.company:
            await ws.send_json({"ok": False, "error": "company_mismatch"})
            await ws.close()
            return

        await ws.send_json({"ok": True, "warehouse": wh["name"]})

        while True:
            data = await ws.receive_json()
            payload = CameraDetectPayload(**data)

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
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "deleted_at": None
                    }
                    item_id = (await db["items"].insert_one(item_doc)).inserted_id
                    await db["history"].insert_one({
                        "item_id": item_id,
                        "warehouse_id": wh["_id"],
                        "type": "camera_update",
                        "amount": det.count,
                        "ts": datetime.now(timezone.utc),
                        "by_user_id": None
                    })
                    continue

                old_count = item["count"]
                new_count = det.count

                if new_count != old_count:
                    await db["items"].update_one(
                        {"_id": item["_id"]},
                        {"$set": {"count": new_count, "updated_at": datetime.now(timezone.utc)}}
                    )
                    await db["history"].insert_one({
                        "item_id": item["_id"],
                        "warehouse_id": wh["_id"],
                        "type": "camera_update",
                        "amount": new_count - old_count,
                        "ts": datetime.now(timezone.utc),
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

            await ws.send_json({"ok": True})

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await ws.send_json({"ok": False, "error": str(e)})
        finally:
            await ws.close()
