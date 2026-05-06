# Dropbox File Sync

Small Docker Compose prototype for a Dropbox-style file storage service:

- FastAPI file service
- Postgres metadata, share, chunk, and change-event tables
- MinIO as local S3-compatible blob storage
- Presigned URLs so file bytes go directly between client and blob storage
- Download URLs that model CDN-backed presigned downloads
- Share table optimized for "files shared with this user"
- Sync polling through a per-user change log
- Multipart upload state for resumable large-file uploads

## Run

```bash
docker compose up --build
```

API docs: <http://localhost:8010/docs>

MinIO console: <http://localhost:9002>

Credentials:

```text
minioadmin / minioadmin
```

## Diagram

```mermaid
flowchart LR
    client[Client / Device]
    api[FastAPI File Service]
    db[(Postgres Metadata DB)]
    blob[(MinIO / S3 Blob Storage)]
    other[Other Devices]

    client -- "POST /files/presigned-url" --> api
    api -- "metadata: pending" --> db
    api -- "presigned PUT URL" --> client
    client -- "PUT bytes directly" --> blob
    client -- "POST /files/{id}/complete" --> api
    api -- "HEAD object + status uploaded" --> blob
    api -- "change event: created" --> db

    client -- "GET /files/{id}" --> api
    api -- "auth + metadata lookup" --> db
    api -- "presigned GET URL" --> client
    client -- "download bytes" --> blob

    client -- "POST /files/{id}/share" --> api
    api -- "file_shares + shared events" --> db

    other -- "GET /files/changes?since=N" --> api
    api -- "per-user change log" --> db
```

## API

All endpoints require `X-User-Id`.

Create a presigned upload:

```http
POST /files/presigned-url
```

```json
{
  "file_metadata": {
    "name": "notes.txt",
    "size": 1234,
    "mime_type": "text/plain",
    "fingerprint": "optional-client-hash"
  }
}
```

The server stores metadata as `pending` and returns a presigned `PUT` URL. After uploading bytes to blob storage, call:

```http
POST /files/{file_id}/complete
```

Download metadata and a presigned download URL:

```http
GET /files/{file_id}
```

Share with users:

```http
POST /files/{file_id}/share
```

```json
{
  "users": ["bob", "carol"]
}
```

Poll for remote changes:

```http
GET /files/changes?since=0
```

## Large File Flow

Create a multipart upload:

```http
POST /files/multipart/presigned-url
```

```json
{
  "file_metadata": {
    "name": "video.mov",
    "size": 53687091200,
    "mime_type": "video/quicktime",
    "fingerprint": "whole-file-hash"
  },
  "chunk_size": 8388608
}
```

The response contains one presigned upload URL per part. After each part upload, save the returned `ETag`:

```http
PATCH /files/{file_id}/parts/{part_number}
```

```json
{
  "etag": "etag-from-s3"
}
```

Resume by checking part status:

```http
GET /files/{file_id}/parts
```

Complete after all parts are uploaded:

```http
POST /files/{file_id}/complete-multipart
```

## Try It

```bash
python scripts/smoke_test.py
```

Run unit tests inside the API container:

```bash
docker compose exec -T api python -m pytest -q
```

## Design Notes

This prototype follows the Hello Interview Dropbox design: store metadata separately from file bytes, use presigned URLs to avoid routing large files through the app server, keep shares in a separate table, and model device sync with change events.

Source: <https://www.hellointerview.com/learn/system-design/problem-breakdowns/dropbox>
