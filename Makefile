.PHONY: bitly-up bitly-test bitly-test-clean bitly-down dropbox-up dropbox-test dropbox-test-clean dropbox-down test

bitly-up:
	cd examples/bitly && docker compose up --build

bitly-test:
	cd examples/bitly && trap 'docker compose down' EXIT; docker compose up --build -d && docker compose exec -T api python -m pytest -q && python scripts/smoke_test.py

bitly-test-clean:
	cd examples/bitly && docker compose down -v

bitly-down:
	cd examples/bitly && docker compose down

dropbox-up:
	cd examples/dropbox && docker compose up --build

dropbox-test:
	cd examples/dropbox && trap 'docker compose down' EXIT; docker compose up --build -d && docker compose exec -T api python -m pytest -q && python scripts/smoke_test.py

dropbox-test-clean:
	cd examples/dropbox && docker compose down -v

dropbox-down:
	cd examples/dropbox && docker compose down

test: bitly-test dropbox-test
