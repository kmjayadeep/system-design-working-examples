from app.main import should_fail


def test_should_fail_reads_payload_flag():
    assert should_fail({"fail": True}) is True
    assert should_fail({"fail": False}) is False
