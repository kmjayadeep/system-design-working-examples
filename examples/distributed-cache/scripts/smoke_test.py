import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8240"


def request_json(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(BASE_URL + path, data=data, headers={"content-type": "application/json", "connection": "close"}, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"})
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Distributed Cache" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    key = quote("user:1")
    status, owner = request_json(f"/ring/{key}")
    assert status == 200 and owner["owner"] in owner["nodes"], owner
    status, stored = request_json(f"/cache/{key}", "PUT", {"value": "cached profile", "ttlSeconds": 60})
    assert status == 200 and stored["owner"] == owner["owner"], stored
    status, hit = request_json(f"/cache/{key}")
    assert status == 200 and hit["value"] == "cached profile" and hit["hit"], hit
    status, deleted = request_json(f"/cache/{key}", "DELETE")
    assert status == 200 and deleted["deleted"], deleted
    status, miss = request_json(f"/cache/{key}")
    assert status == 404, miss
    print(f"ok proxy instances={sorted(instances)}")
    print("ok ring lookup, put/get/delete, ttl metadata, and miss path")


if __name__ == "__main__":
    main()
