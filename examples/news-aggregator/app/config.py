from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://news:news@localhost:5438/news")
    redis_url: str = Field(default="redis://localhost:6384/0")
    feed_cache_ttl_seconds: int = Field(default=60)


settings = Settings()
