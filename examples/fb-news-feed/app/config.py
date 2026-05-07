from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://feed:feed@postgres:5432/feed"
    redis_url: str = "redis://redis:6379/0"
    feed_limit: int = 200


settings = Settings()
