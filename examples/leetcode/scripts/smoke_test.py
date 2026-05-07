import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8140"


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
    assert status == 200 and "LeetCode Judge" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, problems = request_json("/problems")
    assert status == 200 and problems["problems"][0]["problemId"] == "reverse-string", (status, problems)

    status, problem = request_json("/problems/two-sum")
    assert status == 200 and problem["cache"] == "MISS", (status, problem)

    status, cached = request_json("/problems/two-sum")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    code = """def solve(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
"""
    status, queued = request_json(
        "/problems/two-sum/submit",
        method="POST",
        payload={"language": "python", "code": code, "competition_id": "weekly-1"},
    )
    assert status == 202 and queued["status"] == "queued", (status, queued)

    status, pending = request_json(f"/submissions/{queued['submissionId']}")
    assert status == 200 and pending["status"] == "queued", (status, pending)

    status, tick = request_json("/workers/judge/tick?limit=10", method="POST")
    assert status == 200 and tick["processed"] == 1, (status, tick)

    status, result = request_json(f"/submissions/{queued['submissionId']}")
    assert status == 200 and result["status"] == "accepted" and result["passedTests"] == 2, (status, result)

    status, bad = request_json(
        "/problems/two-sum/submit",
        method="POST",
        payload={"language": "python", "code": "def solve(nums, target):\n    return []", "competition_id": "weekly-1"},
        user_id="bob",
    )
    assert status == 202, (status, bad)
    request_json("/workers/judge/tick?limit=10", method="POST")

    status, leaderboard = request_json("/leaderboard/weekly-1")
    assert status == 200 and leaderboard["rankings"][0]["userId"] == "alice", (status, leaderboard)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok submission={queued['submissionId']}")
    print("ok problem cache, queued judge worker, result polling, and leaderboard")


if __name__ == "__main__":
    main()
