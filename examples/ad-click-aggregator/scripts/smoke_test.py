import json
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE_URL = "http://localhost:8050"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = build_opener(NoRedirect)


def request_json(path, method="GET"):
    request = Request(
        BASE_URL + path,
        headers={"content-type": "application/json", "connection": "close"},
        method=method,
    )
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, dict(exc.headers), body


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with opener.open(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Ad Click Aggregator" in html

    instances = set()
    for _ in range(12):
        status, _, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    for click_id, user_id in [
        ("click-1", "alice"),
        ("click-2", "bob"),
        ("click-3", "alice"),
        ("click-1", "alice"),
    ]:
        status, headers, _ = request_json(f"/click/ad-1?click_id={click_id}&user_id={user_id}")
        assert status == 302, (status, headers)
        assert headers["location"] == "https://advertiser.example/landing"

    status, _, processed = request_json("/processor/tick?limit=10", method="POST")
    assert status == 200, (status, processed)
    assert processed == {"processed": 3, "duplicates": 1}

    status, _, metrics = request_json("/metrics?ad_id=ad-1")
    assert status == 200, (status, metrics)
    assert len(metrics["buckets"]) == 1
    assert metrics["buckets"][0]["clickCount"] == 3
    assert metrics["buckets"][0]["uniqueUsers"] == 2

    print(f"ok proxy instances={sorted(instances)}")
    print("ok redirect tracking")
    print("ok idempotent processing")
    print("ok minute-level metrics")


if __name__ == "__main__":
    main()
