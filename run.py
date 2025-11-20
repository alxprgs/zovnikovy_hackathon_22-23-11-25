from __future__ import annotations

import os
import asyncio
import sys
import uvicorn
from server.core.config import settings


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


async def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", settings.PORT))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    reload_enabled = settings.DEV and env_bool("RELOAD", False)

    config = uvicorn.Config(
        os.getenv("APP", "server:app"),
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=log_level,
        proxy_headers=True,
        forwarded_allow_ips="*",
        lifespan="on",
    )

    try:
        import uvloop  # type: ignore
        config.loop = "uvloop"
    except ImportError:
        pass

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nСервер остановлен пользователем.")
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        sys.exit(1)
