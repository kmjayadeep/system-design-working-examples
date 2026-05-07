from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.geo import route_distance_km
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class CreateActivityRequest(BaseModel):
    activity_type: str = Field(default="run", pattern="^(run|ride|walk)$")


class ActivityPoint(BaseModel):
    latitude: float
    longitude: float
    recorded_at: datetime | None = None


class AddPointsRequest(BaseModel):
    points: list[ActivityPoint] = Field(min_length=1)


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def point_payload(point: ActivityPoint) -> dict:
    recorded_at = point.recorded_at or datetime.now(UTC)
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    return {
        "latitude": point.latitude,
        "longitude": point.longitude,
        "recorded_at": recorded_at.isoformat(),
    }


def activity_key(activity_id: uuid.UUID) -> str:
    return f"activity:{activity_id}:live"


def points_key(activity_id: uuid.UUID) -> str:
    return f"activity:{activity_id}:points"


async def live_payload(redis: Redis, activity_id: uuid.UUID) -> dict:
    raw = await redis.get(activity_key(activity_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="live activity not found")
    return json.loads(raw)


async def write_live_payload(redis: Redis, config: Settings, activity_id: uuid.UUID, payload: dict) -> None:
    await redis.set(activity_key(activity_id), json.dumps(payload), ex=config.live_ttl_seconds)


async def update_summary(redis: Redis, config: Settings, activity_id: uuid.UUID, status: str | None = None) -> dict:
    payload = await live_payload(redis, activity_id)
    points = [json.loads(raw) for raw in await redis.lrange(points_key(activity_id), 0, -1)]
    payload["pointCount"] = len(points)
    payload["distanceKm"] = round(route_distance_km(points), 3)
    if len(points) >= 2:
        start = datetime.fromisoformat(points[0]["recorded_at"])
        end = datetime.fromisoformat(points[-1]["recorded_at"])
        payload["elapsedSeconds"] = max(int((end - start).total_seconds()), 0)
    else:
        payload["elapsedSeconds"] = 0
    if status:
        payload["status"] = status
    await write_live_payload(redis, config, activity_id, payload)
    await redis.expire(points_key(activity_id), config.live_ttl_seconds)
    return payload


def activity_from_row(row: asyncpg.Record) -> dict:
    return {
        "activityId": str(row["id"]),
        "userId": row["user_id"],
        "activityType": row["activity_type"],
        "status": row["status"],
        "distanceKm": round(row["distance_km"], 3),
        "elapsedSeconds": row["elapsed_seconds"],
        "startedAt": row["started_at"].isoformat(),
        "endedAt": row["ended_at"].isoformat() if row["ended_at"] else None,
        "pointCount": row["point_count"],
    }


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


app = FastAPI(title="Strava Activity Tracking Prototype", lifespan=lifespan)


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


@app.post("/activities", status_code=201)
async def start_activity(
    payload: CreateActivityRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    activity_id = uuid.uuid4()
    started_at = datetime.now(UTC)
    await state.db.execute(
        """
        INSERT INTO activities (id, user_id, activity_type, status, started_at)
        VALUES ($1, $2, $3, 'active', $4)
        """,
        activity_id,
        actor_user_id,
        payload.activity_type,
        started_at,
    )
    live = {
        "activityId": str(activity_id),
        "userId": actor_user_id,
        "activityType": payload.activity_type,
        "status": "active",
        "startedAt": started_at.isoformat(),
        "distanceKm": 0,
        "elapsedSeconds": 0,
        "pointCount": 0,
    }
    await write_live_payload(state.redis, config, activity_id, live)
    return live


@app.post("/activities/{activity_id}/points")
async def add_points(
    activity_id: uuid.UUID,
    payload: AddPointsRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    if live["status"] not in {"active", "paused"}:
        raise HTTPException(status_code=409, detail=f"activity is {live['status']}")
    values = [json.dumps(point_payload(point)) for point in payload.points]
    await state.redis.rpush(points_key(activity_id), *values)
    updated = await update_summary(state.redis, config, activity_id)
    return updated


@app.post("/activities/{activity_id}/pause")
async def pause_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    return await update_summary(state.redis, config, activity_id, "paused")


@app.post("/activities/{activity_id}/resume")
async def resume_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    return await update_summary(state.redis, config, activity_id, "active")


@app.post("/activities/{activity_id}/stop")
async def stop_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    return await update_summary(state.redis, config, activity_id, "stopped")


@app.get("/activities/{activity_id}/live")
async def get_live_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    return live


@app.post("/activities/{activity_id}/save")
async def save_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    live = await live_payload(state.redis, activity_id)
    if live["userId"] != actor_user_id:
        raise HTTPException(status_code=404, detail="activity not found")
    if live["status"] != "stopped":
        raise HTTPException(status_code=409, detail="activity must be stopped before saving")
    points = [json.loads(raw) for raw in await state.redis.lrange(points_key(activity_id), 0, -1)]
    ended_at = datetime.now(UTC)
    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                UPDATE activities
                SET status = 'saved', distance_km = $2, elapsed_seconds = $3,
                    ended_at = $4, point_count = $5
                WHERE id = $1 AND user_id = $6
                """,
                activity_id,
                live["distanceKm"],
                live["elapsedSeconds"],
                ended_at,
                live["pointCount"],
                actor_user_id,
            )
            await conn.executemany(
                """
                INSERT INTO activity_points (activity_id, sequence_number, latitude, longitude, recorded_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (activity_id, sequence_number) DO NOTHING
                """,
                [
                    (
                        activity_id,
                        index,
                        point["latitude"],
                        point["longitude"],
                        datetime.fromisoformat(point["recorded_at"]),
                    )
                    for index, point in enumerate(points, start=1)
                ],
            )
    await state.redis.delete(activity_key(activity_id), points_key(activity_id))
    return {"status": "saved", "activityId": str(activity_id), "pointCount": len(points)}


@app.get("/activities/feed")
async def feed(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    rows = await state.db.fetch(
        """
        SELECT a.*
        FROM activities a
        LEFT JOIN friendships f ON f.friend_id = a.user_id AND f.user_id = $1
        WHERE a.status = 'saved' AND (a.user_id = $1 OR f.friend_id IS NOT NULL)
        ORDER BY a.ended_at DESC NULLS LAST, a.started_at DESC
        LIMIT 20
        """,
        actor_user_id,
    )
    return {"activities": [activity_from_row(row) for row in rows]}


@app.get("/activities/{activity_id}")
async def get_activity(
    activity_id: uuid.UUID,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    row = await state.db.fetchrow(
        """
        SELECT a.*
        FROM activities a
        LEFT JOIN friendships f ON f.friend_id = a.user_id AND f.user_id = $2
        WHERE a.id = $1 AND (a.user_id = $2 OR f.friend_id IS NOT NULL)
        """,
        activity_id,
        actor_user_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="activity not found")
    points = await state.db.fetch(
        """
        SELECT sequence_number, latitude, longitude, recorded_at
        FROM activity_points
        WHERE activity_id = $1
        ORDER BY sequence_number
        """,
        activity_id,
    )
    payload = activity_from_row(row)
    payload["points"] = [
        {
            "sequenceNumber": point["sequence_number"],
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "recordedAt": point["recorded_at"].isoformat(),
        }
        for point in points
    ]
    return payload
