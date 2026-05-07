from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://payments:payments@postgres:5432/payments"
    redis_url: str = "redis://redis:6379/0"


settings = Settings()
