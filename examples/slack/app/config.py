from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://slack:slack@postgres:5432/slack"
    redis_url: str = "redis://redis:6379/0"
    stream_max_len: int = 1000


settings = Settings()
