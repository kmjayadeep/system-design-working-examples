# Project Pattern

## Layout

Each example lives under:

```text
examples/<name>/
  app/
  tests/
  scripts/smoke_test.py
  docker-compose.yml
  nginx.conf
  requirements.txt
  README.md
```

Add extra files only when the example needs them, such as `schema.sql`.

## Compose Topology

Use this shape unless the design requires a different protocol:

```yaml
services:
  api-a: &api
    build: .
    depends_on:
      backing-service:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2).read()"]
      interval: 2s
      timeout: 3s
      retries: 20

  api-b:
    <<: *api

  proxy:
    image: nginx:1.27-alpine
    ports:
      - "<public-port>:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      api-a:
        condition: service_healthy
      api-b:
        condition: service_healthy
```

Use tmpfs for disposable backing stores:

```yaml
tmpfs:
  - /var/lib/postgresql/data
```

For Redis demos, disable persistence:

```yaml
command: redis-server --save "" --appendonly no
```

For MinIO demos, avoid `/data` if the image declares it as a volume; use a tmpfs path such as `/tmp/minio-data`.

## Nginx

Use Nginx as the local load balancer/API gateway analogue:

```nginx
upstream example_api {
    random;
    server api-a:8000;
    server api-b:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://example_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

For WebSocket/SSE examples, extend this with upgrade headers and document whether sticky routing is required.

## Smoke Tests

Smoke tests should prove:

- the public proxy reaches both API replicas via `/debug/instance`
- the manual UI route loads successfully
- each functional requirement works end to end
- important design-specific behavior works, such as cache hits, access control, chunk state, or event polling

Use `Connection: close` for proxy replica probes to avoid client connection reuse hiding load-balancing behavior.

## Makefile

Add four targets:

```make
<name>-up:
	cd examples/<name> && docker compose up --build

<name>-test:
	cd examples/<name> && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

<name>-test-clean:
	cd examples/<name> && docker compose down -v --remove-orphans

<name>-down:
	cd examples/<name> && docker compose down --remove-orphans
```

Also add the example to the aggregate `test` target.

## README

Include:

- stack and design intent
- original system design reference link when the user provides one
- public URLs and credentials for local-only tools
- manual UI URL for testing the functional requirements in a browser
- note that runtime data is ephemeral
- Mermaid architecture diagram with proxy/API gateway, two API replicas, and backing stores
- API examples matching the user's notes
- smoke and unit test commands
- design notes and source link when one was provided

## Root README

Add every example to the root examples table with columns for the example, original reference link, demonstrated concepts, and stack.

## Manual UI

Each example should include a simple browser UI. Prefer a single server-rendered page with plain HTML, CSS, and JavaScript. It should exercise the core functional requirements manually through the same public API endpoints that the smoke test uses. Avoid frontend frameworks and build tooling unless the user asks for a richer app.
