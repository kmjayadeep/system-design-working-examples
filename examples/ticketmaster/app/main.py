from __future__ import annotations

import json
import socket
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class ReserveRequest(BaseModel):
    ticket_ids: list[str] = Field(min_length=1)


class ConfirmRequest(BaseModel):
    reservation_id: uuid.UUID


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.00")))


def event_cache_key(event_id: str) -> str:
    return f"event:{event_id}"


def ticket_status(row: asyncpg.Record) -> str:
    if row["status"] == "reserved" and row["reserved_until"] <= datetime.now(UTC):
        return "available"
    return row["status"]


def ticket_payload(row: asyncpg.Record) -> dict:
    return {
        "ticketId": row["id"],
        "section": row["section"],
        "row": row["seat_row"],
        "seat": row["seat_number"],
        "price": money(row["price"]),
        "status": ticket_status(row),
        "reservedUntil": row["reserved_until"].isoformat() if row["reserved_until"] else None,
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


app = FastAPI(title="Ticketmaster Prototype", lifespan=lifespan)


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


@app.get("/events/search")
async def search_events(
    state: Annotated[AppState, Depends(get_state)],
    q: str = "",
    city: str | None = None,
    page_size: int = Query(default=10, ge=1, le=50),
):
    rows = await state.db.fetch(
        """
        SELECT e.id, e.name, e.category, e.starts_at, v.name AS venue, v.city, p.name AS performer
        FROM events e
        JOIN venues v ON v.id = e.venue_id
        JOIN performers p ON p.id = e.performer_id
        WHERE ($1 = '' OR lower(e.name || ' ' || p.name || ' ' || e.category) LIKE '%' || lower($1) || '%')
          AND ($2::text IS NULL OR v.city = $2)
        ORDER BY e.starts_at
        LIMIT $3
        """,
        q,
        city,
        page_size,
    )
    return {"events": [dict(row) for row in rows]}


@app.get("/events/{event_id}")
async def get_event(
    event_id: str,
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    cached = await state.redis.get(event_cache_key(event_id))
    if cached:
        payload = json.loads(cached)
        payload["cache"] = "HIT"
        return payload
    event = await state.db.fetchrow(
        """
        SELECT e.*, v.name AS venue_name, v.city, p.name AS performer_name
        FROM events e
        JOIN venues v ON v.id = e.venue_id
        JOIN performers p ON p.id = e.performer_id
        WHERE e.id = $1
        """,
        event_id,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    tickets = await state.db.fetch("SELECT * FROM tickets WHERE event_id = $1 ORDER BY id", event_id)
    payload = {
        "event": {
            "eventId": event["id"],
            "name": event["name"],
            "category": event["category"],
            "startsAt": event["starts_at"].isoformat(),
            "venue": {"name": event["venue_name"], "city": event["city"]},
            "performer": event["performer_name"],
        },
        "tickets": [ticket_payload(row) for row in tickets],
        "cache": "MISS",
    }
    await state.redis.set(event_cache_key(event_id), json.dumps({k: v for k, v in payload.items() if k != "cache"}), ex=config.event_cache_ttl_seconds)
    return payload


@app.post("/events/{event_id}/reservations", status_code=201)
async def reserve_tickets(
    event_id: str,
    payload: ReserveRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    reservation_id = uuid.uuid4()
    reserved_until = datetime.now(UTC) + timedelta(seconds=config.reservation_ttl_seconds)
    async with state.db.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            rows = await conn.fetch(
                """
                SELECT * FROM tickets
                WHERE event_id = $1 AND id = ANY($2::text[])
                FOR UPDATE
                """,
                event_id,
                payload.ticket_ids,
            )
            if len(rows) != len(set(payload.ticket_ids)):
                raise HTTPException(status_code=404, detail="one or more tickets were not found")
            unavailable = [row["id"] for row in rows if row["status"] == "sold" or (row["status"] == "reserved" and row["reserved_until"] > datetime.now(UTC))]
            if unavailable:
                raise HTTPException(status_code=409, detail={"unavailableTicketIds": unavailable})
            total = sum(row["price"] for row in rows)
            await conn.execute(
                """
                INSERT INTO reservations (id, user_id, event_id, status, total_price, expires_at)
                VALUES ($1, $2, $3, 'reserved', $4, $5)
                """,
                reservation_id,
                actor_user_id,
                event_id,
                total,
                reserved_until,
            )
            await conn.execute(
                """
                UPDATE tickets
                SET status = 'reserved', reservation_id = $3, reserved_until = $4
                WHERE event_id = $1 AND id = ANY($2::text[])
                """,
                event_id,
                payload.ticket_ids,
                reservation_id,
                reserved_until,
            )
    await state.redis.delete(event_cache_key(event_id))
    return {"reservationId": str(reservation_id), "status": "reserved", "expiresAt": reserved_until.isoformat(), "totalPrice": money(total)}


@app.post("/bookings", status_code=201)
async def confirm_booking(
    payload: ConfirmRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    booking_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            reservation = await conn.fetchrow("SELECT * FROM reservations WHERE id = $1 AND user_id = $2 FOR UPDATE", payload.reservation_id, actor_user_id)
            if reservation is None:
                raise HTTPException(status_code=404, detail="reservation not found")
            if reservation["status"] != "reserved" or reservation["expires_at"] <= datetime.now(UTC):
                raise HTTPException(status_code=409, detail="reservation expired or already confirmed")
            await conn.execute(
                """
                INSERT INTO bookings (id, reservation_id, user_id, event_id, total_price)
                VALUES ($1, $2, $3, $4, $5)
                """,
                booking_id,
                payload.reservation_id,
                actor_user_id,
                reservation["event_id"],
                reservation["total_price"],
            )
            await conn.execute("UPDATE reservations SET status = 'confirmed' WHERE id = $1", payload.reservation_id)
            await conn.execute("UPDATE tickets SET status = 'sold' WHERE reservation_id = $1", payload.reservation_id)
    await state.redis.delete(event_cache_key(reservation["event_id"]))
    return {"bookingId": str(booking_id), "status": "confirmed", "totalPrice": money(reservation["total_price"])}
