import json
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8270"


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
    assert status == 200 and "Metrics Monitoring" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    status, batch = request_json("/metrics/batch", "POST", {"points": [{"name": "cpu", "value": 50}, {"name": "cpu", "value": 91}, {"name": "mem", "value": 70}]})
    assert status == 202 and batch["accepted"] == 3, batch
    status, series = request_json("/metrics/cpu")
    assert status == 200 and series["count"] == 2 and series["avg"] == 70.5, series
    status, alert = request_json("/alerts", "POST", {"name": "high cpu", "metric": "cpu", "threshold": 80, "direction": "above"})
    assert status == 201 and alert["metric"] == "cpu", alert
    status, fired = request_json("/alerts/evaluate", "POST")
    assert status == 200 and fired["fired"][0]["name"] == "high cpu", fired
    print(f"ok proxy instances={sorted(instances)}")
    print("ok metric ingestion, time-series query, alert creation, and evaluation")


if __name__ == "__main__":
    main()
