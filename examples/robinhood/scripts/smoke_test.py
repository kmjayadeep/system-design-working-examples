import json
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8220"


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(BASE_URL + path, data=data, headers={"content-type": "application/json", "connection": "close"}, method=method)
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"})
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Robinhood" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    assert request_json("/market/prices", "POST", {"symbol": "AAPL", "priceCents": 18000})[0] == 201
    status, buy = request_json("/orders", "POST", {"userId": "alice", "symbol": "AAPL", "side": "buy", "quantity": 2})
    assert status == 201 and buy["status"] == "filled", buy
    status, sell = request_json("/orders", "POST", {"userId": "alice", "symbol": "AAPL", "side": "sell", "quantity": 1})
    assert status == 201 and sell["status"] == "filled", sell
    status, rejected = request_json("/orders", "POST", {"userId": "bob", "symbol": "AAPL", "side": "sell", "quantity": 99})
    assert status == 201 and rejected["status"] == "rejected", rejected
    status, portfolio = request_json("/portfolio/alice")
    assert status == 200 and any(item["symbol"] == "AAPL" for item in portfolio["holdings"]), portfolio
    print(f"ok proxy instances={sorted(instances)}")
    print("ok prices, buy/sell orders, rejections, and portfolio reads")


if __name__ == "__main__":
    main()
