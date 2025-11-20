from __future__ import annotations

from pathlib import Path
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

    VERSION: str = Field("0.0.1")

    WEATHER_API_KEY: str = Field(...)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class MailSettings(BaseSettings):
    MAIL_USERNAME: EmailStr | None = None
    MAIL_FROM: EmailStr | None = None

    MAIL_PORT_IMAP: int = Field(993, ge=1, le=65535)
    MAIL_PORT_SMTP: int = Field(465, ge=1, le=65535)
    MAIL_PORT_BASE: int = Field(465, ge=1, le=65535)

    MAIL_SERVER_IMAP: str | None = None
    MAIL_SERVER_SMTP: str | None = None

    MAIL_SSL: bool = Field(True)
    MAIL_PASSWORD: str | None = Field(None, min_length=6)

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

        if not self.MAIL_USERNAME:
            self.MAIL_USERNAME = f"noreply@{base_domain}"

        if not self.MAIL_FROM:
            self.MAIL_FROM = f"noreply@{base_domain}"

        if not self.MAIL_SERVER_IMAP:
            self.MAIL_SERVER_IMAP = f"mail.{base_domain}"

        if not self.MAIL_SERVER_SMTP:
            self.MAIL_SERVER_SMTP = f"mail.{base_domain}"

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
mail_settings: Final = get_mail_settings()
postgresql_settings: Final = get_postgresql_settings()
mongodb_settings: Final = get_mongodb_settings()
mysql_settings: Final = get_mysql_settings()
