from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenBucketRule:
    rule_id: str
    capacity: int
    refill_per_second: float


def refill_tokens(rule: TokenBucketRule, current_tokens: float, elapsed_seconds: float) -> float:
    return min(rule.capacity, current_tokens + (elapsed_seconds * rule.refill_per_second))


def retry_after_ms(rule: TokenBucketRule, tokens: float) -> int:
    if tokens >= 1:
        return 0
    return int(((1 - tokens) / rule.refill_per_second) * 1000)
