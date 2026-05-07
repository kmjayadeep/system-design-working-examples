from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://leetcode:leetcode@postgres:5432/leetcode"
    redis_url: str = "redis://redis:6379/0"
    problem_cache_ttl_seconds: int = 60


settings = Settings()
