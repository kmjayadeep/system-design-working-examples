.PHONY: bitly-up bitly-test bitly-test-clean bitly-down dropbox-up dropbox-test dropbox-test-clean dropbox-down gopuff-up gopuff-test gopuff-test-clean gopuff-down ticketmaster-up ticketmaster-test ticketmaster-test-clean ticketmaster-down fb-news-feed-up fb-news-feed-test fb-news-feed-test-clean fb-news-feed-down tinder-up tinder-test tinder-test-clean tinder-down leetcode-up leetcode-test leetcode-test-clean leetcode-down whatsapp-up whatsapp-test whatsapp-test-clean whatsapp-down rate-limiter-up rate-limiter-test rate-limiter-test-clean rate-limiter-down fb-live-comments-up fb-live-comments-test fb-live-comments-test-clean fb-live-comments-down fb-post-search-up fb-post-search-test fb-post-search-test-clean fb-post-search-down youtube-top-k-up youtube-top-k-test youtube-top-k-test-clean youtube-top-k-down uber-up uber-test uber-test-clean uber-down youtube-up youtube-test youtube-test-clean youtube-down web-crawler-up web-crawler-test web-crawler-test-clean web-crawler-down ad-click-aggregator-up ad-click-aggregator-test ad-click-aggregator-test-clean ad-click-aggregator-down news-aggregator-up news-aggregator-test news-aggregator-test-clean news-aggregator-down yelp-up yelp-test yelp-test-clean yelp-down strava-up strava-test strava-test-clean strava-down online-auction-up online-auction-test online-auction-test-clean online-auction-down price-tracking-up price-tracking-test price-tracking-test-clean price-tracking-down instagram-up instagram-test instagram-test-clean instagram-down robinhood-up robinhood-test robinhood-test-clean robinhood-down google-docs-up google-docs-test google-docs-test-clean google-docs-down distributed-cache-up distributed-cache-test distributed-cache-test-clean distributed-cache-down job-scheduler-up job-scheduler-test job-scheduler-test-clean job-scheduler-down payment-system-up payment-system-test payment-system-test-clean payment-system-down metrics-monitoring-up metrics-monitoring-test metrics-monitoring-test-clean metrics-monitoring-down test

bitly-up:
	cd examples/bitly && docker compose up --build

bitly-test:
	cd examples/bitly && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

bitly-test-clean:
	cd examples/bitly && docker compose down -v

bitly-down:
	cd examples/bitly && docker compose down --remove-orphans

dropbox-up:
	cd examples/dropbox && docker compose up --build

dropbox-test:
	cd examples/dropbox && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

dropbox-test-clean:
	cd examples/dropbox && docker compose down -v

dropbox-down:
	cd examples/dropbox && docker compose down --remove-orphans

gopuff-up:
	cd examples/gopuff && docker compose up --build

gopuff-test:
	cd examples/gopuff && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

gopuff-test-clean:
	cd examples/gopuff && docker compose down -v --remove-orphans

gopuff-down:
	cd examples/gopuff && docker compose down --remove-orphans

ticketmaster-up:
	cd examples/ticketmaster && docker compose up --build

ticketmaster-test:
	cd examples/ticketmaster && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

ticketmaster-test-clean:
	cd examples/ticketmaster && docker compose down -v --remove-orphans

ticketmaster-down:
	cd examples/ticketmaster && docker compose down --remove-orphans

fb-news-feed-up:
	cd examples/fb-news-feed && docker compose up --build

fb-news-feed-test:
	cd examples/fb-news-feed && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

fb-news-feed-test-clean:
	cd examples/fb-news-feed && docker compose down -v --remove-orphans

fb-news-feed-down:
	cd examples/fb-news-feed && docker compose down --remove-orphans

tinder-up:
	cd examples/tinder && docker compose up --build

tinder-test:
	cd examples/tinder && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

tinder-test-clean:
	cd examples/tinder && docker compose down -v --remove-orphans

tinder-down:
	cd examples/tinder && docker compose down --remove-orphans

leetcode-up:
	cd examples/leetcode && docker compose up --build

leetcode-test:
	cd examples/leetcode && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

leetcode-test-clean:
	cd examples/leetcode && docker compose down -v --remove-orphans

leetcode-down:
	cd examples/leetcode && docker compose down --remove-orphans

whatsapp-up:
	cd examples/whatsapp && docker compose up --build

whatsapp-test:
	cd examples/whatsapp && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

whatsapp-test-clean:
	cd examples/whatsapp && docker compose down -v --remove-orphans

whatsapp-down:
	cd examples/whatsapp && docker compose down --remove-orphans

rate-limiter-up:
	cd examples/rate-limiter && docker compose up --build

rate-limiter-test:
	cd examples/rate-limiter && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

rate-limiter-test-clean:
	cd examples/rate-limiter && docker compose down -v --remove-orphans

rate-limiter-down:
	cd examples/rate-limiter && docker compose down --remove-orphans

fb-live-comments-up:
	cd examples/fb-live-comments && docker compose up --build

fb-live-comments-test:
	cd examples/fb-live-comments && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

fb-live-comments-test-clean:
	cd examples/fb-live-comments && docker compose down -v --remove-orphans

fb-live-comments-down:
	cd examples/fb-live-comments && docker compose down --remove-orphans

fb-post-search-up:
	cd examples/fb-post-search && docker compose up --build

fb-post-search-test:
	cd examples/fb-post-search && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

fb-post-search-test-clean:
	cd examples/fb-post-search && docker compose down -v --remove-orphans

fb-post-search-down:
	cd examples/fb-post-search && docker compose down --remove-orphans

youtube-top-k-up:
	cd examples/youtube-top-k && docker compose up --build

youtube-top-k-test:
	cd examples/youtube-top-k && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

