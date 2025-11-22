from __future__ import annotations

from bson import ObjectId
from datetime import datetime, date
from typing import Any, Dict

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source, handler):
        return handler(ObjectId)

def oid(v: str | ObjectId) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    return ObjectId(v)

def to_jsonable(x: Any) -> Any:
    if isinstance(x, ObjectId):
        return str(x)

    if isinstance(x, (datetime, date)):
        return x.isoformat()

    if isinstance(x, list):
        return [to_jsonable(i) for i in x]

    if isinstance(x, tuple):
        return [to_jsonable(i) for i in x]

    if isinstance(x, dict):
        out: Dict[str, Any] = {}
        for k, v in x.items():
            if k == "_id":
                out["id"] = to_jsonable(v)
            else:
                out[k] = to_jsonable(v)
        return out

    return x

def public_id(doc: dict) -> dict:
    return to_jsonable(doc) if doc else doc
