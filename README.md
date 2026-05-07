# System Design Working Examples

Runnable prototypes for common system design problems. Each example is intentionally small enough to run locally, but keeps the major services and data flows close to the design discussion so the behavior is visible.

## Examples

| Example | Reference | What it demonstrates | Stack |
| --- | --- | --- | --- |
| [Bitly URL Shortener](examples/bitly) | [Hello Interview Bitly](https://www.hellointerview.com/learn/system-design/problem-breakdowns/bitly) | Short URL creation, custom aliases, expiration, Redis counters, read-through cache, proxy load balancing, and `302` redirects | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Dropbox File Sync](examples/dropbox) | [Hello Interview Dropbox](https://www.hellointerview.com/learn/system-design/problem-breakdowns/dropbox) | Presigned uploads/downloads, metadata storage, sharing, sync change logs, proxy load balancing, and multipart resumable uploads | Python, FastAPI, Nginx, Postgres, MinIO, Docker Compose |
| [GoPuff Local Delivery](examples/gopuff) | [Hello Interview GoPuff](https://www.hellointerview.com/learn/system-design/problem-breakdowns/gopuff) | Nearby distribution-center availability, Redis availability cache, multi-item orders, and serializable inventory transactions | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Ticketmaster Booking](examples/ticketmaster) | [Hello Interview Ticketmaster](https://www.hellointerview.com/learn/system-design/problem-breakdowns/ticketmaster) | Event search, cached seat-map reads, transactional ticket reservations, booking confirmation, and double-booking prevention | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [FB News Feed](examples/fb-news-feed) | [Hello Interview FB News Feed](https://www.hellointerview.com/learn/system-design/problem-breakdowns/fb-news-feed) | Follow graph writes, post creation, async fanout-on-write, precomputed feed reads, and cursor pagination | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Tinder Matching](examples/tinder) | [Hello Interview Tinder](https://www.hellointerview.com/learn/system-design/problem-breakdowns/tinder) | Profile preferences, nearby recommendation stacks, swipe history exclusion, strongly consistent mutual matches, and match notifications | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [LeetCode Judge](examples/leetcode) | [Hello Interview LeetCode](https://www.hellointerview.com/learn/system-design/problem-breakdowns/leetcode) | Problem browsing, cached problem details, queued code submissions, judge worker results, and competition leaderboard reads | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [WhatsApp Messaging](examples/whatsapp) | [Hello Interview WhatsApp](https://www.hellointerview.com/learn/system-design/problem-breakdowns/whatsapp) | Group chat creation, message fanout, durable offline inboxes, ack-based delivery, and presigned media attachments | Python, FastAPI, Nginx, Postgres, Redis, MinIO, Docker Compose |
| [Distributed Rate Limiter](examples/rate-limiter) | [Hello Interview Rate Limiter](https://www.hellointerview.com/learn/system-design/problem-breakdowns/distributed-rate-limiter) | Shared Redis token buckets, atomic distributed checks, structured allow/deny responses, refill behavior, and default rule fallback | Python, FastAPI, Nginx, Redis, Docker Compose |
| [FB Live Comments](examples/fb-live-comments) | [Hello Interview FB Live Comments](https://www.hellointerview.com/learn/system-design/problem-breakdowns/fb-live-comments) | Comment writes, cursor-paginated history, Redis-backed live streams, and near-real-time polling across replicas | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [FB Post Search](examples/fb-post-search) | [Hello Interview FB Post Search](https://www.hellointerview.com/learn/system-design/problem-breakdowns/fb-post-search) | Post ingestion, likes, durable inverted indexing, cached keyword searches, and recency or like-count ranking | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [YouTube Top K](examples/youtube-top-k) | [Hello Interview YouTube Top K](https://www.hellointerview.com/learn/system-design/problem-breakdowns/top-k) | View ingestion, Redis sorted-set aggregation, all-time and tumbling-window Top K queries, and batched writes | Python, FastAPI, Nginx, Redis, Docker Compose |
| [Uber Ride Sharing](examples/uber) | [Hello Interview Uber](https://www.hellointerview.com/learn/system-design/problem-breakdowns/uber) | Fare estimates, Redis GEO nearby-driver lookup, consistent ride assignment with row locks, and ride lifecycle transitions | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [YouTube Video Streaming](examples/youtube) | [Hello Interview YouTube](https://www.hellointerview.com/learn/system-design/problem-breakdowns/youtube) | Presigned large-video uploads, resumable multipart upload state, segment processing, manifests, and cached playback metadata | Python, FastAPI, Nginx, Postgres, Redis, MinIO, Docker Compose |
| [Web Crawler](examples/web-crawler) | [Hello Interview Web Crawler](https://www.hellointerview.com/learn/system-design/problem-breakdowns/web-crawler) | URL frontier queue, crawl dedupe, host politeness, raw/text blob storage, and crawl progress tracking | Python, FastAPI, Nginx, Postgres, Redis, MinIO, Docker Compose |
| [Ad Click Aggregator](examples/ad-click-aggregator) | [Hello Interview Ad Click Aggregator](https://www.hellointerview.com/learn/system-design/problem-breakdowns/ad-click-aggregator) | Server-side click redirects, Redis click buffering, idempotent event processing, and minute-level aggregate queries | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [News Aggregator](examples/news-aggregator) | [Hello Interview News Aggregator](https://www.hellointerview.com/learn/system-design/problem-breakdowns/google-news) | Publisher ingestion, cached feed reads, cursor pagination, category feeds, and publisher redirects | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Yelp Business Search](examples/yelp) | [Hello Interview Yelp](https://www.hellointerview.com/learn/system-design/problem-breakdowns/yelp) | Business search by name/category/location, cached search results, review writes, one-review-per-user, and average rating updates | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Strava Activity Tracking](examples/strava) | [Hello Interview Strava](https://www.hellointerview.com/learn/system-design/problem-breakdowns/strava) | Live activity tracking, offline point batch upload, lifecycle transitions, route persistence, and friend feed reads | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Online Auction](examples/online-auction) | [Hello Interview Online Auction](https://www.hellointerview.com/learn/system-design/problem-breakdowns/online-auction) | Auction posting, transactional bid contention control, stale bid rejection, cached auction reads, and current winner display | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Price Tracking Service](examples/price-tracking) | [Hello Interview Price Tracking Service](https://www.hellointerview.com/learn/system-design/problem-breakdowns/camelcamelcamel) | Price history reads, product price ingestion, threshold subscriptions, async notification ticks, and cache invalidation | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Instagram Photo Sharing](examples/instagram) | [Hello Interview Instagram](https://www.hellointerview.com/learn/system-design/problem-breakdowns/instagram) | Presigned media uploads, post publishing, follow graph writes, and chronological feed reads | Python, FastAPI, Nginx, Postgres, MinIO, Docker Compose |
| [Robinhood Trading](examples/robinhood) | [Hello Interview Robinhood](https://www.hellointerview.com/learn/system-design/problem-breakdowns/robinhood) | Market price ingestion, transactional buy/sell orders, portfolio updates, and order rejection paths | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Google Docs Collaboration](examples/google-docs) | [Hello Interview Google Docs](https://www.hellointerview.com/learn/system-design/problem-breakdowns/google-docs) | Document sharing, versioned edit operations, conflict detection, and Redis-backed live edit events | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |
| [Distributed Cache](examples/distributed-cache) | [Hello Interview Distributed Cache](https://www.hellointerview.com/learn/system-design/problem-breakdowns/distributed-cache) | Cache key routing, TTL writes, reads, deletes, and visible owner-node assignment | Python, FastAPI, Nginx, Redis, Docker Compose |
| [Job Scheduler](examples/job-scheduler) | [Hello Interview Job Scheduler](https://www.hellointerview.com/learn/system-design/problem-breakdowns/job-scheduler) | Scheduled jobs, due-job claiming, retries, terminal failure, and execution history | Python, FastAPI, Nginx, Postgres, Redis, Docker Compose |

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
make ticketmaster-test
make fb-news-feed-test
make tinder-test
make leetcode-test
make whatsapp-test
make rate-limiter-test
make fb-live-comments-test
make fb-post-search-test
make youtube-top-k-test
make uber-test
make youtube-test
make web-crawler-test
make ad-click-aggregator-test
make news-aggregator-test
make yelp-test
make strava-test
make online-auction-test
make price-tracking-test
make instagram-test
make robinhood-test
make google-docs-test
make distributed-cache-test
make job-scheduler-test
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
  ticketmaster/
    app/
    tests/
    scripts/
    docker-compose.yml
  fb-news-feed/
    app/
    tests/
    scripts/
    docker-compose.yml
  tinder/
    app/
    tests/
    scripts/
    docker-compose.yml
  leetcode/
    app/
    tests/
    scripts/
    docker-compose.yml
  whatsapp/
    app/
    tests/
    scripts/
    docker-compose.yml
  rate-limiter/
    app/
    tests/
    scripts/
    docker-compose.yml
  fb-live-comments/
    app/
    tests/
    scripts/
    docker-compose.yml
  fb-post-search/
    app/
    tests/
    scripts/
    docker-compose.yml
  youtube-top-k/
    app/
    tests/
    scripts/
    docker-compose.yml
  uber/
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
  ad-click-aggregator/
    app/
    tests/
    scripts/
    docker-compose.yml
  news-aggregator/
    app/
    tests/
    scripts/
    docker-compose.yml
  yelp/
    app/
    tests/
    scripts/
    docker-compose.yml
  strava/
    app/
    tests/
    scripts/
    docker-compose.yml
  online-auction/
    app/
    tests/
    scripts/
    docker-compose.yml
  price-tracking/
    app/
    tests/
    scripts/
    docker-compose.yml
  instagram/
    app/
    tests/
    scripts/
    docker-compose.yml
  robinhood/
    app/
    tests/
    scripts/
    docker-compose.yml
  google-docs/
    app/
    tests/
    scripts/
    docker-compose.yml
  distributed-cache/
    app/
    tests/
    scripts/
    docker-compose.yml
  job-scheduler/
    app/
    tests/
    scripts/
    docker-compose.yml
```

## Project Skill

This repo includes a local Codex skill at `.codex/skills/create-system-design-example` for adding future examples with the same conventions: Docker Compose, two API replicas, Nginx as the load balancer/API gateway analogue, ephemeral data stores, README diagrams, Makefile targets, and smoke tests.

## License

MIT
