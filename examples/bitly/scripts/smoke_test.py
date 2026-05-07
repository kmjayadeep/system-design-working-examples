import json
import time
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE_URL = "http://localhost:8000"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = build_opener(NoRedirect)


def header(headers, name):
    return {key.lower(): value for key, value in headers.items()}[name.lower()]


def post_json(path, payload):
    request = Request(
        BASE_URL + path,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", "connection": "close"},
        method="POST",
    )
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return exc.code, dict(exc.headers), body


def get_without_redirect(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read().decode()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode()


def get_json(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with opener.open(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with opener.open(request, timeout=5) as response:
        return response.status, response.read().decode()


def main():
    instances = set()
    for _ in range(8):
        status, body = get_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, html = get_text("/")
    assert status == 200 and "Bitly URL Shortener" in html, status

    status, _, generated = post_json(
        "/shorten", {"long_url": "https://example.com/generated"}
    )
    assert status == 201, (status, generated)
    code = generated["short_code"]

    status, headers, _ = get_without_redirect(f"/{code}")
    assert status == 302, (status, headers)
    assert header(headers, "location") == "https://example.com/generated"
    assert header(headers, "x-cache") == "MISS"

    status, headers, _ = get_without_redirect(f"/{code}")
    assert status == 302, (status, headers)
    assert header(headers, "x-cache") == "HIT"

    alias = f"my-alias-{int(time.time())}"
    status, _, custom = post_json(
        "/shorten",
        {"long_url": "https://example.com/custom", "custom_alias": alias},
    )
    assert status == 201 and custom["short_code"] == alias, (status, custom)

    status, headers, _ = get_without_redirect(f"/{alias}")
    assert status == 302, (status, headers)
    assert header(headers, "location") == "https://example.com/custom"

    status, _, duplicate = post_json(
        "/shorten",
        {"long_url": "https://example.com/other", "custom_alias": alias},
    )
    assert status == 409, (status, duplicate)

    expires_at = (datetime.now(UTC) + timedelta(seconds=2)).isoformat()
    expiring_alias = f"expires-{int(time.time())}"
    status, _, expiring = post_json(
        "/shorten",
        {
            "long_url": "https://example.com/expired",
            "custom_alias": expiring_alias,
            "expiration_date": expires_at,
        },
    )
    assert status == 201, (status, expiring)
    time.sleep(3)
    status, _, body = get_without_redirect(f"/{expiring_alias}")
    assert status == 410, (status, body)

    status, _, body = get_without_redirect("/missing-code-for-test")
    assert status == 404, (status, body)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok generated={code}")
    print(f"ok custom={alias}")
    print(f"ok expired={expiring_alias}")


if __name__ == "__main__":
    main()
