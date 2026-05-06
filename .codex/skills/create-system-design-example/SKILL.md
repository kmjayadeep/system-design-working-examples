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
8. Add focused unit tests for deterministic helpers and a `scripts/smoke_test.py` that exercises the real functional requirements through the public proxy port.
9. Add an example README with: purpose, original reference link when available, stack, run command, public ports, Mermaid diagram, API examples, smoke/unit test commands, and design notes.
10. Update root `README.md` and `Makefile` only. Do not add CI unless the user explicitly asks.
11. Run the example test target and stop all containers before finishing.

## Implementation Defaults

- Use `api-a` for `docker compose exec -T api-a python -m pytest -q`.
- Use `proxy` as the only public API port; do not publish each API replica.
- Use `nginx:alpine` with upstreams for `api-a:8000` and `api-b:8000`.
- Use `random;` in the Nginx upstream for local demos, so repeated smoke-test requests visibly hit both replicas.
- Add health checks to API replicas and make the proxy depend on both replicas being healthy.
- Keep smoke tests dependency-light; standard-library `urllib` is enough unless a protocol requires more.
- Use `--remove-orphans` in Makefile down/up test paths to handle service renames cleanly.

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
