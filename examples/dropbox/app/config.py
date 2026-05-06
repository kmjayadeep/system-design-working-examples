from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://dropbox:dropbox@localhost:5433/dropbox")
    s3_internal_endpoint: str = Field(default="http://localhost:9001")
    s3_public_endpoint: str = Field(default="http://localhost:9001")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="dropbox-files")
    presigned_url_ttl_seconds: int = Field(default=900)


settings = Settings()
