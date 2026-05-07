from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.market import order_total
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class PriceRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    price_cents: int = Field(alias="priceCents", gt=0)


class OrderRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    symbol: str = Field(min_length=1, max_length=12)
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)


def get_state(request: Request) -> AppState:
    return request.app.state.services


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


app = FastAPI(title="Robinhood Prototype", lifespan=lifespan)


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


@app.post("/market/prices", status_code=201)
async def update_price(payload: PriceRequest, state: Annotated[AppState, Depends(get_state)]):
    symbol = payload.symbol.upper()
    await state.redis.hset("market:prices", symbol, payload.price_cents)
    await state.redis.xadd("market:price-events", {"symbol": symbol, "price_cents": payload.price_cents}, maxlen=1000)
    return {"symbol": symbol, "priceCents": payload.price_cents}


@app.get("/market/prices/{symbol}")
async def get_price(symbol: str, state: Annotated[AppState, Depends(get_state)]):
    price = await state.redis.hget("market:prices", symbol.upper())
    if price is None:
        raise HTTPException(status_code=404, detail="price not found")
    return {"symbol": symbol.upper(), "priceCents": int(price)}


@app.post("/orders", status_code=201)
async def place_order(payload: OrderRequest, state: Annotated[AppState, Depends(get_state)]):
    symbol = payload.symbol.upper()
    raw_price = await state.redis.hget("market:prices", symbol)
    if raw_price is None:
        raise HTTPException(status_code=409, detail="symbol has no market price")
    price_cents = int(raw_price)
    total = order_total(payload.quantity, price_cents)
    order_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow("SELECT * FROM accounts WHERE user_id = $1 FOR UPDATE", payload.user_id)
            if account is None:
                await conn.execute("INSERT INTO accounts (user_id, cash_cents) VALUES ($1, 0)", payload.user_id)
                account = await conn.fetchrow("SELECT * FROM accounts WHERE user_id = $1 FOR UPDATE", payload.user_id)
            status, reason = "filled", None
            if payload.side == "buy":
                if account["cash_cents"] < total:
                    status, reason = "rejected", "insufficient cash"
                else:
                    await conn.execute("UPDATE accounts SET cash_cents = cash_cents - $1 WHERE user_id = $2", total, payload.user_id)
                    await conn.execute(
                        """
                        INSERT INTO holdings (user_id, symbol, quantity) VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, symbol) DO UPDATE SET quantity = holdings.quantity + EXCLUDED.quantity
                        """,
                        payload.user_id,
                        symbol,
                        payload.quantity,
                    )
            else:
                holding = await conn.fetchrow("SELECT * FROM holdings WHERE user_id = $1 AND symbol = $2 FOR UPDATE", payload.user_id, symbol)
                if holding is None or holding["quantity"] < payload.quantity:
                    status, reason = "rejected", "insufficient shares"
                else:
                    await conn.execute("UPDATE holdings SET quantity = quantity - $1 WHERE user_id = $2 AND symbol = $3", payload.quantity, payload.user_id, symbol)
                    await conn.execute("UPDATE accounts SET cash_cents = cash_cents + $1 WHERE user_id = $2", total, payload.user_id)
            row = await conn.fetchrow(
                """
                INSERT INTO orders (id, user_id, symbol, side, quantity, price_cents, status, reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                order_id,
                payload.user_id,
                symbol,
                payload.side,
                payload.quantity,
                price_cents,
                status,
                reason,
            )
    await state.redis.xadd("order-events", {"order_id": str(order_id), "status": row["status"]}, maxlen=1000)
    return order_payload(row)


def order_payload(row: asyncpg.Record) -> dict:
    return {
        "orderId": str(row["id"]),
        "userId": row["user_id"],
        "symbol": row["symbol"],
        "side": row["side"],
        "quantity": row["quantity"],
        "priceCents": row["price_cents"],
        "status": row["status"],
        "reason": row["reason"],
        "createdAt": row["created_at"].isoformat(),
    }


@app.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str, state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        account = await conn.fetchrow("SELECT * FROM accounts WHERE user_id = $1", user_id)
        holdings = await conn.fetch("SELECT * FROM holdings WHERE user_id = $1 AND quantity > 0 ORDER BY symbol", user_id)
        orders = await conn.fetch("SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 20", user_id)
    return {
        "userId": user_id,
        "cashCents": 0 if account is None else account["cash_cents"],
        "holdings": [{"symbol": row["symbol"], "quantity": row["quantity"]} for row in holdings],
        "recentOrders": [order_payload(row) for row in orders],
    }
