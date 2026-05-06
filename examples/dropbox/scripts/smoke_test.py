import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8010"


def request_json(path, method="GET", payload=None, user_id="alice"):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        headers={
            "content-type": "application/json",
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
    request = Request(url, data=content, method="PUT")
    with urlopen(request, timeout=10) as response:
        return response.status, dict(response.headers)


def get_bytes(url):
    with urlopen(url, timeout=10) as response:
        return response.status, response.read()


def main():
    content = b"dropbox prototype file contents"
    status, upload = request_json(
        "/files/presigned-url",
        method="POST",
        payload={
            "file_metadata": {
                "name": "notes.txt",
                "size": len(content),
                "mime_type": "text/plain",
                "fingerprint": "sha256-demo",
            }
        },
    )
    assert status == 201, (status, upload)
    status, _ = put_bytes(upload["upload_url"], content)
    assert status == 200

    file_id = upload["file_id"]
    status, completed = request_json(f"/files/{file_id}/complete", method="POST")
    assert status == 200 and completed["status"] == "uploaded", (status, completed)

    status, file_info = request_json(f"/files/{file_id}")
    assert status == 200, (status, file_info)
    status, downloaded = get_bytes(file_info["downloadUrl"])
    assert status == 200 and downloaded == content, downloaded

    status, share = request_json(
        f"/files/{file_id}/share",
        method="POST",
        payload={"users": ["bob"]},
    )
    assert status == 200 and share["status"] == "shared", (status, share)

    status, bob_file = request_json(f"/files/{file_id}", user_id="bob")
    assert status == 200, (status, bob_file)

    status, alice_changes = request_json("/files/changes?since=0")
    assert status == 200 and alice_changes["changes"][0]["type"] == "created"

    status, bob_changes = request_json("/files/changes?since=0", user_id="bob")
    assert status == 200 and bob_changes["changes"][0]["type"] == "shared"

    status, forbidden = request_json(f"/files/{file_id}", user_id="charlie")
    assert status == 404, (status, forbidden)

    part_one = b"a" * (5 * 1024 * 1024)
    part_two = b"tail"
    status, multipart = request_json(
        "/files/multipart/presigned-url",
        method="POST",
        payload={
            "file_metadata": {
                "name": "large.bin",
                "size": len(part_one) + len(part_two),
                "mime_type": "application/octet-stream",
                "fingerprint": "multipart-demo",
            },
            "chunk_size": len(part_one),
        },
    )
    assert status == 201 and len(multipart["parts"]) == 2, (status, multipart)
    multipart_file_id = multipart["file_id"]

    status, part_status = request_json(f"/files/{multipart_file_id}/parts")
    assert status == 200
    assert [part["status"] for part in part_status["parts"]] == ["pending", "pending"]

    for part, content_part in zip(multipart["parts"], [part_one, part_two], strict=True):
        status, headers = put_bytes(part["upload_url"], content_part)
        assert status == 200, (status, headers)
        status, mark = request_json(
            f"/files/{multipart_file_id}/parts/{part['part_number']}",
            method="PATCH",
            payload={"etag": headers["ETag"]},
        )
        assert status == 200 and mark["status"] == "uploaded", (status, mark)

    status, part_status = request_json(f"/files/{multipart_file_id}/parts")
    assert status == 200
    assert [part["status"] for part in part_status["parts"]] == ["uploaded", "uploaded"]

    status, completed_multipart = request_json(
        f"/files/{multipart_file_id}/complete-multipart",
        method="POST",
    )
    assert status == 200 and completed_multipart["status"] == "uploaded", (
        status,
        completed_multipart,
    )

    print(f"ok uploaded={file_id}")
    print("ok downloaded via presigned URL")
    print("ok shared with bob")
    print("ok sync changes for alice and bob")
    print(f"ok multipart={multipart_file_id}")


if __name__ == "__main__":
    main()
