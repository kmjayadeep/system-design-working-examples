from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://prices:prices@postgres:5432/prices"
    redis_url: str = "redis://redis:6379/0"
    price_history_cache_ttl_seconds: int = 60


settings = Settings()
