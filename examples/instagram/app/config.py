from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://instagram:instagram@localhost:54321/instagram")
    s3_internal_endpoint: str = Field(default="http://localhost:8211")
    s3_public_endpoint: str = Field(default="http://localhost:8211")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="instagram-media")
    presigned_url_ttl_seconds: int = Field(default=900)


settings = Settings()
