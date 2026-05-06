from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://yelp:yelp@localhost:5439/yelp")
    redis_url: str = Field(default="redis://localhost:6385/0")
    search_cache_ttl_seconds: int = Field(default=60)


settings = Settings()
