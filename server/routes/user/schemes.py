from __future__ import annotations

from pydantic import BaseModel, Field, EmailStr


class AuthSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class RegistrSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    mail: EmailStr = Field(...)
    company: str = Field(...)



class CreateUserSchema(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    permissions: dict


class UpdateUserSchema(BaseModel):
    login: str
    updates: dict

class UpdateUserSetPost(BaseModel):
    login: str
    post: str
    status: bool