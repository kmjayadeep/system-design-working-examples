from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://bitly:bitly@localhost:5432/bitly")
    redis_url: str = Field(default="redis://localhost:6379/0")
    base_url: str = Field(default="http://localhost:8000")
    counter_xor_secret: int = Field(default=11259375)
    cleanup_interval_seconds: int = Field(default=30)


settings = Settings()
