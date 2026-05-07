from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://comments:comments@postgres:5432/comments"
    redis_url: str = "redis://redis:6379/0"
    stream_max_len: int = 1000


settings = Settings()
