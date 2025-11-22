from __future__ import annotations

from datetime import datetime
from typing import Optional, List

import re
from pydantic import BaseModel, Field, field_validator


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_str(
    v,
    *,
    field: str,
    min_len: int | None = None,
    max_len: int | None = None,
    allow_empty: bool = False,
):
    if v is None:
        raise ValueError(f"{field}: поле обязательно")
    if not isinstance(v, str):
        raise ValueError(f"{field}: должно быть строкой")

    v = v.strip()

    if not allow_empty and v == "":
        raise ValueError(f"{field}: поле не может быть пустым")

    if min_len is not None and len(v) < min_len:
        raise ValueError(f"{field}: минимум {min_len} символов")

    if max_len is not None and len(v) > max_len:
        raise ValueError(f"{field}: максимум {max_len} символов")

    return v


def _validate_int(v, *, field: str, ge: int | None = None, gt: int | None = None):
    if v is None:
        raise ValueError(f"{field}: поле обязательно")
    try:
        iv = int(v)
    except Exception:
        raise ValueError(f"{field}: должно быть целым числом")

    if ge is not None and iv < ge:
        raise ValueError(f"{field}: должно быть не меньше {ge}")

    if gt is not None and iv <= gt:
        raise ValueError(f"{field}: должно быть больше {gt}")

    return iv


def _validate_email(v, *, field: str = "email"):
    v = _validate_str(v, field=field, min_len=3, max_len=320)
    if not _EMAIL_RE.match(v):
        raise ValueError(f"{field}: некорректный email")
    return v

