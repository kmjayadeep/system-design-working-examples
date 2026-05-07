from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://robinhood:robinhood@postgres:5432/robinhood"
    redis_url: str = "redis://redis:6379/0"


settings = Settings()

