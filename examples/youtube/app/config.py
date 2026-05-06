from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://youtube:youtube@localhost:5435/youtube")
    redis_url: str = Field(default="redis://localhost:6381/0")
    s3_internal_endpoint: str = Field(default="http://localhost:9011")
    s3_public_endpoint: str = Field(default="http://localhost:9011")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="youtube-videos")
    presigned_url_ttl_seconds: int = Field(default=900)
    video_metadata_cache_ttl_seconds: int = Field(default=60)


settings = Settings()
