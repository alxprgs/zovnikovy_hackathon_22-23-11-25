from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Final, List


IS_WINDOWS: Final = platform.system() == "Windows"
IN_GITHUB_ACTIONS: Final = os.getenv("GITHUB_ACTIONS") == "true"
BASE_DIR: Final = Path(__file__).resolve().parent.parent


def _detect_data_root() -> Path:
    if env_root := os.getenv("DATA_ROOT"):
        return Path(env_root).expanduser().resolve()

    if IN_GITHUB_ACTIONS:
        return (BASE_DIR / "core" / "data").resolve()

    if IS_WINDOWS:
        return (BASE_DIR / "core" / "data").resolve()

    return Path("/data")


DATA_ROOT: Final = _detect_data_root()


def _mkdir(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(
            f"Не удалось создать каталог {path}; "
            f"проверьте права или volume-mount Docker-контейнера."
        ) from exc
    return path


_WRITABLE_SUBDIRS: Final[List[str]] = ["db", "logs"]

for sub in _WRITABLE_SUBDIRS:
    _mkdir(DATA_ROOT / sub)


DB_DIR: Final = DATA_ROOT / "db"
LOG_DIR: Final = DATA_ROOT / "logs"

TEMPLATES_DIR: Final = BASE_DIR / "templates"
STATIC_DIR: Final = BASE_DIR / "static"

__all__ = [
    "IS_WINDOWS", "IN_GITHUB_ACTIONS",
    "BASE_DIR",
    "DB_DIR", "LOG_DIR",
    "TEMPLATES_DIR", "STATIC_DIR"
]
