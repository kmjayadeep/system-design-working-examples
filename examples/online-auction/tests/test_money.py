from decimal import Decimal

from app.main import money


def test_money_formats_two_decimal_places():
    assert money(Decimal("12")) == "12.00"
    assert money(Decimal("12.345")) == "12.34"


def test_money_allows_null_current_winner_values():
    assert money(None) is None
