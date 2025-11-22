from __future__ import annotations
from datetime import datetime
from server.core.config import root_user_settings
from server.core.functions.hash_utils import hash_password
from fastapi import Request

async def init_root_user(log: bool = False):
    from server import app
    db = app.state.mongo_db

    await db["users"].create_index([("login", 1)], unique=True)
    await db["users"].create_index([("company_id", 1)])
    await db["companies"].create_index([("name", 1)], unique=True)
    await db["warehouses"].create_index([("company_id", 1)])
    await db["warehouses"].create_index([("camera_api_key", 1)], unique=True, sparse=True)
    await db["items"].create_index([("warehouse_id", 1)])
    await db["items"].create_index([("warehouse_id", 1), ("name", 1)], unique=True)
    await db["history"].create_index([("item_id", 1), ("ts", -1)])
    await db["supplies"].create_index([("warehouse_id", 1), ("expected_at", 1)])

    login = root_user_settings.LOGIN
    password = root_user_settings.PASSWORD
    email = root_user_settings.MAIL

    existing = await db["users"].find_one({"login": login, "is_root": True})
    if existing:
        return

    doc = {
        "login": login,
        "password": hash_password(password),
        "email": email,
        "post": "root",
        "permissions": ["*"],
        "is_root": True,
        "is_ceo": False,
        "company_id": None,
        "created_at": datetime.utcnow(),
        "blocked_at": None,
        "deleted_at": None
    }

    await db["users"].insert_one(doc)
    if log:
        print("[ROOT] Root user created.")
