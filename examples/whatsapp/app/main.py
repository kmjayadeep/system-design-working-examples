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
from app.storage import ensure_bucket, presigned_get_url, presigned_put_url
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class CreateChatRequest(BaseModel):
    participants: list[str] = Field(min_length=1, max_length=99)
    name: str = Field(default="", max_length=100)


class AttachmentRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(default="application/octet-stream", max_length=255)


class SendMessageRequest(BaseModel):
    body: str = Field(default="", max_length=4000)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list)


class AckRequest(BaseModel):
    message_id: uuid.UUID


def get_state(request: Request) -> AppState:
    return request.app.state.services


def get_settings() -> Settings:
    return settings


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


async def ensure_participant(db: asyncpg.Pool, chat_id: uuid.UUID, actor_user_id: str) -> None:
    row = await db.fetchrow("SELECT 1 FROM chat_participants WHERE chat_id = $1 AND user_id = $2", chat_id, actor_user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="chat not found")


async def message_payload(db: asyncpg.Pool, config: Settings, row: asyncpg.Record) -> dict:
    attachments = await db.fetch(
        """
        SELECT id, filename, mime_type, object_key
        FROM attachments
        WHERE message_id = $1
        ORDER BY id
        """,
        row["id"],
    )
    return {
        "messageId": str(row["id"]),
        "chatId": str(row["chat_id"]),
        "senderId": row["sender_id"],
        "body": row["body"],
        "sentAt": row["created_at"].isoformat(),
        "attachments": [
            {
                "attachmentId": str(item["id"]),
                "filename": item["filename"],
                "mimeType": item["mime_type"],
                "downloadUrl": presigned_get_url(config, item["object_key"]),
            }
            for item in attachments
        ],
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.db = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    state.redis = Redis.from_url(settings.redis_url)
    ensure_bucket(settings)
    app.state.services = state
    try:
        yield
    finally:
        await state.redis.aclose()
        await state.db.close()


app = FastAPI(title="WhatsApp Messaging Prototype", lifespan=lifespan)


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


@app.post("/chats", status_code=201)
async def create_chat(payload: CreateChatRequest, actor_user_id: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    participants = sorted(set([actor_user_id, *payload.participants]))
    if len(participants) > 100:
        raise HTTPException(status_code=422, detail="chats are limited to 100 participants")
    chat_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("INSERT INTO chats (id, name, created_by) VALUES ($1, $2, $3)", chat_id, payload.name, actor_user_id)
            await conn.executemany(
                "INSERT INTO chat_participants (chat_id, user_id) VALUES ($1, $2)",
                [(chat_id, user) for user in participants],
            )
    return {"chatId": str(chat_id), "participants": participants}


@app.post("/attachments", status_code=201)
async def create_attachment(
    payload: AttachmentRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
):
    attachment_id = uuid.uuid4()
    object_key = f"{actor_user_id}/{attachment_id}/{payload.filename}"
    await state.db.execute(
        """
        INSERT INTO attachments (id, owner_id, filename, mime_type, object_key, status)
        VALUES ($1, $2, $3, $4, $5, 'pending')
        """,
        attachment_id,
        actor_user_id,
        payload.filename,
        payload.mime_type,
        object_key,
    )
    return {"attachmentId": str(attachment_id), "uploadUrl": presigned_put_url(config, object_key), "method": "PUT"}


@app.post("/chats/{chat_id}/messages", status_code=201)
async def send_message(
    chat_id: uuid.UUID,
    payload: SendMessageRequest,
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
):
    await ensure_participant(state.db, chat_id, actor_user_id)
    message_id = uuid.uuid4()
    async with state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO messages (id, chat_id, sender_id, body) VALUES ($1, $2, $3, $4)",
                message_id,
                chat_id,
                actor_user_id,
                payload.body,
            )
            participants = await conn.fetch("SELECT user_id FROM chat_participants WHERE chat_id = $1", chat_id)
            for participant in participants:
                await conn.execute(
                    """
                    INSERT INTO inbox (user_id, chat_id, message_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    participant["user_id"],
                    chat_id,
                    message_id,
                )
            if payload.attachment_ids:
                await conn.execute(
                    """
                    UPDATE attachments
                    SET message_id = $2, status = 'attached'
                    WHERE owner_id = $1 AND id = ANY($3::uuid[])
                    """,
                    actor_user_id,
                    message_id,
                    payload.attachment_ids,
                )
    await state.redis.publish(f"chat:{chat_id}", json.dumps({"messageId": str(message_id)}))
    return {"messageId": str(message_id), "status": "sent", "fanoutRecipients": len(participants)}


@app.get("/inbox")
async def inbox(
    actor_user_id: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=20, ge=1, le=100),
):
    rows = await state.db.fetch(
        """
        SELECT m.*
        FROM inbox i
        JOIN messages m ON m.id = i.message_id
        WHERE i.user_id = $1
        ORDER BY m.created_at
        LIMIT $2
        """,
        actor_user_id,
        limit,
    )
    return {"messages": [await message_payload(state.db, config, row) for row in rows]}


@app.post("/acks")
async def ack_message(payload: AckRequest, actor_user_id: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    result = await state.db.execute(
        "DELETE FROM inbox WHERE user_id = $1 AND message_id = $2",
        actor_user_id,
        payload.message_id,
    )
    return {"status": "acked" if result != "DELETE 0" else "not_found"}
