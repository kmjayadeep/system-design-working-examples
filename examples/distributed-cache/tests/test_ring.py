from app.ring import owner_for_key


def test_owner_for_key_is_stable():
    nodes = ["a", "b", "c"]
    assert owner_for_key("user:1", nodes) == owner_for_key("user:1", nodes)
