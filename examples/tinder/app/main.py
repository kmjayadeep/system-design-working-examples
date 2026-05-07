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
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class ProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=100)
    gender: str = Field(pattern="^(female|male|nonbinary)$")
    interested_in: str = Field(pattern="^(female|male|both|any)$")
    min_age: int = Field(default=18, ge=18, le=100)
    max_age: int = Field(default=100, ge=18, le=100)
    max_distance_km: float = Field(default=25, gt=0)
    latitude: float
    longitude: float


class SwipeRequest(BaseModel):
    decision: str = Field(pattern="^(yes|no)$")


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def profile_payload(row: asyncpg.Record, distance_km: float | None = None) -> dict:
    payload = {
        "userId": row["user_id"],
        "name": row["name"],
        "age": row["age"],
        "gender": row["gender"],
        "interestedIn": row["interested_in"],
        "maxDistanceKm": row["max_distance_km"],
    }
    if distance_km is not None:
        payload["distanceKm"] = round(distance_km, 2)
    return payload


def feed_cache_key(actor_user_id: str, latitude: float, longitude: float) -> str:
    return f"feed:{actor_user_id}:{round(latitude, 2)}:{round(longitude, 2)}"


def gender_matches(preference: str, candidate_gender: str) -> bool:
    return preference in {"both", "any"} or preference == candidate_gender


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


app = FastAPI(title="Tinder Matching Prototype", lifespan=lifespan)


@app.get("/")
async def ui():
    return ui_response()


@app.get("/health")
async def health(state: Annotated[AppState, Depends(get_state)]):
    await state.redis.ping()
    async with state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/debug/instance")
async def debug_instance():
    return {"instance": socket.gethostname()}


@app.post("/profile", status_code=201)
async def upsert_profile(
    payload: ProfileRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    if payload.min_age > payload.max_age:
        raise HTTPException(status_code=422, detail="min_age must be <= max_age")
    row = await state.db.fetchrow(
        """
        INSERT INTO profiles (
            user_id, name, age, gender, interested_in, min_age, max_age,
            max_distance_km, latitude, longitude
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (user_id) DO UPDATE SET
            name = EXCLUDED.name,
            age = EXCLUDED.age,
            gender = EXCLUDED.gender,
            interested_in = EXCLUDED.interested_in,
            min_age = EXCLUDED.min_age,
            max_age = EXCLUDED.max_age,
            max_distance_km = EXCLUDED.max_distance_km,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
        RETURNING *
        """,
        actor_user_id,
        payload.name,
        payload.age,
        payload.gender,
        payload.interested_in,
        payload.min_age,
        payload.max_age,
        payload.max_distance_km,
        payload.latitude,
        payload.longitude,
    )
    await state.redis.flushdb()
    return {"status": "saved", "profile": profile_payload(row)}


@app.get("/feed")
async def feed(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    latitude: float,
    longitude: float,
    limit: int = Query(default=10, ge=1, le=50),
):
    cache_key = feed_cache_key(actor_user_id, latitude, longitude)
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    actor = await state.db.fetchrow("SELECT * FROM profiles WHERE user_id = $1", actor_user_id)
    if actor is None:
        raise HTTPException(status_code=404, detail="profile not found")
    rows = await state.db.fetch(
        """
        SELECT p.*
        FROM profiles p
        LEFT JOIN swipes s ON s.swiping_user_id = $1 AND s.target_user_id = p.user_id
        WHERE p.user_id != $1
          AND s.target_user_id IS NULL
          AND p.age BETWEEN $2 AND $3
        ORDER BY p.user_id
        """,
        actor_user_id,
        actor["min_age"],
        actor["max_age"],
    )
    candidates = []
    for row in rows:
        if not gender_matches(actor["interested_in"], row["gender"]):
            continue
        if not gender_matches(row["interested_in"], actor["gender"]):
            continue
        distance = haversine_km(latitude, longitude, row["latitude"], row["longitude"])
        if distance <= actor["max_distance_km"]:
            candidates.append(profile_payload(row, distance))
    candidates.sort(key=lambda item: (item["distanceKm"], item["userId"]))
    payload = {"profiles": candidates[:limit], "cache": "MISS"}
    await state.redis.set(cache_key, json.dumps({k: v for k, v in payload.items() if k != "cache"}), ex=config.feed_cache_ttl_seconds)
    return payload


@app.post("/swipe/{target_user_id}", status_code=201)
async def swipe(
    target_user_id: str,
    payload: SwipeRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    if target_user_id == actor_user_id:
        raise HTTPException(status_code=409, detail="cannot swipe on yourself")
    match_id = None
    async with state.db.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            target = await conn.fetchrow("SELECT user_id FROM profiles WHERE user_id = $1", target_user_id)
            actor = await conn.fetchrow("SELECT user_id FROM profiles WHERE user_id = $1", actor_user_id)
            if target is None or actor is None:
                raise HTTPException(status_code=404, detail="profile not found")
            await conn.execute(
                """
                INSERT INTO swipes (swiping_user_id, target_user_id, decision)
                VALUES ($1, $2, $3)
                ON CONFLICT (swiping_user_id, target_user_id)
                DO UPDATE SET decision = EXCLUDED.decision, created_at = now()
                """,
                actor_user_id,
                target_user_id,
                payload.decision,
            )
            if payload.decision == "yes":
                reciprocal = await conn.fetchrow(
                    """
                    SELECT 1 FROM swipes
                    WHERE swiping_user_id = $1 AND target_user_id = $2 AND decision = 'yes'
                    """,
                    target_user_id,
                    actor_user_id,
                )
                if reciprocal:
                    user_one, user_two = sorted([actor_user_id, target_user_id])
                    row = await conn.fetchrow(
                        """
                        INSERT INTO matches (id, user_one, user_two)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_one, user_two) DO UPDATE SET matched_at = matches.matched_at
                        RETURNING id
                        """,
                        uuid.uuid4(),
                        user_one,
                        user_two,
                    )
                    match_id = row["id"]
    await state.redis.flushdb()
    return {
        "status": "swiped",
        "decision": payload.decision,
        "matched": match_id is not None,
        "matchId": str(match_id) if match_id else None,
    }


@app.get("/matches")
async def matches(actor_user_id: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch(
        """
        SELECT *
        FROM matches
        WHERE user_one = $1 OR user_two = $1
        ORDER BY matched_at DESC
        """,
        actor_user_id,
    )
    return {
        "matches": [
            {
                "matchId": str(row["id"]),
                "matchedUserId": row["user_two"] if row["user_one"] == actor_user_id else row["user_one"],
                "matchedAt": row["matched_at"].isoformat(),
            }
            for row in rows
        ]
    }
