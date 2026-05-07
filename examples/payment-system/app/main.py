from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class PaymentMethodRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    token: str = Field(min_length=1)
    brand: str = "visa"
    last4: str = Field(min_length=4, max_length=4)


class PaymentRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    merchant_id: str = Field(alias="merchantId", min_length=1)
    amount_cents: int = Field(alias="amountCents", gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


def ledger_for_capture(amount_cents: int) -> list[dict]:
    return [
        {"account": "user_cash", "amountCents": -amount_cents},
        {"account": "merchant_receivable", "amountCents": amount_cents},
    ]


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


app = FastAPI(title="Payment System Prototype", lifespan=lifespan)


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


def payment_payload(row: asyncpg.Record) -> dict:
    return {
        "paymentId": str(row["id"]),
        "idempotencyKey": row["idempotency_key"],
        "userId": row["user_id"],
        "merchantId": row["merchant_id"],
        "amountCents": row["amount_cents"],
        "currency": row["currency"],
        "status": row["status"],
    }


@app.post("/payment-methods", status_code=201)
async def create_payment_method(payload: PaymentMethodRequest, state: Annotated[AppState, Depends(get_state)]):
    method_id = uuid.uuid4()
    await state.db.execute(
        "INSERT INTO payment_methods (id, user_id, token, brand, last4) VALUES ($1, $2, $3, $4, $5)",
        method_id,
        payload.user_id,
        payload.token,
        payload.brand,
        payload.last4,
    )
    return {"paymentMethodId": str(method_id), "userId": payload.user_id, "brand": payload.brand, "last4": payload.last4}


@app.post("/payments", status_code=201)
async def create_payment(
    payload: PaymentRequest,
    state: Annotated[AppState, Depends(get_state)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    async with state.db.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM payments WHERE idempotency_key = $1", idempotency_key)
        if existing:
            return {**payment_payload(existing), "idempotentReplay": True}
        async with conn.transaction():
            payment_id = uuid.uuid4()
            row = await conn.fetchrow(
                """
                INSERT INTO payments (id, idempotency_key, user_id, merchant_id, amount_cents, currency, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'captured')
                RETURNING *
                """,
                payment_id,
                idempotency_key,
                payload.user_id,
                payload.merchant_id,
                payload.amount_cents,
                payload.currency,
            )
            for entry in ledger_for_capture(payload.amount_cents):
                await conn.execute("INSERT INTO ledger_entries (payment_id, account, amount_cents) VALUES ($1, $2, $3)", payment_id, entry["account"], entry["amountCents"])
    await state.redis.xadd("payment-events", {"payment_id": str(row["id"]), "status": row["status"]}, maxlen=1000)
    return {**payment_payload(row), "idempotentReplay": False}


@app.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("SELECT * FROM payments WHERE id = $1 FOR UPDATE", payment_id)
            if row is None:
                raise HTTPException(status_code=404, detail="payment not found")
            if row["status"] == "refunded":
                return payment_payload(row)
            if row["status"] != "captured":
                raise HTTPException(status_code=409, detail="payment is not refundable")
            await conn.execute("INSERT INTO ledger_entries (payment_id, account, amount_cents) VALUES ($1, 'merchant_receivable', $2)", payment_id, -row["amount_cents"])
            await conn.execute("INSERT INTO ledger_entries (payment_id, account, amount_cents) VALUES ($1, 'user_cash', $2)", payment_id, row["amount_cents"])
            row = await conn.fetchrow("UPDATE payments SET status = 'refunded', updated_at = now() WHERE id = $1 RETURNING *", payment_id)
    return payment_payload(row)


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    row = await state.db.fetchrow("SELECT * FROM payments WHERE id = $1", payment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return payment_payload(row)


@app.get("/payments/{payment_id}/ledger")
async def get_ledger(payment_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch("SELECT * FROM ledger_entries WHERE payment_id = $1 ORDER BY id", payment_id)
    return {"entries": [{"account": row["account"], "amountCents": row["amount_cents"]} for row in rows]}