class RegisterCEO(BaseModel):
    company_name: str = Field(...)
    company_inn: Optional[str] = Field(None)

    login: str = Field(...)
    password: str = Field(...)
    email: str = Field(...)

    @field_validator("company_name")
    @classmethod
    def v_company_name(cls, v):
        return _validate_str(v, field="company_name", min_len=2, max_len=120)

    @field_validator("company_inn")
    @classmethod
    def v_company_inn(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        v = _validate_str(v, field="company_inn", max_len=20)
        if not v.isdigit():
            raise ValueError("company_inn: ИНН должен содержать только цифры")
        return v

    @field_validator("login")
    @classmethod
    def v_login(cls, v):
        return _validate_str(v, field="login", min_len=3, max_len=64)

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        return _validate_str(v, field="password", min_len=8, max_len=128)

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        return _validate_email(v)


class Login(BaseModel):
    login: str
    password: str

    @field_validator("login")
    @classmethod
    def v_login(cls, v):
        return _validate_str(v, field="login", min_len=1, max_len=64)

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        return _validate_str(v, field="password", min_len=1, max_len=128)


class CreateEmployee(BaseModel):
    login: str = Field(...)
    password: str = Field(...)
    email: str = Field(...)
    post: str = Field(...)
    permissions: List[str] = Field(default_factory=list)

    @field_validator("login")
    @classmethod
    def v_login(cls, v):
        return _validate_str(v, field="login", min_len=3, max_len=64)

    @field_validator("password")
    @classmethod
    def v_password(cls, v):
        return _validate_str(v, field="password", min_len=8, max_len=128)

    @field_validator("email")
    @classmethod
    def v_email(cls, v):
        return _validate_email(v)

    @field_validator("post")
    @classmethod
    def v_post(cls, v):
        return _validate_str(v, field="post", min_len=1, max_len=120)

    @field_validator("permissions")
    @classmethod
    def v_permissions(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("permissions: должно быть списком строк")
        out = []
        for p in v:
            if not isinstance(p, str):
                raise ValueError("permissions: каждый элемент должен быть строкой")
            ps = p.strip()
            if ps:
                out.append(ps)
        return out


class UpdateEmployeePerms(BaseModel):
    user_id: str
    post: Optional[str] = None
    permissions: Optional[List[str]] = None
    blocked: Optional[bool] = None

    @field_validator("user_id")
    @classmethod
    def v_user_id(cls, v):
        return _validate_str(v, field="user_id", min_len=1, max_len=128)

    @field_validator("post")
    @classmethod
    def v_post(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="post", min_len=1, max_len=120)

    @field_validator("permissions")
    @classmethod
    def v_permissions(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("permissions: должно быть списком строк")
        out = []
        for p in v:
            if not isinstance(p, str):
                raise ValueError("permissions: каждый элемент должен быть строкой")
            ps = p.strip()
            if ps:
                out.append(ps)
        return out


class UpdateCompany(BaseModel):
    name: Optional[str] = Field(None)
    inn: Optional[str] = Field(None)

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="name", min_len=2, max_len=120)

    @field_validator("inn")
    @classmethod
    def v_inn(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        v = _validate_str(v, field="inn", max_len=20)
        if not v.isdigit():
            raise ValueError("inn: ИНН должен содержать только цифры")
        return v

class CreateWarehouse(BaseModel):
    name: str = Field(...)
    notification_emails: List[str] = Field(default_factory=list)
    low_stock_default: int = Field(1)

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        return _validate_str(v, field="name", min_len=1, max_len=120)

    @field_validator("notification_emails")
    @classmethod
    def v_notification_emails(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("notification_emails: должен быть списком email")
        out = []
        for e in v:
            out.append(_validate_email(e, field="notification_emails"))
        return out

    @field_validator("low_stock_default")
    @classmethod
    def v_low_stock_default(cls, v):
        return _validate_int(v, field="low_stock_default", ge=0)


class UpdateWarehouse(BaseModel):
    warehouse_id: str
    name: Optional[str] = None
    notification_emails: Optional[List[str]] = None
    low_stock_default: Optional[int] = None

    @field_validator("warehouse_id")
    @classmethod
    def v_warehouse_id(cls, v):
        return _validate_str(v, field="warehouse_id", min_len=1, max_len=128)

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="name", min_len=1, max_len=120)

    @field_validator("notification_emails")
    @classmethod
    def v_notification_emails(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("notification_emails: должен быть списком email")
        out = []
        for e in v:
            out.append(_validate_email(e, field="notification_emails"))
        return out

    @field_validator("low_stock_default")
    @classmethod
    def v_low_stock_default(cls, v):
        if v is None:
            return None
        return _validate_int(v, field="low_stock_default", ge=0)
    

class CreateItem(BaseModel):
    warehouse_id: str
    name: str = Field(...)
    category: str = Field("other")
    unit: str = Field("шт")
    count: int = Field(0)
    low_limit: Optional[int] = Field(None)

    @field_validator("warehouse_id")
    @classmethod
    def v_warehouse_id(cls, v):
        return _validate_str(v, field="warehouse_id", min_len=1, max_len=128)

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        return _validate_str(v, field="name", min_len=1, max_len=120)

    @field_validator("category")
    @classmethod
    def v_category(cls, v):
        if v is None:
            return "other"
        return _validate_str(v, field="category", min_len=1, max_len=120)

    @field_validator("unit")
    @classmethod
    def v_unit(cls, v):
        if v is None:
            return "шт"
        return _validate_str(v, field="unit", min_len=1, max_len=20)

    @field_validator("count")
    @classmethod
    def v_count(cls, v):
        return _validate_int(v, field="count", ge=0)

    @field_validator("low_limit")
    @classmethod
    def v_low_limit(cls, v):
        if v is None:
            return None
        return _validate_int(v, field="low_limit", ge=0)


class UpdateItem(BaseModel):
    item_id: str
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    low_limit: Optional[int] = None

    @field_validator("item_id")
    @classmethod
    def v_item_id(cls, v):
        return _validate_str(v, field="item_id", min_len=1, max_len=128)

    @field_validator("name")
    @classmethod
    def v_name(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="name", min_len=1, max_len=120)

    @field_validator("category")
    @classmethod
    def v_category(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="category", min_len=1, max_len=120)

    @field_validator("unit")
    @classmethod
    def v_unit(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="unit", min_len=1, max_len=20)

    @field_validator("low_limit")
    @classmethod
    def v_low_limit(cls, v):
        if v is None:
            return None
        return _validate_int(v, field="low_limit", ge=0)


class ItemOp(BaseModel):
    item_id: str
    amount: int = Field(...)

    @field_validator("item_id")
    @classmethod
    def v_item_id(cls, v):
        return _validate_str(v, field="item_id", min_len=1, max_len=128)

    @field_validator("amount")
    @classmethod
    def v_amount(cls, v):
        return _validate_int(v, field="amount", gt=0)

class CreateSupply(BaseModel):
    warehouse_id: str
    item_id: str
    amount: int = Field(...)
    expected_at: datetime
    note: Optional[str] = Field(None)

    @field_validator("warehouse_id")
    @classmethod
    def v_warehouse_id(cls, v):
        return _validate_str(v, field="warehouse_id", min_len=1, max_len=128)

    @field_validator("item_id")
    @classmethod
    def v_item_id(cls, v):
        return _validate_str(v, field="item_id", min_len=1, max_len=128)

    @field_validator("amount")
    @classmethod
    def v_amount(cls, v):
        return _validate_int(v, field="amount", gt=0)

    @field_validator("expected_at", mode="before")
    @classmethod
    def v_expected_at(cls, v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                raise ValueError("expected_at: некорректная дата/время (нужен ISO формат)")
        raise ValueError("expected_at: некорректная дата/время")

    @field_validator("note")
    @classmethod
    def v_note(cls, v):
        if v is None:
            return None
        return _validate_str(v, field="note", max_len=300, allow_empty=True)


class UpdateSupplyStatus(BaseModel):
    supply_id: str
    status: str

    @field_validator("supply_id")
    @classmethod
    def v_supply_id(cls, v):
        return _validate_str(v, field="supply_id", min_len=1, max_len=128)

    @field_validator("status")
    @classmethod
    def v_status(cls, v):
        v = _validate_str(v, field="status", min_len=1, max_len=20)
        if v not in ("waiting", "done", "canceled"):
            raise ValueError("status: допустимые значения: waiting, done, canceled")
        return v

class CameraAuth(BaseModel):
    company: str
    warehouse_id: str
    api_key: str

    @field_validator("company")
    @classmethod
    def v_company(cls, v):
        return _validate_str(v, field="company", min_len=1, max_len=128)

    @field_validator("warehouse_id")
    @classmethod
    def v_warehouse_id(cls, v):
        return _validate_str(v, field="warehouse_id", min_len=1, max_len=128)

    @field_validator("api_key")
    @classmethod
    def v_api_key(cls, v):
        return _validate_str(v, field="api_key", min_len=1, max_len=256)


class CameraDetectItem(BaseModel):
    type: str
    count: int = Field(...)

    @field_validator("type")
    @classmethod
    def v_type(cls, v):
        return _validate_str(v, field="type", min_len=1, max_len=64)

    @field_validator("count")
    @classmethod
    def v_count(cls, v):
        return _validate_int(v, field="count", ge=0)


class CameraDetectPayload(BaseModel):
    detect: List[CameraDetectItem]

    @field_validator("detect")
    @classmethod
    def v_detect(cls, v):
        if not isinstance(v, list) or not v:
            raise ValueError("detect: должен быть непустой список")
        return v