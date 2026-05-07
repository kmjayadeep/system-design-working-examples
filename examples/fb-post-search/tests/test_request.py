from app.main import tokenize


def test_tokenize_lowercases_and_dedupes_terms():
    assert tokenize("Meta Search, search!") == ["meta", "search"]
