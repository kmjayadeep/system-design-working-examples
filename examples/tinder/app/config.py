from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://tinder:tinder@postgres:5432/tinder"
    redis_url: str = "redis://redis:6379/0"
    feed_cache_ttl_seconds: int = 30


settings = Settings()
