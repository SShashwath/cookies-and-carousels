from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://foodmatch:foodmatch@127.0.0.1:5432/foodmatch"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    restaurant_provider: Literal["mock", "google"] = "mock"
    google_places_api_key: str = ""
    room_ttl_hours: int = Field(default=24, ge=1, le=168)
    rate_limit_client_ip_header: Literal["", "x-real-ip"] = ""

    @property
    def sqlalchemy_url(self) -> str:
        scheme, separator, rest = self.database_url.partition("://")
        if scheme in {"postgres", "postgresql"} and separator:
            return f"postgresql+psycopg://{rest}"
        return self.database_url


@lru_cache
def settings() -> Settings:
    return Settings()
