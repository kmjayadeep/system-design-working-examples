from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://uber:uber@postgres:5432/uber"
    redis_url: str = "redis://redis:6379/0"
    driver_search_radius_km: float = 5.0
    base_fare: float = 5.0
    per_km_fare: float = 2.25


settings = Settings()
