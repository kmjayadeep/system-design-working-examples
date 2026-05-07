from decimal import Decimal

from app.main import money


def test_money_formats_two_decimals():
    assert money(Decimal("99")) == "99.00"
    assert money(Decimal("99.999")) == "100.00"
