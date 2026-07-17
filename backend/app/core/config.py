from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASTRO_", extra="ignore")

    # Runtime
    debug: bool = False

    # Database — SQLite for dev (zero deps), Postgres in prod via env override
    db_url: str = "sqlite:///./data/astrostock.db"

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
