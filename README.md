# System Design Working Examples

Runnable prototypes for common system design problems. Each example is intentionally small enough to run locally, but keeps the major services and data flows close to the design discussion so the behavior is visible.

## Examples

| Example | Reference | What it demonstrates | Stack |
| --- | --- | --- | --- |
| [Bitly URL Shortener](examples/bitly) | [Hello Interview Bitly](https://www.hellointerview.com/learn/system-design/problem-breakdowns/bitly) | Short URL creation, custom aliases, expiration, Redis counters, read-through cache, proxy load balancing, and `302` redirects | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Dropbox File Sync](examples/dropbox) | [Hello Interview Dropbox](https://www.hellointerview.com/learn/system-design/problem-breakdowns/dropbox) | Presigned uploads/downloads, metadata storage, sharing, sync change logs, proxy load balancing, and multipart resumable uploads | Python, FastAPI, Nginx, Postgres, MinIO, Docker Compose |
| [GoPuff Local Delivery](examples/gopuff) | [Hello Interview GoPuff](https://www.hellointerview.com/learn/system-design/problem-breakdowns/gopuff) | Nearby distribution-center availability, Redis availability cache, multi-item orders, and serializable inventory transactions | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [YouTube Video Streaming](examples/youtube) | [Hello Interview YouTube](https://www.hellointerview.com/learn/system-design/problem-breakdowns/youtube) | Presigned large-video uploads, resumable multipart upload state, segment processing, manifests, and cached playback metadata | Python, FastAPI, Nginx, Postgres, Redis, MinIO, Docker Compose |
| [Web Crawler](examples/web-crawler) | [Hello Interview Web Crawler](https://www.hellointerview.com/learn/system-design/problem-breakdowns/web-crawler) | URL frontier queue, crawl dedupe, host politeness, raw/text blob storage, and crawl progress tracking | Python, FastAPI, Nginx, Postgres, Redis, MinIO, Docker Compose |

## Requirements

- Docker Compose
- Python 3.12 or newer for local smoke scripts
- GitHub CLI only if publishing the repository

## Run An Example

```bash
cd examples/bitly
docker compose up --build
```

See each example's README for API details, diagrams, and test commands.

The examples are intentionally disposable: database/object-store data is backed by container tmpfs or in-memory settings and is wiped by `docker compose down`.

Or use the root Makefile:

```bash
make bitly-test
make dropbox-test
make gopuff-test
make youtube-test
make web-crawler-test
```

## Repository Layout

```text
.codex/
  skills/
    create-system-design-example/
examples/
  bitly/
    app/
    tests/
    scripts/
    docker-compose.yml
  dropbox/
    app/
    tests/
    scripts/
    docker-compose.yml
  gopuff/
    app/
    tests/
    scripts/
    docker-compose.yml
  youtube/
    app/
    tests/
    scripts/
    docker-compose.yml
  web-crawler/
    app/
    tests/
    scripts/
    docker-compose.yml
```

## Project Skill

This repo includes a local Codex skill at `.codex/skills/create-system-design-example` for adding future examples with the same conventions: Docker Compose, two API replicas, Nginx as the load balancer/API gateway analogue, ephemeral data stores, README diagrams, Makefile targets, and smoke tests.

## License

MIT
