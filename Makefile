.PHONY: bitly-up bitly-test bitly-test-clean bitly-down dropbox-up dropbox-test dropbox-test-clean dropbox-down gopuff-up gopuff-test gopuff-test-clean gopuff-down test

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

test: bitly-test dropbox-test gopuff-test
