from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@postgres:5432/strava"
    redis_url: str = "redis://redis:6379/0"
    live_ttl_seconds: int = 60 * 60


settings = Settings()
