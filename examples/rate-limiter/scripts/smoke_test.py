import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8160"


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={"content-type": "application/json", "connection": "close"},
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
    assert status == 200 and "Distributed Rate Limiter" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, rule = request_json(
        "/rules",
        method="POST",
        payload={"rule_id": "search", "capacity": 3, "refill_per_second": 1},
    )
    assert status == 201 and rule["status"] == "saved", (status, rule)

    decisions = []
    for _ in range(4):
        status, result = request_json("/check?client_id=alice&rule_id=search", method="POST")
        assert status == 200, (status, result)
        decisions.append(result)
    assert [item["allowed"] for item in decisions] == [True, True, True, False], decisions
    assert decisions[-1]["retryAfterMs"] is not None

    status, bob = request_json("/check?client_id=bob&rule_id=search", method="POST")
    assert status == 200 and bob["allowed"] and bob["remaining"] == 2, (status, bob)

    time.sleep(1.1)
    status, refilled = request_json("/check?client_id=alice&rule_id=search", method="POST")
    assert status == 200 and refilled["allowed"], (status, refilled)

    status, default_rule = request_json("/check?client_id=charlie&rule_id=unknown", method="POST")
    assert status == 200 and default_rule["ruleId"] == "default", (status, default_rule)

    print(f"ok proxy instances={sorted(instances)}")
    print("ok shared redis token bucket, denial, refill, and default rule fallback")


if __name__ == "__main__":
    main()
