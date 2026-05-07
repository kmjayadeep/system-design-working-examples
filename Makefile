.PHONY: bitly-up bitly-test bitly-test-clean bitly-down dropbox-up dropbox-test dropbox-test-clean dropbox-down gopuff-up gopuff-test gopuff-test-clean gopuff-down youtube-up youtube-test youtube-test-clean youtube-down web-crawler-up web-crawler-test web-crawler-test-clean web-crawler-down ad-click-aggregator-up ad-click-aggregator-test ad-click-aggregator-test-clean ad-click-aggregator-down news-aggregator-up news-aggregator-test news-aggregator-test-clean news-aggregator-down yelp-up yelp-test yelp-test-clean yelp-down strava-up strava-test strava-test-clean strava-down test

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

test: bitly-test dropbox-test gopuff-test youtube-test web-crawler-test ad-click-aggregator-test news-aggregator-test yelp-test strava-test
