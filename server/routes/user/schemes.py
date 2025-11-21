from __future__ import annotations

from pydantic import BaseModel, Field


class AuthSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class CreateUserSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    permissions: dict


class UpdateUserSchema(BaseModel):
    login: str
    updates: dict