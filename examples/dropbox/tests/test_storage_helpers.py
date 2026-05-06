from app.main import metadata_from_row


class FakeRow(dict):
    def __getitem__(self, key):
        return dict.__getitem__(self, key)


def test_metadata_from_row_uses_api_shape():
    row = FakeRow(
        id="file-1",
        name="notes.txt",
        created_at=FakeDate(),
        owner_id="alice",
        size=12,
        mime_type="text/plain",
        status="uploaded",
        fingerprint="abc",
    )

    assert metadata_from_row(row) == {
        "id": "file-1",
        "name": "notes.txt",
        "uploadedAt": "2026-05-06T00:00:00+00:00",
        "uploadedBy": "alice",
        "size": 12,
        "mimeType": "text/plain",
        "status": "uploaded",
        "fingerprint": "abc",
    }


class FakeDate:
    def isoformat(self):
        return "2026-05-06T00:00:00+00:00"
