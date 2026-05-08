---
name: create-system-design-example
description: Create new runnable examples in the system-design-working-examples repository from system design notes, problem breakdowns, or URLs. Use when Codex is asked to add another system design example like Bitly or Dropbox, scaffold an example under the examples directory, wire Docker Compose services, add a lightweight load-balancer/API-gateway proxy with multiple API replicas, write README diagrams/API docs, create smoke tests, and update root project commands.
---

# Create System Design Example

## Overview

Build small but faithful working prototypes for this repository. The goal is to make system design behavior visible locally, not to simulate production scale.

Read [references/project-pattern.md](references/project-pattern.md) before implementation unless the user asks only for a tiny edit.

## Workflow

1. Extract functional requirements, non-functional requirements, core entities, APIs, and deep-dive mechanisms from the user's notes. If the user provides a current external URL, browse it and cite it in both the root example table and the example README.
2. Create the example under `examples/<kebab-name>`.
3. Prefer Python + FastAPI for API services unless the repo has moved to another default.
4. Add `docker-compose.yml` with at least two API replicas, named `api-a` and `api-b`, behind an Nginx `proxy` service. Treat Nginx as the local stand-in for a load balancer/API gateway.
5. Make API replicas stateless. Put shared state in backing services such as Postgres, Redis, or MinIO.
6. Use ephemeral runtime storage. Prefer tmpfs-backed data directories and disable persistence where possible. Normal `docker compose down` should wipe local data.
7. Add a small `/debug/instance` endpoint and make the smoke test verify the proxy reaches both API replicas.
8. Add a simple web UI for manually testing the functional requirements through the public proxy. Keep it basic, local, and served by the app or proxy; it does not need a frontend build step.
9. Add focused unit tests for deterministic helpers and a `scripts/smoke_test.py` that exercises the real functional requirements through the public proxy port, including a basic assertion that the UI route loads.
10. Add an example README with: purpose, original reference link when available, stack, run command, public ports, manual UI URL, Mermaid diagram, API examples, smoke/unit test commands, and design notes.
11. Update root `README.md` and `Makefile` only. Do not add CI unless the user explicitly asks.
12. Run the example test target and stop all containers before finishing.

## Implementation Defaults

- Use `api-a` for `docker compose exec -T api-a python -m pytest -q`.
- Use `proxy` as the only public API port; do not publish each API replica.
- Use `nginx:alpine` with upstreams for `api-a:8000` and `api-b:8000`.
- Use `random;` in the Nginx upstream for local demos, so repeated smoke-test requests visibly hit both replicas.
- Add health checks to API replicas and make the proxy depend on both replicas being healthy.
- Keep smoke tests dependency-light; standard-library `urllib` is enough unless a protocol requires more.
- Keep UIs dependency-light; plain server-rendered HTML/CSS/JS is preferred for these prototypes.
- Use `--remove-orphans` in Makefile down/up test paths to handle service renames cleanly.

## MinIO / S3 Upload Completion

When an example uses presigned uploads and has a metadata transition such as `pending -> uploaded`, `pending -> published`, or `pending_upload -> ready`, do not trust the client to mark the upload complete.

Use real MinIO bucket notifications in Compose:

- Configure the MinIO service with a webhook target such as:

```yaml
environment:
  MINIO_NOTIFY_WEBHOOK_ENABLE_example: "on"
  MINIO_NOTIFY_WEBHOOK_ENDPOINT_example: "http://proxy/storage/events/minio"
```

- Add a one-shot `minio-events` setup container using `minio/mc`:

```yaml
minio-events:
  image: minio/mc:RELEASE.2025-04-16T18-13-26Z
  depends_on:
    minio:
      condition: service_healthy
    proxy:
      condition: service_started
  entrypoint: /bin/sh
  command:
    - -c
    - |
      set -eu
      mc alias set local http://minio:9000 minioadmin minioadmin
      mc mb --ignore-existing local/<bucket>
      mc event remove --force local/<bucket> arn:minio:sqs::example:webhook || true
      mc event add local/<bucket> arn:minio:sqs::example:webhook --event put
      mc event list local/<bucket>
```

- Implement a webhook endpoint that accepts MinIO's native `Records[]` payload, decodes `record.s3.object.key` with `unquote_plus`, ignores unrelated object keys, calls `HeadObject`, verifies size/metadata when available, and performs an idempotent status transition.
- Smoke tests should upload bytes to the presigned URL and then poll the API until storage-confirmed status appears. They should not call a fake event endpoint or a client-side completion endpoint for simple uploads.
- Client completion endpoints may exist as local hints for multipart or manual testing, but the normal simple-upload path should be asynchronous and storage-confirmed.

## Validation

Run:

```bash
make <example>-test
```

The target should:

- start Compose
- run unit tests in `api-a`
- run `scripts/smoke_test.py` through the proxy
- stop Compose even when tests fail

Before the final response, run `docker ps` and confirm no example containers are left running.
