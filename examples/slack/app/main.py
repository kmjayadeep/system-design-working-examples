from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
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


class WorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    members: list[str] = Field(default_factory=list)


class ChannelRequest(BaseModel):
    workspace_id: uuid.UUID = Field(alias="workspaceId")
    name: str = Field(min_length=1, max_length=80)
    is_private: bool = Field(default=False, alias="isPrivate")
    members: list[str] = Field(default_factory=list)


class JoinRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)


class MessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    parent_message_id: uuid.UUID | None = Field(default=None, alias="parentMessageId")


def stream_key(channel_id: str) -> str:
    return f"channel-events:{channel_id}"


def get_state(request: Request) -> AppState:
    return request.app.state.services


def user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    return x_user_id


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


app = FastAPI(title="Slack Prototype", lifespan=lifespan)


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


def message_payload(row: asyncpg.Record) -> dict:
    return {
        "messageId": str(row["id"]),
        "workspaceId": str(row["workspace_id"]),
        "channelId": str(row["channel_id"]),
        "userId": row["user_id"],
        "parentMessageId": str(row["parent_message_id"]) if row["parent_message_id"] else None,
        "body": row["body"],
        "createdAt": row["created_at"].isoformat(),
    }


async def require_channel_member(conn: asyncpg.Connection, channel_id: uuid.UUID, actor: str) -> asyncpg.Record:
    row = await conn.fetchrow(
        """
        SELECT c.*
        FROM channels c
        JOIN channel_members cm ON cm.channel_id = c.id AND cm.user_id = $2
        WHERE c.id = $1
        """,
        channel_id,
        actor,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="not a channel member")
    return row


@app.post("/workspaces", status_code=201)
async def create_workspace(payload: WorkspaceRequest, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    workspace_id = uuid.uuid4()
    members = sorted(set(payload.members + [actor]))
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("INSERT INTO workspaces (id, name) VALUES ($1, $2) RETURNING *", workspace_id, payload.name)
            await conn.executemany("INSERT INTO workspace_members (workspace_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", [(workspace_id, member) for member in members])
    return {"workspaceId": str(row["id"]), "name": row["name"], "members": members}


@app.post("/channels", status_code=201)
async def create_channel(payload: ChannelRequest, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    members = sorted(set(payload.members + [actor]))
    async with state.db.acquire() as conn:
        async with conn.transaction():
            workspace_member = await conn.fetchval("SELECT 1 FROM workspace_members WHERE workspace_id = $1 AND user_id = $2", payload.workspace_id, actor)
            if not workspace_member:
                raise HTTPException(status_code=403, detail="not a workspace member")
            channel_id = uuid.uuid4()
            row = await conn.fetchrow(
                "INSERT INTO channels (id, workspace_id, name, is_private) VALUES ($1, $2, $3, $4) RETURNING *",
                channel_id,
                payload.workspace_id,
                payload.name,
                payload.is_private,
            )
            await conn.executemany("INSERT INTO channel_members (channel_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", [(channel_id, member) for member in members])
    return {"channelId": str(row["id"]), "workspaceId": str(row["workspace_id"]), "name": row["name"], "isPrivate": row["is_private"], "members": members}


@app.post("/channels/{channel_id}/join", status_code=201)
async def join_channel(channel_id: uuid.UUID, payload: JoinRequest, state: Annotated[AppState, Depends(get_state)]):
    channel = await state.db.fetchrow("SELECT * FROM channels WHERE id = $1", channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="channel not found")
    if channel["is_private"]:
        raise HTTPException(status_code=403, detail="private channels require invite")
    await state.db.execute("INSERT INTO channel_members (channel_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", channel_id, payload.user_id)
    return {"channelId": str(channel_id), "userId": payload.user_id}


@app.post("/channels/{channel_id}/messages", status_code=201)
async def post_message(
    channel_id: uuid.UUID,
    payload: MessageRequest,
    actor: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(lambda: settings)],
):
    async with state.db.acquire() as conn:
        channel = await require_channel_member(conn, channel_id, actor)
        if payload.parent_message_id:
            parent = await conn.fetchrow("SELECT * FROM messages WHERE id = $1 AND channel_id = $2", payload.parent_message_id, channel_id)
            if parent is None:
                raise HTTPException(status_code=404, detail="parent message not found")
        message_id = uuid.uuid4()
        row = await conn.fetchrow(
            """
            INSERT INTO messages (id, workspace_id, channel_id, user_id, parent_message_id, body)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            message_id,
            channel["workspace_id"],
            channel_id,
            actor,
            payload.parent_message_id,
            payload.body,
        )
    event = message_payload(row)
    stream_event = {key: "" if value is None else str(value) for key, value in event.items()}
    await state.redis.xadd(stream_key(str(channel_id)), stream_event, maxlen=config.stream_max_len)
    return event


@app.get("/channels/{channel_id}/messages")
async def channel_messages(channel_id: uuid.UUID, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)], limit: int = Query(default=50, ge=1, le=100)):
    async with state.db.acquire() as conn:
        await require_channel_member(conn, channel_id, actor)
        rows = await conn.fetch("SELECT * FROM messages WHERE channel_id = $1 AND parent_message_id IS NULL ORDER BY created_at DESC LIMIT $2", channel_id, limit)
    return {"messages": [message_payload(row) for row in rows]}


@app.get("/messages/{message_id}/thread")
async def thread_messages(message_id: uuid.UUID, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        parent = await conn.fetchrow("SELECT * FROM messages WHERE id = $1", message_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="message not found")
        await require_channel_member(conn, parent["channel_id"], actor)
        rows = await conn.fetch("SELECT * FROM messages WHERE parent_message_id = $1 ORDER BY created_at ASC", message_id)
    return {"parent": message_payload(parent), "replies": [message_payload(row) for row in rows]}


@app.get("/search")
async def search_messages(workspace_id: uuid.UUID, q: str, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    rows = await state.db.fetch(
        """
        SELECT m.*
        FROM messages m
        JOIN channel_members cm ON cm.channel_id = m.channel_id AND cm.user_id = $3
        WHERE m.workspace_id = $1 AND to_tsvector('english', m.body) @@ plainto_tsquery('english', $2)
        ORDER BY m.created_at DESC
        LIMIT 20
        """,
        workspace_id,
        q,
        actor,
    )
    return {"results": [message_payload(row) for row in rows]}


@app.get("/channels/{channel_id}/events")
async def channel_events(channel_id: uuid.UUID, after: str = Query(default="0-0"), count: int = Query(default=20, ge=1, le=100), state: Annotated[AppState, Depends(get_state)] = None):
    rows = await state.redis.xrange(stream_key(str(channel_id)), min=f"({after}", max="+", count=count)
    return {"events": [{"streamId": sid, **data} for sid, data in rows]}
