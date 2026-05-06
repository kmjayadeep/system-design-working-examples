from app.shortener import (
    base62_decode,
    base62_encode,
    generated_code,
    generated_counter_value,
    validate_custom_alias,
)


def test_base62_encode():
    assert base62_encode(0) == "0"
    assert base62_encode(61) == "Z"
    assert base62_encode(62) == "10"
    assert base62_decode("10") == 62


def test_generated_codes_have_reserved_prefix():
    assert generated_code(1, 11259375).startswith("g")
    assert generated_counter_value(generated_code(123, 11259375), 11259375) == 123


def test_custom_alias_cannot_use_generated_prefix():
    try:
        validate_custom_alias("generated")
    except ValueError as exc:
        assert "cannot start" in str(exc)
    else:
        raise AssertionError("expected generated-prefix alias to be rejected")
