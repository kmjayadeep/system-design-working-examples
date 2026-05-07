from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import Settings, settings
from app.ui import ui_response


class AppState:
    db: asyncpg.Pool
    redis: Redis


class DocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ShareRequest(BaseModel):
    user_id: str = Field(alias="userId", min_length=1)
    permission: Literal["read", "write"] = "write"


class OperationRequest(BaseModel):
    base_version: int = Field(alias="baseVersion", ge=0)
    text: str = Field(min_length=1, max_length=4000)


def apply_append(content: str, text: str) -> str:
    if not content:
        return text
    return f"{content}\n{text}"


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


app = FastAPI(title="Google Docs Prototype", lifespan=lifespan)


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


def doc_payload(row: asyncpg.Record) -> dict:
    return {
        "documentId": str(row["id"]),
        "ownerId": row["owner_id"],
        "title": row["title"],
        "content": row["content"],
        "version": row["version"],
        "updatedAt": row["updated_at"].isoformat(),
    }


async def require_access(conn: asyncpg.Connection, document_id: uuid.UUID, actor: str, write: bool = False) -> asyncpg.Record:
    row = await conn.fetchrow(
        """
        SELECT d.*, s.permission
        FROM documents d
        LEFT JOIN document_shares s ON s.document_id = d.id AND s.user_id = $2
        WHERE d.id = $1
        """,
        document_id,
        actor,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="document not found")
    allowed = row["owner_id"] == actor or row["permission"] == "write" or (not write and row["permission"] == "read")
    if not allowed:
        raise HTTPException(status_code=403, detail="document access denied")
    return row


@app.post("/documents", status_code=201)
async def create_document(payload: DocumentRequest, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    doc_id = uuid.uuid4()
    row = await state.db.fetchrow(
        "INSERT INTO documents (id, owner_id, title) VALUES ($1, $2, $3) RETURNING *",
        doc_id,
        actor,
        payload.title,
    )
    return doc_payload(row)


@app.post("/documents/{document_id}/share", status_code=201)
async def share_document(document_id: uuid.UUID, payload: ShareRequest, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        doc = await conn.fetchrow("SELECT * FROM documents WHERE id = $1", document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        if doc["owner_id"] != actor:
            raise HTTPException(status_code=403, detail="only owner can share")
        await conn.execute(
            """
            INSERT INTO document_shares (document_id, user_id, permission)
            VALUES ($1, $2, $3)
            ON CONFLICT (document_id, user_id) DO UPDATE SET permission = EXCLUDED.permission
            """,
            document_id,
            payload.user_id,
            payload.permission,
        )
    return {"documentId": str(document_id), "userId": payload.user_id, "permission": payload.permission}


@app.post("/documents/{document_id}/operations", status_code=201)
async def append_operation(
    document_id: uuid.UUID,
    payload: OperationRequest,
    actor: Annotated[str, Depends(user_id)],
    state: Annotated[AppState, Depends(get_state)],
    config: Annotated[Settings, Depends(lambda: settings)],
):
    async with state.db.acquire() as conn:
        async with conn.transaction():
            row = await require_access(conn, document_id, actor, write=True)
            row = await conn.fetchrow("SELECT * FROM documents WHERE id = $1 FOR UPDATE", document_id)
            if row["version"] != payload.base_version:
                raise HTTPException(status_code=409, detail={"currentVersion": row["version"], "content": row["content"]})
            new_content = apply_append(row["content"], payload.text)
            new_version = row["version"] + 1
            row = await conn.fetchrow(
                "UPDATE documents SET content = $1, version = $2, updated_at = now() WHERE id = $3 RETURNING *",
                new_content,
                new_version,
                document_id,
            )
            op_id = await conn.fetchval(
                """
                INSERT INTO document_operations (document_id, user_id, base_version, new_version, text)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                document_id,
                actor,
                payload.base_version,
                new_version,
                payload.text,
            )
    await state.redis.xadd(f"doc-events:{document_id}", {"op_id": op_id, "user_id": actor, "version": new_version, "text": payload.text}, maxlen=config.stream_max_len)
    return {**doc_payload(row), "operationId": op_id}


@app.get("/documents/{document_id}")
async def get_document(document_id: uuid.UUID, actor: Annotated[str, Depends(user_id)], state: Annotated[AppState, Depends(get_state)]):
    async with state.db.acquire() as conn:
        row = await require_access(conn, document_id, actor)
    return doc_payload(row)


@app.get("/documents/{document_id}/events")
async def document_events(document_id: uuid.UUID, state: Annotated[AppState, Depends(get_state)], after: str = Query(default="0-0"), count: int = Query(default=20, ge=1, le=100)):
    rows = await state.redis.xrange(f"doc-events:{document_id}", min=f"({after}", max="+", count=count)
    return {"events": [{"streamId": sid, **data} for sid, data in rows]}
