from pydantic import ValidationError

from app.main import CommentRequest


def test_comment_requires_message():
    try:
        CommentRequest(message="")
    except ValidationError:
        return
    raise AssertionError("empty comments should fail validation")
