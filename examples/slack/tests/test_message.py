from app.main import stream_key


def test_stream_key_uses_channel_id():
    assert stream_key("channel-1") == "channel-events:channel-1"
