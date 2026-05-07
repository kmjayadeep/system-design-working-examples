from app.main import apply_append


def test_apply_append_adds_newline_between_edits():
    assert apply_append("hello", "world") == "hello\nworld"
