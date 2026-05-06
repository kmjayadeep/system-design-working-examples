import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8040"


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


def main():
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, job = request_json(
        "/crawl-jobs",
        method="POST",
        payload={"seeds": ["https://example.test/"], "max_pages": 4},
    )
    assert status == 201, (status, job)
    job_id = job["jobId"]

    processed = []
    for _ in range(10):
        status, tick = request_json(f"/crawl-jobs/{job_id}/tick?limit=4", method="POST")
        assert status == 200, (status, tick)
        processed.extend(tick["processed"])
        time.sleep(1.1)
        if len(set(processed)) >= 4:
            break
    assert len(set(processed)) == 4, processed

    status, state = request_json(f"/crawl-jobs/{job_id}")
    assert status == 200, (status, state)
    assert state["status"] == "completed"
    crawled = [page for page in state["pages"] if page["status"] == "crawled"]
    assert len(crawled) == 4
    assert all(page["raw_object_key"] and page["text_object_key"] for page in crawled)
    assert len({page["url"] for page in state["pages"]}) == len(state["pages"])

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok job={job_id}")
    print("ok frontier expansion, dedupe, politeness, and blob storage")


if __name__ == "__main__":
    main()
