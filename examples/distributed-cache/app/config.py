from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"
    cache_nodes: str = "cache-a,cache-b,cache-c"


settings = Settings()

