from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Dict

from server.core.db_utils import oid, public_id


async def create_notification(
    db,
    *,
    company_id: Any,
    title: str,
    message: str,
    ntype: str = "info",
    warehouse_id: Optional[Any] = None,
    supply_id: Optional[Any] = None,
    item_id: Optional[Any] = None,
    by_user_id: Optional[Any] = None,
):
    now = datetime.now(timezone.utc)

    def _maybe_oid(x):
        if x is None:
            return None
        if isinstance(x, str):
            try:
                return oid(x)
            except Exception:
                return x
        return x

    doc: Dict[str, Any] = {
        "company_id": _maybe_oid(company_id),
        "warehouse_id": _maybe_oid(warehouse_id),
        "supply_id": _maybe_oid(supply_id),
        "item_id": _maybe_oid(item_id),
        "type": ntype,
        "title": title,
        "message": message,
        "read": False,
        "created_at": now,
        "by_user_id": _maybe_oid(by_user_id),
        "read_at": None,
        "read_by_user_id": None,
    }
    _id = (await db["notifications"].insert_one(doc)).inserted_id
    return public_id({**doc, "_id": _id})