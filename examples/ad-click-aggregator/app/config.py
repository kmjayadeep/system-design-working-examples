from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql://ads:ads@localhost:5437/ads")
    redis_url: str = Field(default="redis://localhost:6383/0")


settings = Settings()
