import hashlib


def owner_for_key(key: str, nodes: list[str]) -> str:
    if not nodes:
        raise ValueError("nodes cannot be empty")
    digest = hashlib.sha256(key.encode()).hexdigest()
    return nodes[int(digest, 16) % len(nodes)]

