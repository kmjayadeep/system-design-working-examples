from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://whatsapp:whatsapp@postgres:5432/whatsapp")
    redis_url: str = Field(default="redis://redis:6379/0")
    s3_internal_endpoint: str = Field(default="http://minio:9000")
    s3_public_endpoint: str = Field(default="http://localhost:8151")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="whatsapp-media")
    presigned_url_ttl_seconds: int = Field(default=900)


settings = Settings()
