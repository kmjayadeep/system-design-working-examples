from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://tickets:tickets@postgres:5432/tickets"
    redis_url: str = "redis://redis:6379/0"
    event_cache_ttl_seconds: int = 30
    reservation_ttl_seconds: int = 300


settings = Settings()
