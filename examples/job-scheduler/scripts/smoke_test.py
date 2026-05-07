import json
import time
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8250"


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
    assert status == 200 and "Job Scheduler" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    status, job = request_json("/jobs", "POST", {"name": "email", "payload": {"to": "a"}, "delaySeconds": 0})
    assert status == 201 and job["status"] == "scheduled", job
    status, ran = request_json("/jobs/run-due", "POST")
    assert status == 200 and ran["jobs"][0]["status"] == "succeeded", ran
    status, runs = request_json(f"/jobs/{job['jobId']}/runs")
    assert status == 200 and runs["runs"][0]["status"] == "succeeded", runs
    status, bad = request_json("/jobs", "POST", {"name": "retry", "payload": {"fail": True}, "delaySeconds": 0, "maxAttempts": 2})
    request_json("/jobs/run-due", "POST")
    time.sleep(1.2)
    status, retried = request_json("/jobs/run-due", "POST")
    assert status == 200 and retried["jobs"][0]["status"] == "failed" and retried["jobs"][0]["attempts"] == 2, retried
    print(f"ok proxy instances={sorted(instances)}")
    print("ok scheduling, due execution, retry, terminal failure, and run history")


if __name__ == "__main__":
    main()
