.PHONY: bitly-up bitly-test bitly-test-clean bitly-down

bitly-up:
	cd examples/bitly && docker compose up --build

bitly-test:
	cd examples/bitly && trap 'docker compose down' EXIT; docker compose up --build -d; docker compose exec -T api python -m pytest -q; python scripts/smoke_test.py

bitly-test-clean:
	cd examples/bitly && docker compose down -v

bitly-down:
	cd examples/bitly && docker compose down
