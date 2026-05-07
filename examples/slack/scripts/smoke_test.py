import json
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8280"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(BASE_URL + path, data=data, headers={"content-type": "application/json", "connection": "close", "X-User-Id": user_id}, method=method)
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"})
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Slack" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, workspace = request_json("/workspaces", "POST", {"name": "Acme", "members": ["alice", "bob", "carol"]})
    assert status == 201, workspace
    status, channel = request_json("/channels", "POST", {"workspaceId": workspace["workspaceId"], "name": "engineering", "members": ["alice", "bob"]})
    assert status == 201 and channel["name"] == "engineering", channel
    channel_id = channel["channelId"]

    status, msg = request_json(f"/channels/{channel_id}/messages", "POST", {"body": "deploy plan is ready"}, user_id="bob")
    assert status == 201 and msg["body"] == "deploy plan is ready", msg
    status, reply = request_json(f"/channels/{channel_id}/messages", "POST", {"body": "approved in thread", "parentMessageId": msg["messageId"]})
    assert status == 201 and reply["parentMessageId"] == msg["messageId"], reply

    status, history = request_json(f"/channels/{channel_id}/messages")
    assert status == 200 and [item["body"] for item in history["messages"]] == ["deploy plan is ready"], history
    status, thread = request_json(f"/messages/{msg['messageId']}/thread")
    assert status == 200 and thread["replies"][0]["body"] == "approved in thread", thread
    status, search = request_json(f"/search?workspace_id={workspace['workspaceId']}&q={quote('deploy')}", user_id="bob")
    assert status == 200 and search["results"][0]["messageId"] == msg["messageId"], search
    status, events = request_json(f"/channels/{channel_id}/events?after=0-0")
    assert status == 200 and [event["body"] for event in events["events"]] == ["deploy plan is ready", "approved in thread"], events

    print(f"ok proxy instances={sorted(instances)}")
    print("ok workspaces, channels, messages, threads, search, and live events")


if __name__ == "__main__":
    main()
