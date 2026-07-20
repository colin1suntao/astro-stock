import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASTRO_", extra="ignore")

    # Runtime
    debug: bool = False

    # Database — SQLite for dev (zero deps), Postgres in prod via env override.
    # Priority: DATABASE_URL (e.g. Railway's Postgres service) > ASTRO_DB_URL > SQLite default.
    db_url: str = os.environ.get("DATABASE_URL") or "sqlite:///./data/astrostock.db"

    def __init__(self, **data):
        # Read DATABASE_URL directly from the environment before pydantic
        # settings resolution runs, so Railway's Postgres URL always wins
        # over the ASTRO_DB_URL env var (or the default env parsing) here.
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            data["db_url"] = database_url
        super().__init__(**data)

    # JWT
    jwt_secret: str = "dev-secret-change-in-prod"
    jwt_algo: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 1 day

    # LLM (LongCat, OpenAI-compatible)
    llm_base_url: str = "https://api.longcat.chat/openai/v1/chat/completions"
    llm_api_key: str = "ak_2fC5bH7f63pz9Fo2aD5ce3lp57i8j"
    llm_model: str = "LongCat-2.0"
    llm_max_tokens: int = 1500  # reasoning models eat tokens; leave room for body

    # Swiss Ephemeris
    ephem_path: str = "./data/swisseph"

    # Market data
    yfinance_cache_dir: str = "./data/yfinance_cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
