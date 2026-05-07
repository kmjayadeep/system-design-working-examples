from app.main import media_object_key


def test_media_object_key_includes_owner_and_post_id():
    key = media_object_key("alice", "post-1", "photo")
    assert key == "alice/post-1/photo"
