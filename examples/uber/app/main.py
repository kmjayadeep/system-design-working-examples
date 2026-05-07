from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.geo import haversine_km
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class LocationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    available: bool = True


class RideRequest(BaseModel):
    rider_id: str = Field(alias="riderId", min_length=1)
    start_lat: float = Field(alias="startLat", ge=-90, le=90)
    start_lng: float = Field(alias="startLng", ge=-180, le=180)
    dest_lat: float = Field(alias="destLat", ge=-90, le=90)
    dest_lng: float = Field(alias="destLng", ge=-180, le=180)


class RespondRequest(BaseModel):
    driver_id: str = Field(alias="driverId", min_length=1)
    accept: bool


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def ride_payload(row: asyncpg.Record) -> dict:
    return {
        "rideId": str(row["id"]),
        "riderId": row["rider_id"],
        "driverId": row["driver_id"],
        "start": {"lat": row["start_lat"], "lng": row["start_lng"]},
        "destination": {"lat": row["dest_lat"], "lng": row["dest_lng"]},
        "estimatedFare": round(float(row["estimated_fare"]), 2),
        "status": row["status"],
        "createdAt": row["created_at"].isoformat(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="Uber Prototype", lifespan=lifespan)


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


@app.post("/drivers/{driver_id}/location")
async def update_driver_location(
    driver_id: str,
    payload: LocationRequest,
    state: Annotated[AppState, Depends(get_state)],
):
    status = "available" if payload.available else "offline"
    await state.db.execute(
        """
        INSERT INTO drivers (id, lat, lng, status)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, status = EXCLUDED.status, updated_at = now()
        """,
        driver_id,
        payload.lat,
        payload.lng,
        status,
    )
    if payload.available:
        await state.redis.geoadd("drivers:available", (payload.lng, payload.lat, driver_id))
    else:
        await state.redis.zrem("drivers:available", driver_id)
    return {"driverId": driver_id, "status": status, "lat": payload.lat, "lng": payload.lng}


@app.get("/fare-estimate")
async def fare_estimate(
    config: Annotated[Settings, Depends(get_settings)],
    start_lat: float = Query(alias="startLat"),
    start_lng: float = Query(alias="startLng"),
    dest_lat: float = Query(alias="destLat"),
    dest_lng: float = Query(alias="destLng"),
):
    distance = haversine_km(start_lat, start_lng, dest_lat, dest_lng)
    return {"distanceKm": round(distance, 2), "estimatedFare": round(config.base_fare + distance * config.per_km_fare, 2)}


async def nearby_driver_ids(redis: Redis, lat: float, lng: float, radius_km: float) -> list[str]:
    rows = await redis.geosearch(
        "drivers:available",
        longitude=lng,
        latitude=lat,
        radius=radius_km,
        unit="km",
        sort="ASC",
        count=20,
    )
    return [row if isinstance(row, str) else row.decode() for row in rows]


@app.post("/rides", status_code=201)
async def request_ride(
    payload: RideRequest,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    estimate = await fare_estimate(config, payload.start_lat, payload.start_lng, payload.dest_lat, payload.dest_lng)
    candidates = await nearby_driver_ids(state.redis, payload.start_lat, payload.start_lng, config.driver_search_radius_km)
    if not candidates:
        raise HTTPException(status_code=409, detail="no nearby drivers available")

    ride_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        for driver_id in candidates:
            async with conn.transaction():
                driver = await conn.fetchrow("SELECT * FROM drivers WHERE id = $1 FOR UPDATE", driver_id)
                if driver is None or driver["status"] != "available":
                    await state.redis.zrem("drivers:available", driver_id)
                    continue
                await conn.execute("UPDATE drivers SET status = 'requested', updated_at = now() WHERE id = $1", driver_id)
                await state.redis.zrem("drivers:available", driver_id)
                row = await conn.fetchrow(
                    """
                    INSERT INTO rides (id, rider_id, driver_id, start_lat, start_lng, dest_lat, dest_lng, estimated_fare, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'requested')
                    RETURNING *
                    """,
                    ride_id,
                    payload.rider_id,
                    driver_id,
                    payload.start_lat,
                    payload.start_lng,
                    payload.dest_lat,
                    payload.dest_lng,
                    estimate["estimatedFare"],
                )
                return ride_payload(row)
    raise HTTPException(status_code=409, detail="nearby drivers were already assigned")


@app.post("/rides/{ride_id}/respond")
async def respond_to_ride(
    ride_id: uuid.UUID,
    payload: RespondRequest,
    state: Annotated[AppState, Depends(get_state)],
):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT * FROM rides WHERE id = $1 FOR UPDATE", ride_id)
            if row is None:
                raise HTTPException(status_code=404, detail="ride not found")
            if row["driver_id"] != payload.driver_id:
                raise HTTPException(status_code=403, detail="ride assigned to another driver")
            if row["status"] != "requested":
                raise HTTPException(status_code=409, detail="ride is not awaiting response")
            status = "accepted" if payload.accept else "declined"
            driver_status = "busy" if payload.accept else "available"
            await conn.execute("UPDATE drivers SET status = $1, updated_at = now() WHERE id = $2", driver_status, payload.driver_id)
            if not payload.accept:
                driver = await conn.fetchrow("SELECT * FROM drivers WHERE id = $1", payload.driver_id)
                await state.redis.geoadd("drivers:available", (driver["lng"], driver["lat"], payload.driver_id))
            row = await conn.fetchrow("UPDATE rides SET status = $1, updated_at = now() WHERE id = $2 RETURNING *", status, ride_id)
            return ride_payload(row)


@app.post("/rides/{ride_id}/complete")
async def complete_ride(ride_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT * FROM rides WHERE id = $1 FOR UPDATE", ride_id)
            if row is None:
                raise HTTPException(status_code=404, detail="ride not found")
            if row["status"] != "accepted":
                raise HTTPException(status_code=409, detail="ride must be accepted first")
            driver = await conn.fetchrow("SELECT * FROM drivers WHERE id = $1 FOR UPDATE", row["driver_id"])
            await conn.execute("UPDATE drivers SET status = 'available', updated_at = now() WHERE id = $1", row["driver_id"])
            await state.redis.geoadd("drivers:available", (driver["lng"], driver["lat"], row["driver_id"]))
            row = await conn.fetchrow("UPDATE rides SET status = 'completed', updated_at = now() WHERE id = $1 RETURNING *", ride_id)
            return ride_payload(row)


@app.get("/rides/{ride_id}")
async def get_ride(ride_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    row = await state.db.fetchrow("SELECT * FROM rides WHERE id = $1", ride_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ride not found")
    return ride_payload(row)