youtube-top-k-test-clean:
	cd examples/youtube-top-k && docker compose down -v --remove-orphans

youtube-top-k-down:
	cd examples/youtube-top-k && docker compose down --remove-orphans

uber-up:
	cd examples/uber && docker compose up --build

uber-test:
	cd examples/uber && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

uber-test-clean:
	cd examples/uber && docker compose down -v --remove-orphans

uber-down:
	cd examples/uber && docker compose down --remove-orphans

youtube-up:
	cd examples/youtube && docker compose up --build

youtube-test:
	cd examples/youtube && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

youtube-test-clean:
	cd examples/youtube && docker compose down -v --remove-orphans

youtube-down:
	cd examples/youtube && docker compose down --remove-orphans

web-crawler-up:
	cd examples/web-crawler && docker compose up --build

web-crawler-test:
	cd examples/web-crawler && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

web-crawler-test-clean:
	cd examples/web-crawler && docker compose down -v --remove-orphans

web-crawler-down:
	cd examples/web-crawler && docker compose down --remove-orphans

ad-click-aggregator-up:
	cd examples/ad-click-aggregator && docker compose up --build

ad-click-aggregator-test:
	cd examples/ad-click-aggregator && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

ad-click-aggregator-test-clean:
	cd examples/ad-click-aggregator && docker compose down -v --remove-orphans

ad-click-aggregator-down:
	cd examples/ad-click-aggregator && docker compose down --remove-orphans

news-aggregator-up:
	cd examples/news-aggregator && docker compose up --build

news-aggregator-test:
	cd examples/news-aggregator && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

news-aggregator-test-clean:
	cd examples/news-aggregator && docker compose down -v --remove-orphans

news-aggregator-down:
	cd examples/news-aggregator && docker compose down --remove-orphans

yelp-up:
	cd examples/yelp && docker compose up --build

yelp-test:
	cd examples/yelp && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

yelp-test-clean:
	cd examples/yelp && docker compose down -v --remove-orphans

yelp-down:
	cd examples/yelp && docker compose down --remove-orphans

strava-up:
	cd examples/strava && docker compose up --build

strava-test:
	cd examples/strava && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

strava-test-clean:
	cd examples/strava && docker compose down -v --remove-orphans

strava-down:
	cd examples/strava && docker compose down --remove-orphans

online-auction-up:
	cd examples/online-auction && docker compose up --build

online-auction-test:
	cd examples/online-auction && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

online-auction-test-clean:
	cd examples/online-auction && docker compose down -v --remove-orphans

online-auction-down:
	cd examples/online-auction && docker compose down --remove-orphans

price-tracking-up:
	cd examples/price-tracking && docker compose up --build

price-tracking-test:
	cd examples/price-tracking && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

price-tracking-test-clean:
	cd examples/price-tracking && docker compose down -v --remove-orphans

price-tracking-down:
	cd examples/price-tracking && docker compose down --remove-orphans

instagram-up:
	cd examples/instagram && docker compose up --build

instagram-test:
	cd examples/instagram && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

instagram-test-clean:
	cd examples/instagram && docker compose down -v --remove-orphans

instagram-down:
	cd examples/instagram && docker compose down --remove-orphans

robinhood-up:
	cd examples/robinhood && docker compose up --build

robinhood-test:
	cd examples/robinhood && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

robinhood-test-clean:
	cd examples/robinhood && docker compose down -v --remove-orphans

robinhood-down:
	cd examples/robinhood && docker compose down --remove-orphans

google-docs-up:
	cd examples/google-docs && docker compose up --build

google-docs-test:
	cd examples/google-docs && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

google-docs-test-clean:
	cd examples/google-docs && docker compose down -v --remove-orphans

google-docs-down:
	cd examples/google-docs && docker compose down --remove-orphans

distributed-cache-up:
	cd examples/distributed-cache && docker compose up --build

distributed-cache-test:
	cd examples/distributed-cache && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

distributed-cache-test-clean:
	cd examples/distributed-cache && docker compose down -v --remove-orphans

distributed-cache-down:
	cd examples/distributed-cache && docker compose down --remove-orphans

job-scheduler-up:
	cd examples/job-scheduler && docker compose up --build

job-scheduler-test:
	cd examples/job-scheduler && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

job-scheduler-test-clean:
	cd examples/job-scheduler && docker compose down -v --remove-orphans

job-scheduler-down:
	cd examples/job-scheduler && docker compose down --remove-orphans

payment-system-up:
	cd examples/payment-system && docker compose up --build

payment-system-test:
	cd examples/payment-system && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

payment-system-test-clean:
	cd examples/payment-system && docker compose down -v --remove-orphans

payment-system-down:
	cd examples/payment-system && docker compose down --remove-orphans

metrics-monitoring-up:
	cd examples/metrics-monitoring && docker compose up --build

metrics-monitoring-test:
	cd examples/metrics-monitoring && trap 'docker compose down --remove-orphans' EXIT; docker compose up --build -d --remove-orphans && docker compose exec -T api-a python -m pytest -q && python scripts/smoke_test.py

metrics-monitoring-test-clean:
	cd examples/metrics-monitoring && docker compose down -v --remove-orphans

metrics-monitoring-down:
	cd examples/metrics-monitoring && docker compose down --remove-orphans

test: bitly-test dropbox-test gopuff-test ticketmaster-test fb-news-feed-test tinder-test leetcode-test whatsapp-test rate-limiter-test fb-live-comments-test fb-post-search-test youtube-top-k-test uber-test youtube-test web-crawler-test ad-click-aggregator-test news-aggregator-test yelp-test strava-test online-auction-test price-tracking-test instagram-test robinhood-test google-docs-test distributed-cache-test job-scheduler-test payment-system-test metrics-monitoring-test
