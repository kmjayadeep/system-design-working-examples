from app.main import ledger_for_capture


def test_ledger_for_capture_balances_to_zero():
    entries = ledger_for_capture(500)
    assert sum(entry["amountCents"] for entry in entries) == 0
