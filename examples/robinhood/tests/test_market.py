from app.market import order_total


def test_order_total_uses_integer_cents():
    assert order_total(quantity=3, price_cents=1250) == 3750
