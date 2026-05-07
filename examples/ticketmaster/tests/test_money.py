from decimal import Decimal

from app.main import money


def test_money_formats_prices():
    assert money(Decimal("125")) == "125.00"
