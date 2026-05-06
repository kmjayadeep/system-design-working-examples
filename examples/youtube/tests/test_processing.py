from app.processing import rendition_payload, split_segments


def test_split_segments_keeps_all_bytes():
    content = b"abcdefghij"
    segments = split_segments(content, segment_count=3)
    assert len(segments) == 3
    assert b"".join(segments) == content


def test_rendition_payload_labels_segment():
    assert rendition_payload("360p", b"abc").startswith(b"rendition=360p\n")
