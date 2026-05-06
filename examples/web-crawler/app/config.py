from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://crawler:crawler@localhost:5436/crawler")
    redis_url: str = Field(default="redis://localhost:6382/0")
    s3_internal_endpoint: str = Field(default="http://localhost:9021")
    s3_public_endpoint: str = Field(default="http://localhost:9021")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="crawler-pages")
    politeness_delay_seconds: int = Field(default=1)


settings = Settings()
