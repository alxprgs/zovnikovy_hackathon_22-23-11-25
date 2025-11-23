from __future__ import annotations

from typing import Optional, Final
from functools import lru_cache

from pydantic import Field, AnyUrl, EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DEV: bool = Field(True)

    DOMAIN_WITHOUT_WWW: str = Field("asfes.ru")
    DOMAIN: str = Field("hackathon.asfes.ru")

    PORT: int = Field(9105)
    RELOAD: int = Field(0)

    VERSION: str = Field("1.0.0")
 
    WEATHER_API_KEY: str = Field(...)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

class RootUser(BaseSettings):
    LOGIN: str = Field(..., min_length=3)
    PASSWORD: str = Field(..., min_length=8)
    MAIL: EmailStr = Field(default="admin@asfes.ru")

    model_config = SettingsConfigDict(
        env_prefix="ROOT_USER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class JWTSettings(BaseSettings):
    SECRET_KEY: str = Field(...)
    ALGORITHM: str = Field("HS256")
    TOKEN_EXPIRE_SEC: int = Field(60 * 60)

    model_config = SettingsConfigDict(
        env_prefix="JWT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class MailSettings(BaseSettings):
    USERNAME: EmailStr | None = None
    FROM: EmailStr | None = None

    PORT_IMAP: int = Field(993)
    PORT_SMTP: int = Field(465)
    SERVER_IMAP: str | None = None
    SERVER_SMTP: str | None = None

    SSL: bool = True
    PASSWORD: str | None = Field(None, min_length=6)

    model_config = SettingsConfigDict(
        env_prefix="MAIL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def fill_defaults(self):
        base_domain = get_settings().DOMAIN_WITHOUT_WWW

        if not self.USERNAME:
            self.USERNAME = f"noreply@{base_domain}"

        if not self.FROM:
            self.FROM = self.USERNAME

        if not self.SERVER_IMAP:
            self.SERVER_IMAP = f"mail.{base_domain}"

        if not self.SERVER_SMTP:
            self.SERVER_SMTP = f"mail.{base_domain}"

        return self


class DatabaseConfig(BaseSettings):
    URL: Optional[AnyUrl] = None

    USER: Optional[str] = None
    PASSWORD: Optional[str] = None
    HOST: Optional[str] = None
    PORT: Optional[int] = None
    NAME: Optional[str] = None

    SCHEME: str = Field(..., min_length=3)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def assemble_url(self):
        if self.URL:
            return self

        missing = [
            f for f in ["USER", "PASSWORD", "HOST", "PORT", "NAME"]
            if getattr(self, f) is None
        ]

        if missing:
            raise ValueError(
                f"Missing DB fields ({', '.join(missing)}) and URL is not provided."
            )

        self.URL = (
            f"{self.SCHEME}://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )

        return self


class MongoDB(DatabaseConfig):
    SCHEME: str = "mongodb"
    model_config = SettingsConfigDict(
        env_prefix="MONGO_",
        env_file=".env",
        extra="ignore"
    )


class PostgreSQL(DatabaseConfig):
    SCHEME: str = "postgresql+asyncpg"
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        extra="ignore"
    )


class MySQL(DatabaseConfig):
    SCHEME: str = "mysql+aiomysql"
    model_config = SettingsConfigDict(
        env_prefix="MYSQL_",
        env_file=".env",
        extra="ignore"
    )


@lru_cache
def get_root_user_settings() -> RootUser:
    return RootUser()

@lru_cache
def get_jwt_settings() -> JWTSettings:
    return JWTSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_mail_settings() -> MailSettings:
    return MailSettings()


@lru_cache
def get_postgresql_settings() -> PostgreSQL:
    return PostgreSQL()


@lru_cache
def get_mongodb_settings() -> MongoDB:
    return MongoDB()


@lru_cache
def get_mysql_settings() -> MySQL:
    return MySQL()


settings: Final = get_settings()
root_user_settings: Final = get_root_user_settings()
jwt_settings: Final = get_jwt_settings()
mail_settings: Final = get_mail_settings()
postgresql_settings: Final = get_postgresql_settings()
mongodb_settings: Final = get_mongodb_settings()
mysql_settings: Final = get_mysql_settings()