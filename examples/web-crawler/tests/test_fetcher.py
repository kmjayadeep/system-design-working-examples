from app.fetcher import fetch_fixture_page, normalize_url


def test_normalize_url_removes_query_and_fragment():
    assert normalize_url("https://example.test/?a=1#top") == "https://example.test"


def test_fetch_fixture_page_extracts_text_and_links():
    status, raw, text, links = fetch_fixture_page("https://example.test/")
    assert status == 200
    assert b"Home" in raw
    assert "Home" in text
    assert "https://example.test/about" in links
