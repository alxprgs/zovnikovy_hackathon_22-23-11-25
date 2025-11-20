from __future__ import annotations

from pathlib import Path
from typing import Optional, Final
from pydantic import Field, AnyUrl, ValidationError, model_validator,EmailStr
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


settings: Final = Settings()


class MailSettings(BaseSettings):
    MAIL_USERNAME: EmailStr = Field(
        default_factory=lambda: f"hackathon@{settings.DOMAIN_WITHOUT_WWW}"
    )
    MAIL_FROM: EmailStr = Field(
        default_factory=lambda: f"hackathon@{settings.DOMAIN_WITHOUT_WWW}"
    )

    MAIL_PORT_IMAP: int = Field(993, ge=1, le=65535)
    MAIL_PORT_SMTP: int = Field(465, ge=1, le=65535)
    MAIL_PORT_BASE: int = Field(465, ge=1, le=65535)

    MAIL_SERVER_IMAP: str = Field(
        default_factory=lambda: f"mail.{settings.DOMAIN_WITHOUT_WWW}"
    )
    MAIL_SERVER_SMTP: str = Field(
        default_factory=lambda: f"mail.{settings.DOMAIN_WITHOUT_WWW}"
    )

    MAIL_SSL: bool = Field(True)
    MAIL_PASSWORD: str = Field(..., min_length=6)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

mail_settings: Final = MailSettings()

class DatabaseConfig(BaseSettings):
    URL: Optional[AnyUrl] = Field(default=None)

    USER: Optional[str] = None
    PASSWORD: Optional[str] = None
    HOST: Optional[str] = None
    PORT: Optional[int] = None
    NAME: Optional[str] = None

    SCHEME: str = Field(..., min_length=3)

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )

    @model_validator(mode="after")
    def assemble_url(self):
        if self.URL:
            return self

        missing = [field for field in ["USER", "PASSWORD", "HOST", "PORT", "NAME"]
                if getattr(self, field) is None]

        if missing:
            raise ValueError(
                f"Missing required database parameters: {', '.join(missing)}"
            )

        self.URL = (
            f"{self.SCHEME}://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )
        return self


class MongoDB(DatabaseConfig):
    SCHEME: str = "mongodb"
    model_config = SettingsConfigDict(env_prefix="MONGO_", extra="ignore", env_file=".env")


class PostgreSQL(DatabaseConfig):
    SCHEME: str = "postgresql+asyncpg"
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore", env_file=".env")


class MySQL(DatabaseConfig):
    SCHEME: str = "mysql+aiomysql"
    model_config = SettingsConfigDict(env_prefix="MYSQL_", extra="ignore", env_file=".env")


postgresql_settings = PostgreSQL()
mongodb_settings = MongoDB()
mysql_settings = MySQL()