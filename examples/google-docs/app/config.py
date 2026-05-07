from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://docs:docs@postgres:5432/docs"
    redis_url: str = "redis://redis:6379/0"
    stream_max_len: int = 1000


settings = Settings()
