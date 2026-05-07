from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://search:search@postgres:5432/search"
    redis_url: str = "redis://redis:6379/0"
    search_cache_ttl_seconds: int = 30
    index_event_max_len: int = 1000


settings = Settings()
