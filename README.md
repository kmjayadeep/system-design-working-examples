# System Design Working Examples

Runnable prototypes for common system design problems. Each example is intentionally small enough to run locally, but keeps the major services and data flows close to the design discussion so the behavior is visible.

## Examples

| Example | What it demonstrates | Stack |
| --- | --- | --- |
| [Bitly URL Shortener](examples/bitly) | Short URL creation, custom aliases, expiration, Redis counters, read-through cache, and `302` redirects | Python, FastAPI, Postgres, Redis, Docker Compose |

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

Or use the root Makefile:

```bash
make bitly-test
```

## Repository Layout

```text
examples/
  bitly/
    app/
    tests/
    scripts/
    docker-compose.yml
```

## License

MIT
