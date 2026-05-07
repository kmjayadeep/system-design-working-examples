import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8150"


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


def put_bytes(url, content):
    request = Request(url, data=content, headers={"connection": "close"}, method="PUT")
    with urlopen(request, timeout=10) as response:
        return response.status


def get_bytes(url):
    request = Request(url, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read()


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "WhatsApp Messaging" in html

    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    status, chat = request_json("/chats", method="POST", payload={"participants": ["bob", "charlie"], "name": "demo"})
    assert status == 201 and sorted(chat["participants"]) == ["alice", "bob", "charlie"], (status, chat)
    chat_id = chat["chatId"]

    status, attachment = request_json("/attachments", method="POST", payload={"filename": "note.txt", "mime_type": "text/plain"})
    assert status == 201, (status, attachment)
    assert put_bytes(attachment["uploadUrl"], b"media bytes") == 200

    status, message = request_json(
        f"/chats/{chat_id}/messages",
        method="POST",
        payload={"body": "hello group", "attachment_ids": [attachment["attachmentId"]]},
    )
    assert status == 201 and message["fanoutRecipients"] == 3, (status, message)
    message_id = message["messageId"]

    status, bob_inbox = request_json("/inbox", user_id="bob")
    assert status == 200 and bob_inbox["messages"][0]["messageId"] == message_id, (status, bob_inbox)
    media_url = bob_inbox["messages"][0]["attachments"][0]["downloadUrl"]
    status, downloaded = get_bytes(media_url)
    assert status == 200 and downloaded == b"media bytes", downloaded

    status, ack = request_json("/acks", method="POST", payload={"message_id": message_id}, user_id="bob")
    assert status == 200 and ack["status"] == "acked", (status, ack)

    status, bob_after_ack = request_json("/inbox", user_id="bob")
    assert status == 200 and bob_after_ack["messages"] == [], (status, bob_after_ack)

    status, charlie_inbox = request_json("/inbox", user_id="charlie")
    assert status == 200 and charlie_inbox["messages"][0]["messageId"] == message_id, (status, charlie_inbox)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok chat={chat_id}")
    print(f"ok message={message_id}")
    print("ok durable inbox, ack deletion, and media presigned URLs")


if __name__ == "__main__":
    main()
