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


class OrderLine(BaseModel):
    item_id: str
    quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
    latitude: float
    longitude: float
    items: list[OrderLine] = Field(min_length=1)


def get_settings() -> Settings:
    return settings


def get_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def get_state(request: Request) -> AppState:
    return request.app.state.services


async def nearby_distribution_centers(
    db: asyncpg.Pool,
    latitude: float,
    longitude: float,
    max_distance_km: float,
) -> list[asyncpg.Record]:
    rows = await db.fetch("SELECT * FROM distribution_centers ORDER BY id")
    return [
        row
        for row in rows
        if haversine_km(latitude, longitude, row["latitude"], row["longitude"])
        <= max_distance_km
    ]


def availability_cache_key(latitude: float, longitude: float, item_ids: list[str]) -> str:
    rounded_lat = round(latitude, 2)
    rounded_lon = round(longitude, 2)
    item_part = ",".join(sorted(item_ids)) if item_ids else "all"
    return f"availability:{rounded_lat}:{rounded_lon}:{item_part}"


async def build_availability(
    db: asyncpg.Pool,
    latitude: float,
    longitude: float,
    item_ids: list[str],
    max_distance_km: float,
) -> dict:
    dcs = await nearby_distribution_centers(db, latitude, longitude, max_distance_km)
    dc_ids = [row["id"] for row in dcs]
    if not dc_ids:
        return {"nearbyDistributionCenters": [], "items": []}

    rows = await db.fetch(
        """
        SELECT i.id, i.name, i.description, SUM(inv.quantity)::int AS available_quantity
        FROM inventory inv
        JOIN items i ON i.id = inv.item_id
        WHERE inv.dc_id = ANY($1::text[])
          AND ($2::text[] = '{}'::text[] OR inv.item_id = ANY($2::text[]))
        GROUP BY i.id, i.name, i.description
        HAVING SUM(inv.quantity) > 0
        ORDER BY i.id
        """,
        dc_ids,
        item_ids,
    )
    return {
        "nearbyDistributionCenters": [
            {"id": row["id"], "name": row["name"], "regionId": row["region_id"]}
            for row in dcs
        ],
        "items": [
            {
                "itemId": row["id"],
                "name": row["name"],
                "description": row["description"],
                "availableQuantity": row["available_quantity"],
            }
            for row in rows
        ],
    }


async def choose_fulfillment_dc(
    conn: asyncpg.Connection,
    latitude: float,
    longitude: float,
    requested: dict[str, int],
    max_distance_km: float,
) -> str | None:
    rows = await conn.fetch("SELECT * FROM distribution_centers ORDER BY id")
    candidates = [
        row["id"]
        for row in rows
        if haversine_km(latitude, longitude, row["latitude"], row["longitude"])
        <= max_distance_km
    ]
    for dc_id in candidates:
        inventory_rows = await conn.fetch(
            """
            SELECT item_id, quantity
            FROM inventory
            WHERE dc_id = $1 AND item_id = ANY($2::text[])
            FOR UPDATE
            """,
            dc_id,
            list(requested.keys()),
        )
        available = {row["item_id"]: row["quantity"] for row in inventory_rows}
        if all(available.get(item_id, 0) >= qty for item_id, qty in requested.items()):
            return dc_id
    return None


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


app = FastAPI(title="GoPuff Local Delivery Prototype", lifespan=lifespan)


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


@app.get("/availability")
async def get_availability(
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    latitude: float,
    longitude: float,
    item_id: list[str] = Query(default=[]),
):
    cache_key = availability_cache_key(latitude, longitude, item_id)
    cached = await state.redis.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    payload = await build_availability(
        state.db,
        latitude,
        longitude,
        item_id,
        config.max_delivery_distance_km,
    )
    payload["cache"] = "MISS"
    await state.redis.set(
        cache_key,
        json.dumps({k: v for k, v in payload.items() if k != "cache"}),
        ex=config.availability_cache_ttl_seconds,
    )
    return payload


@app.post("/orders", status_code=201)
async def create_order(
    payload: CreateOrderRequest,
    user_id: Annotated[str, Depends(get_user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    requested: dict[str, int] = {}
    for line in payload.items:
        requested[line.item_id] = requested.get(line.item_id, 0) + line.quantity

    order_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            dc_id = await choose_fulfillment_dc(
                conn,
                payload.latitude,
                payload.longitude,
                requested,
                config.max_delivery_distance_km,
            )
            if dc_id is None:
                raise HTTPException(
                    status_code=409,
                    detail="requested items are not available from one nearby distribution center",
                )

            await conn.execute(
                """
                INSERT INTO orders (id, user_id, dc_id, latitude, longitude, status)
                VALUES ($1, $2, $3, $4, $5, 'created')
                """,
                order_id,
                user_id,
                dc_id,
                payload.latitude,
                payload.longitude,
            )
            for item_id, quantity in requested.items():
                result = await conn.execute(
                    """
                    UPDATE inventory
                    SET quantity = quantity - $3
                    WHERE dc_id = $1 AND item_id = $2 AND quantity >= $3
                    """,
                    dc_id,
                    item_id,
                    quantity,
                )
                if result == "UPDATE 0":
                    raise HTTPException(status_code=409, detail=f"{item_id} is unavailable")
                await conn.execute(
                    """
                    INSERT INTO order_items (order_id, item_id, quantity)
                    VALUES ($1, $2, $3)
                    """,
                    order_id,
                    item_id,
                    quantity,
                )

    await state.redis.flushdb()
    return {
        "orderId": str(order_id),
        "status": "created",
        "distributionCenterId": dc_id,
        "items": [{"itemId": item_id, "quantity": qty} for item_id, qty in requested.items()],
    }
