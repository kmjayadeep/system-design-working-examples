from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://scheduler:scheduler@postgres:5432/scheduler"
    redis_url: str = "redis://redis:6379/0"


settings = Settings()
