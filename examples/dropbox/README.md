# Dropbox File Sync

Small Docker Compose prototype for a Dropbox-style file storage service:

- FastAPI file service
- Nginx reverse proxy in front of two FastAPI replicas
- Postgres metadata, share, chunk, and change-event tables
- MinIO as local S3-compatible blob storage
- Presigned URLs so file bytes go directly between client and blob storage
- Object-created event endpoint that models S3 notifications before metadata is marked uploaded
- Download URLs that model CDN-backed presigned downloads
- Share table optimized for "files shared with this user"
- Sync polling through a per-user change log
- Multipart upload state for resumable large-file uploads

## Run

```bash
docker compose up --build
```

API docs: <http://localhost:8010/docs>

Manual UI: <http://localhost:8010/>

MinIO console: <http://localhost:9002>

Runtime data is intentionally ephemeral. Postgres and MinIO use tmpfs-backed data paths, so `docker compose down` wipes local metadata and files.

Credentials:

```text
minioadmin / minioadmin
```

## Diagram

```mermaid
flowchart LR
    client[Client / Device]
    proxy[Nginx Proxy]
    apiA[FastAPI Replica A]
    apiB[FastAPI Replica B]
    db[(Postgres Metadata DB)]
    blob[(MinIO / S3 Blob Storage)]
    other[Other Devices]

    client -- "POST /files/presigned-url" --> proxy
    proxy --> apiA
    proxy --> apiB
    apiA -- "metadata: pending" --> db
    apiB -- "metadata: pending" --> db
    proxy -- "presigned PUT URL" --> client
    client -- "PUT bytes directly" --> blob
    blob -- "ObjectCreated notification" --> proxy
    apiA -- "HEAD object + status uploaded" --> blob
    apiB -- "HEAD object + status uploaded" --> blob
    apiA -- "change event: created" --> db
    apiB -- "change event: created" --> db

    client -- "GET /files/{id}" --> proxy
    apiA -- "auth + metadata lookup" --> db
    apiB -- "auth + metadata lookup" --> db
    proxy -- "presigned GET URL" --> client
    client -- "download bytes" --> blob

    client -- "POST /files/{id}/share" --> proxy
    apiA -- "file_shares + shared events" --> db
    apiB -- "file_shares + shared events" --> db

    other -- "GET /files/changes?since=N" --> proxy
    apiA -- "per-user change log" --> db
    apiB -- "per-user change log" --> db
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

The server stores metadata as `pending` and returns a presigned `PUT` URL. In production, S3 would emit an object-created notification after the client uploads bytes. In this local demo, simulate that notification:

```http
POST /storage/events/object-created
```

```json
{
  "object_key": "alice/<file-id>/notes.txt",
  "event_name": "ObjectCreated:Put"
}
```

The backend does not trust this event blindly. It looks up file metadata by object key, calls `HeadObject`, verifies the uploaded object size, and only then marks the file `uploaded` and writes the owner's sync change event.

`POST /files/{file_id}/complete` still exists as a client hint for local experimentation, but it uses the same object-store verification path and is not authoritative by itself.

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

For multipart uploads, S3 emits `ObjectCreated:CompleteMultipartUpload` after the backend completes the multipart upload. The demo endpoint immediately verifies the completed object with `HeadObject` and applies the same uploaded transition.

## Try It

```bash
python scripts/smoke_test.py
```

Run unit tests inside the API container:

```bash
docker compose exec -T api-a python -m pytest -q
```

## Design Notes

This prototype follows the Hello Interview Dropbox design: store metadata separately from file bytes, use presigned URLs to avoid routing large files through the app server, keep shares in a separate table, and model device sync with change events.

Upload completion is intentionally storage-confirmed. Clients can report progress, but the backend marks a file uploaded only after object storage can prove the object exists and matches the metadata.

Source: <https://www.hellointerview.com/learn/system-design/problem-breakdowns/dropbox>
