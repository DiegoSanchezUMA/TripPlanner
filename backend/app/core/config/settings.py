"""Configuración leída de variables de entorno (infra/env/.env en local)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    # Sin valor por defecto: así no hay credenciales escritas en el código.
    database_url: str


@lru_cache
def get_settings() -> Settings:
    # pydantic-settings rellena los campos desde el entorno; pyright no lo sabe.
    return Settings()  # pyright: ignore[reportCallIssue]
