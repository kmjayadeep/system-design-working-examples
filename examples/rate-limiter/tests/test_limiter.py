from app.limiter import TokenBucketRule, refill_tokens, retry_after_ms


def test_refill_tokens_caps_at_capacity():
    rule = TokenBucketRule("search", capacity=10, refill_per_second=2)

    assert refill_tokens(rule, current_tokens=5, elapsed_seconds=10) == 10


def test_retry_after_ms_until_next_token():
    rule = TokenBucketRule("search", capacity=3, refill_per_second=2)

    assert retry_after_ms(rule, tokens=0) == 500
