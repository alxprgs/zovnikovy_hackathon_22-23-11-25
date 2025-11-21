from __future__ import annotations

from asfeslib.core.logger import Logger
from asfeslib.databases.MongoDB import MongoConnectScheme, connect_mongo
from motor.motor_asyncio import AsyncIOMotorDatabase

from server.core.config import mongodb_settings, root_user_settings
from server.core.functions.hash_utils import verify_password, hash_password

logger = Logger(__name__)


async def init_root_user(log: bool) -> bool:
    temp_client = None

    try:
        from server import app
        db_from_state = getattr(app.state, "mongo_db", None)

        if db_from_state is None:
            MongoDB = MongoConnectScheme(db_url=mongodb_settings.URL)
            client, db, _ = await connect_mongo(MongoDB)
            db: AsyncIOMotorDatabase
            temp_client = client
            if log:
                logger.info("Подключение к базе данных отдельным клиентом.")
        else:
            db = app.state.mongo_db
            if log:
                logger.info("База данных получена из app.state.mongo_db.")

        root_user_login = root_user_settings.LOGIN
        root_user_password = root_user_settings.PASSWORD

        if not root_user_login or not root_user_password:
            logger.critical(
                "Отсутствует логин или пароль root юзера в .env, запуск невозможен."
            )
            raise RuntimeError("Missing root credentials")

        root_user = await db["users"].find_one({"login": root_user_login})

        if root_user:
            stored_hash = root_user.get("password")
            if not stored_hash or not isinstance(stored_hash, str):
                new_hash = hash_password(root_user_password)
                await db["users"].update_one(
                    {"_id": root_user["_id"]},
                    {"$set": {"password": new_hash, "permissions.root": True}},
                )
                if log:
                    logger.info("Исправлен повреждённый root-юзер.")
                return True

            if not verify_password(root_user_password, stored_hash):
                await db["users"].update_one(
                    {"_id": root_user["_id"]},
                    {
                        "$set": {
                            "password": hash_password(root_user_password),
                            "permissions.root": True,
                        }
                    },
                )
                if log:
                    logger.info("Успешно изменён пароль root юзера.")
                return True

            if log:
                logger.info("Изменения root юзера не требуются.")
            return True

        await db["users"].insert_one({
            "login": root_user_login,
            "password": hash_password(root_user_password),
            "permissions": {"root": True},
        })
        if log:
            logger.info("Успешно создан root юзер.")
        return True

    except Exception as e:
        if log:
            logger.error(f"Ошибка создания/обновления root юзера: '{e}'.")
        return False

    finally:
        if temp_client:
            temp_client.close()