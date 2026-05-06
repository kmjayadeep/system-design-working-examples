def split_segments(content: bytes, segment_count: int = 3) -> list[bytes]:
    if segment_count <= 0:
        raise ValueError("segment_count must be positive")
    if not content:
        return [b""]

    size = max(1, len(content) // segment_count)
    segments = [content[index : index + size] for index in range(0, len(content), size)]
    return segments[: segment_count - 1] + [b"".join(segments[segment_count - 1 :])]


def rendition_payload(rendition: str, segment: bytes) -> bytes:
    return f"rendition={rendition}\n".encode() + segment
