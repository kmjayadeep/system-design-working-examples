from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


FIXTURE_WEB = {
    "https://example.test": '<html><body><h1>Home</h1><a href="/about">About</a><a href="/products">Products</a></body></html>',
    "https://example.test/about": '<html><body><h1>About</h1><a href="/">Home</a></body></html>',
    "https://example.test/products": '<html><body><h1>Products</h1><a href="/products/snacks">Snacks</a></body></html>',
    "https://example.test/products/snacks": "<html><body><h1>Snacks</h1></body></html>",
}


class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(urljoin(self.base_url, href))

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned:
            self.text.append(cleaned)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be absolute http(s)")
    path = parsed.path or "/"
    return parsed._replace(fragment="", query="", path=path).geturl().rstrip("/")


def fetch_fixture_page(url: str) -> tuple[int, bytes, str, list[str]]:
    normalized = normalize_url(url)
    html = FIXTURE_WEB.get(normalized)
    if html is None:
        return 404, b"", "", []
    parser = LinkParser(normalized)
    parser.feed(html)
    links = [normalize_url(link) for link in parser.links if urlparse(link).netloc == urlparse(normalized).netloc]
    return 200, html.encode(), " ".join(parser.text), links
