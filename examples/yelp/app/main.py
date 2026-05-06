from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.geo import haversine_km


class AppState:
    db: asyncpg.Pool
    redis: Redis


class CreateReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def business_payload(row: asyncpg.Record, distance_km: float | None = None) -> dict:
    payload = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "reviewCount": row["review_count"],
        "averageRating": round(row["average_rating"], 2),
    }
    if distance_km is not None:
        payload["distanceKm"] = round(distance_km, 2)
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="Yelp Business Search Prototype", lifespan=lifespan)


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.get("/businesses/search")
async def search_businesses(
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    q: str = "",
    category: str | None = None,
    latitude: float = Query(default=37.7749),
    longitude: float = Query(default=-122.4194),
    radius_km: float = Query(default=20, gt=0),
):
    cache_key = f"search:{q.lower()}:{category}:{round(latitude, 2)}:{round(longitude, 2)}:{radius_km}"
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    rows = await state.db.fetch(
        """
        SELECT *
        FROM businesses
        WHERE ($1 = '' OR lower(name) LIKE '%' || lower($1) || '%')
          AND ($2::text IS NULL OR category = $2)
        ORDER BY average_rating DESC, review_count DESC
        """,
        q,
        category,
    )
    matches = []
    for row in rows:
        distance = haversine_km(latitude, longitude, row["latitude"], row["longitude"])
        if distance <= radius_km:
            matches.append(business_payload(row, distance))
    matches.sort(key=lambda item: (item["distanceKm"], -item["averageRating"]))
    payload = {"businesses": matches}
    await state.redis.set(cache_key, json.dumps(payload), ex=config.search_cache_ttl_seconds)
    payload["cache"] = "MISS"
    return payload


@app.get("/businesses/{business_id}")
async def get_business(business_id: str, state: Annotated[AppState, Depends(get_state)]):
    business = await state.db.fetchrow("SELECT * FROM businesses WHERE id = $1", business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="business not found")
    reviews = await state.db.fetch(
        """
        SELECT user_id, rating, text, created_at
        FROM reviews
        WHERE business_id = $1
        ORDER BY created_at DESC
        """,
        business_id,
    )
    return {
        "business": business_payload(business),
        "reviews": [
            {
                "userId": row["user_id"],
                "rating": row["rating"],
                "text": row["text"],
                "createdAt": row["created_at"].isoformat(),
            }
            for row in reviews
        ],
    }


@app.post("/businesses/{business_id}/reviews", status_code=201)
async def create_review(
    business_id: str,
    payload: CreateReviewRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            business = await conn.fetchrow("SELECT * FROM businesses WHERE id = $1 FOR UPDATE", business_id)
            if business is None:
                raise HTTPException(status_code=404, detail="business not found")
            try:
                await conn.execute(
                    """
                    INSERT INTO reviews (id, business_id, user_id, rating, text)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid.uuid4(),
                    business_id,
                    actor_user_id,
                    payload.rating,
                    payload.text,
                )
            except asyncpg.UniqueViolationError as exc:
                raise HTTPException(status_code=409, detail="user already reviewed this business") from exc
            await conn.execute(
                """
                UPDATE businesses
                SET review_count = review_count + 1,
                    average_rating = (
                        SELECT AVG(rating)::double precision
                        FROM reviews
                        WHERE business_id = $1
                    )
                WHERE id = $1
                """,
                business_id,
            )
    await state.redis.flushdb()
    return {"status": "created"}
