import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8100"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close", "X-User-Id": user_id},
        method=method,
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, body


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Price Tracking Service" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, history = request_json("/products/B000DEMO/prices")
    assert status == 200 and history["cache"] == "MISS" and len(history["history"]) == 2, (status, history)

    status, cached = request_json("/products/B000DEMO/prices")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, subscription = request_json(
        "/subscriptions",
        method="POST",
        payload={"asin": "B000DEMO", "threshold_price": "100.00"},
    )
    assert status == 201 and subscription["status"] == "subscribed", (status, subscription)

    status, high_price = request_json(
        "/prices",
        method="POST",
        payload={"asin": "B000DEMO", "title": "Demo headphones", "price": "109.99", "source": "extension"},
    )
    assert status == 201, (status, high_price)

    status, first_tick = request_json("/notifications/tick", method="POST")
    assert status == 200 and first_tick["sent"] == 0, (status, first_tick)

    status, low_price = request_json(
        "/prices",
        method="POST",
        payload={"asin": "B000DEMO", "title": "Demo headphones", "price": "89.99", "source": "crawler"},
    )
    assert status == 201, (status, low_price)

    status, second_tick = request_json("/notifications/tick", method="POST")
    assert status == 200 and second_tick["sent"] == 1, (status, second_tick)

    status, notifications = request_json("/notifications")
    assert status == 200 and notifications["notifications"][0]["price"] == "89.99", (status, notifications)

    status, refreshed = request_json("/products/B000DEMO/prices")
    assert status == 200 and refreshed["cache"] == "MISS" and len(refreshed["history"]) == 4, (status, refreshed)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok price history cache, subscriptions, and notification worker")


if __name__ == "__main__":
    main()
