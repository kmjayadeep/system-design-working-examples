from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class PriceIngestRequest(BaseModel):
    asin: str = Field(min_length=1, max_length=32)
    title: str = Field(default="", max_length=255)
    price: Decimal = Field(gt=0)
    source: str = Field(default="crawler", max_length=64)


class SubscribeRequest(BaseModel):
    asin: str = Field(min_length=1, max_length=32)
    threshold_price: Decimal = Field(gt=0)


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def history_cache_key(asin: str) -> str:
    return f"price-history:{asin}"


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


app = FastAPI(title="Price Tracking Prototype", lifespan=lifespan)


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


@app.post("/prices", status_code=201)
async def ingest_price(payload: PriceIngestRequest, state: Annotated[AppState, Depends(get_state)]):
    await state.db.execute(
        """
        INSERT INTO products (asin, title)
        VALUES ($1, $2)
        ON CONFLICT (asin) DO UPDATE SET title = COALESCE(NULLIF($2, ''), products.title)
        """,
        payload.asin,
        payload.title,
    )
    price_id = uuid.uuid4()
    observed_at = datetime.now(UTC)
    await state.db.execute(
        """
        INSERT INTO price_points (id, asin, price, source, observed_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        price_id,
        payload.asin,
        payload.price,
        payload.source,
        observed_at,
    )
    await state.redis.delete(history_cache_key(payload.asin))
    await state.redis.rpush("price-changes", json.dumps({"asin": payload.asin, "price": money(payload.price), "observedAt": observed_at.isoformat()}))
    return {"status": "ingested", "priceId": str(price_id)}


@app.get("/products/{asin}/prices")
async def price_history(
    asin: str,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    cached = await state.redis.get(history_cache_key(asin))
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload
    product = await state.db.fetchrow("SELECT * FROM products WHERE asin = $1", asin)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    rows = await state.db.fetch(
        """
        SELECT price, source, observed_at
        FROM price_points
        WHERE asin = $1
        ORDER BY observed_at
        """,
        asin,
    )
    payload = {
        "asin": asin,
        "title": product["title"],
        "history": [
            {"price": money(row["price"]), "source": row["source"], "observedAt": row["observed_at"].isoformat()}
            for row in rows
        ],
        "cache": "MISS",
    }
    await state.redis.set(history_cache_key(asin), json.dumps({k: v for k, v in payload.items() if k != "cache"}), ex=config.price_history_cache_ttl_seconds)
    return payload


@app.post("/subscriptions", status_code=201)
async def subscribe(
    payload: SubscribeRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    product = await state.db.fetchrow("SELECT asin FROM products WHERE asin = $1", payload.asin)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    subscription_id = uuid.uuid4()
    await state.db.execute(
        """
        INSERT INTO subscriptions (id, user_id, asin, threshold_price)
        VALUES ($1, $2, $3, $4)
        """,
        subscription_id,
        actor_user_id,
        payload.asin,
        payload.threshold_price,
    )
    return {"status": "subscribed", "subscriptionId": str(subscription_id)}


@app.post("/notifications/tick")
async def process_notifications(state: Annotated[AppState, Depends(get_state)], limit: int = 100):
    sent = 0
    for _ in range(limit):
        raw = await state.redis.lpop("price-changes")
        if raw is None:
            break
        event = json.loads(raw)
        rows = await state.db.fetch(
            """
            SELECT *
            FROM subscriptions
            WHERE asin = $1 AND active = true AND threshold_price >= $2::numeric
            """,
            event["asin"],
            Decimal(event["price"]),
        )
        for row in rows:
            try:
                await state.db.execute(
                    """
                    INSERT INTO notifications (id, subscription_id, user_id, asin, price)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid.uuid4(),
                    row["id"],
                    row["user_id"],
                    row["asin"],
                    Decimal(event["price"]),
                )
                sent += 1
            except asyncpg.UniqueViolationError:
                pass
    return {"sent": sent}


@app.get("/notifications")
async def notifications(actor_user_id: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch(
        """
        SELECT asin, price, created_at
        FROM notifications
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        actor_user_id,
    )
    return {
        "notifications": [
            {"asin": row["asin"], "price": money(row["price"]), "createdAt": row["created_at"].isoformat()}
            for row in rows
        ]
    }
