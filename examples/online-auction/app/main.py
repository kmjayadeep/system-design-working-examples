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


class CreateAuctionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    starting_price: Decimal = Field(gt=0)
    ends_at: datetime


class BidRequest(BaseModel):
    amount: Decimal = Field(gt=0)


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def money(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(Decimal("0.01")))


def row_payload(row: asyncpg.Record, bids: list[dict] | None = None, cache: str = "MISS") -> dict:
    return {
        "auctionId": str(row["id"]),
        "sellerId": row["seller_id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "startingPrice": money(row["starting_price"]),
        "currentPrice": money(row["current_price"]),
        "currentWinner": row["current_winner"],
        "endsAt": row["ends_at"].isoformat(),
        "bids": bids or [],
        "cache": cache,
    }


def cache_key(auction_id: uuid.UUID) -> str:
    return f"auction:{auction_id}"


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


app = FastAPI(title="Online Auction Prototype", lifespan=lifespan)


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


@app.post("/auctions", status_code=201)
async def create_auction(
    payload: CreateAuctionRequest,
    seller_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    ends_at = payload.ends_at if payload.ends_at.tzinfo else payload.ends_at.replace(tzinfo=UTC)
    if ends_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="ends_at must be in the future")
    auction_id = uuid.uuid4()
    row = await state.db.fetchrow(
        """
        INSERT INTO auctions (id, seller_id, title, description, starting_price, current_price, ends_at)
        VALUES ($1, $2, $3, $4, $5, $5, $6)
        RETURNING *
        """,
        auction_id,
        seller_id,
        payload.title,
        payload.description,
        payload.starting_price,
        ends_at,
    )
    return row_payload(row)


@app.post("/auctions/{auction_id}/bids", status_code=201)
async def place_bid(
    auction_id: uuid.UUID,
    payload: BidRequest,
    bidder_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    async with state.db.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            row = await conn.fetchrow("SELECT * FROM auctions WHERE id = $1 FOR UPDATE", auction_id)
            if row is None:
                raise HTTPException(status_code=404, detail="auction not found")
            if row["seller_id"] == bidder_id:
                raise HTTPException(status_code=409, detail="seller cannot bid on own auction")
            if row["status"] != "open" or row["ends_at"] <= datetime.now(UTC):
                await conn.execute("UPDATE auctions SET status = 'closed' WHERE id = $1", auction_id)
                raise HTTPException(status_code=409, detail="auction is closed")
            if payload.amount <= row["current_price"]:
                raise HTTPException(status_code=409, detail="bid must be higher than current price")

            bid_id = uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO bids (id, auction_id, bidder_id, amount)
                VALUES ($1, $2, $3, $4)
                """,
                bid_id,
                auction_id,
                bidder_id,
                payload.amount,
            )
            updated = await conn.fetchrow(
                """
                UPDATE auctions
                SET current_price = $2, current_winner = $3
                WHERE id = $1
                RETURNING *
                """,
                auction_id,
                payload.amount,
                bidder_id,
            )
    await state.redis.delete(cache_key(auction_id))
    await state.redis.lpush(
        f"auction:{auction_id}:events",
        json.dumps({"bidId": str(bid_id), "bidderId": bidder_id, "amount": money(payload.amount)}),
    )
    await state.redis.ltrim(f"auction:{auction_id}:events", 0, 19)
    return row_payload(updated)


@app.get("/auctions/{auction_id}")
async def get_auction(
    auction_id: uuid.UUID,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    cached = await state.redis.get(cache_key(auction_id))
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload

    row = await state.db.fetchrow("SELECT * FROM auctions WHERE id = $1", auction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="auction not found")
    bids = await state.db.fetch(
        """
        SELECT bidder_id, amount, created_at
        FROM bids
        WHERE auction_id = $1
        ORDER BY amount DESC, created_at DESC
        LIMIT 10
        """,
        auction_id,
    )
    payload = row_payload(
        row,
        [
            {"bidderId": bid["bidder_id"], "amount": money(bid["amount"]), "createdAt": bid["created_at"].isoformat()}
            for bid in bids
        ],
    )
    await state.redis.set(cache_key(auction_id), json.dumps({k: v for k, v in payload.items() if k != "cache"}), ex=config.auction_cache_ttl_seconds)
    return payload
