from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


class RegisterCEO(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=120)
    company_inn: Optional[str] = Field(None, max_length=20)

    login: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr

class Login(BaseModel):
    login: str
    password: str

class CreateEmployee(BaseModel):
    login: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr
    post: str = Field(..., min_length=1, max_length=120)
    permissions: List[str] = Field(default_factory=list)

class UpdateEmployeePerms(BaseModel):
    user_id: str
    post: Optional[str] = None
    permissions: Optional[List[str]] = None
    blocked: Optional[bool] = None


class UpdateCompany(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    inn: Optional[str] = Field(None, max_length=20)


class CreateWarehouse(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    notification_emails: List[EmailStr] = Field(default_factory=list)
    low_stock_default: int = Field(1, ge=0)

class UpdateWarehouse(BaseModel):
    warehouse_id: str
    name: Optional[str] = None
    notification_emails: Optional[List[EmailStr]] = None
    low_stock_default: Optional[int] = Field(None, ge=0)


class CreateItem(BaseModel):
    warehouse_id: str
    name: str = Field(..., min_length=1, max_length=120)
    category: str = Field("other", max_length=120)
    unit: str = Field("шт", max_length=20)
    count: int = Field(0, ge=0)
    low_limit: Optional[int] = Field(None, ge=0)

class UpdateItem(BaseModel):
    item_id: str
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    low_limit: Optional[int] = Field(None, ge=0)

class ItemOp(BaseModel):
    item_id: str
    amount: int = Field(..., gt=0)

class CreateSupply(BaseModel):
    warehouse_id: str
    item_id: str
    amount: int = Field(..., gt=0)
    expected_at: datetime
    note: Optional[str] = Field(None, max_length=300)

class UpdateSupplyStatus(BaseModel):
    supply_id: str
    status: Literal["waiting", "done", "canceled"]

class CameraAuth(BaseModel):
    company: str
    warehouse_id: str
    api_key: str

class CameraDetectItem(BaseModel):
    type: str
    count: int = Field(..., ge=0)

class CameraDetectPayload(BaseModel):
    detect: List[CameraDetectItem]
