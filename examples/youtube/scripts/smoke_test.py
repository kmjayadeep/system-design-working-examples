import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8030"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={
            "content-type": "application/json",
            "connection": "close",
            "X-User-Id": user_id,
        },
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
        return response.status, dict(response.headers)


def get_bytes(url):
    request = Request(url, headers={"connection": "close"}, method="GET")
    with urlopen(request, timeout=10) as response:
        return response.status, response.read()


def main():
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200, (status, body)
        instances.add(body["instance"])
    assert len(instances) >= 2, instances

    content = b"fake video bytes for adaptive streaming demo" * 128
    status, upload = request_json(
        "/videos/presigned-url",
        method="POST",
        payload={
            "video_metadata": {
                "title": "System Design Walkthrough",
                "description": "A local demo video",
                "size": len(content),
            }
        },
    )
    assert status == 201, (status, upload)
    put_status, _ = put_bytes(upload["uploadUrl"], content)
    assert put_status == 200

    video_id = upload["videoId"]
    status, completed = request_json(f"/videos/{video_id}/complete", method="POST")
    assert status == 200 and completed["status"] == "ready", (status, completed)

    status, video = request_json(f"/videos/{video_id}")
    assert status == 200 and video["cache"] == "MISS", (status, video)
    assert len(video["segments"]) >= 6

    status, cached = request_json(f"/videos/{video_id}")
    assert status == 200 and cached["cache"] == "HIT", (status, cached)

    status, manifest = get_bytes(video["manifestUrl"])
    assert status == 200 and b"renditions" in manifest

    first_segment = video["segments"][0]
    status, segment = get_bytes(first_segment["url"])
    assert status == 200 and segment.startswith(f"rendition={first_segment['rendition']}".encode())

    part_one = b"a" * (5 * 1024 * 1024)
    part_two = b"tail"
    status, multipart = request_json(
        "/videos/multipart/presigned-url",
        method="POST",
        payload={
            "video_metadata": {
                "title": "Multipart Upload",
                "description": "resumable upload demo",
                "size": len(part_one) + len(part_two),
            },
            "chunk_size": len(part_one),
        },
    )
    assert status == 201 and len(multipart["parts"]) == 2, (status, multipart)
    multipart_id = multipart["videoId"]
    for part, content_part in zip(multipart["parts"], [part_one, part_two], strict=True):
        status, headers = put_bytes(part["uploadUrl"], content_part)
        assert status == 200, (status, headers)
        status, marked = request_json(
            f"/videos/{multipart_id}/parts/{part['partNumber']}",
            method="PATCH",
            payload={"etag": headers["ETag"]},
        )
        assert status == 200 and marked["status"] == "uploaded", (status, marked)

    status, parts = request_json(f"/videos/{multipart_id}/parts")
    assert status == 200
    assert [part["status"] for part in parts["parts"]] == ["uploaded", "uploaded"]

    status, completed_multipart = request_json(f"/videos/{multipart_id}/complete-multipart", method="POST")
    assert status == 200 and completed_multipart["status"] == "ready", (status, completed_multipart)

    print(f"ok proxy instances={sorted(instances)}")
    print(f"ok video={video_id}")
    print("ok manifest and adaptive segments")
    print("ok metadata cache miss/hit")
    print(f"ok multipart={multipart_id}")


if __name__ == "__main__":
    main()
