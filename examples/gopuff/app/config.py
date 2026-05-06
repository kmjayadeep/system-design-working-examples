from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://gopuff:gopuff@localhost:5434/gopuff")
    redis_url: str = Field(default="redis://localhost:6380/0")
    availability_cache_ttl_seconds: int = Field(default=60)
    max_delivery_distance_km: float = Field(default=16)


settings = Settings()
