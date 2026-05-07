from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://auction:auction@postgres:5432/auction"
    redis_url: str = "redis://redis:6379/0"
    auction_cache_ttl_seconds: int = 30


settings = Settings()
