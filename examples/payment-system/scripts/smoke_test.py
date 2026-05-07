import json
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8260"


def request_json(path, method="GET", payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    all_headers = {"content-type": "application/json", "connection": "close"}
    all_headers.update(headers or {})
    request = Request(BASE_URL + path, data=data, headers=all_headers, method=method)
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def get_text(path):
    request = Request(BASE_URL + path, headers={"connection": "close"})
    with urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def main():
    status, html = get_text("/")
    assert status == 200 and "Payment System" in html
    instances = set()
    for _ in range(12):
        status, body = request_json("/debug/instance")
        assert status == 200
        instances.add(body["instance"])
    assert len(instances) >= 2, instances
    status, method = request_json("/payment-methods", "POST", {"userId": "alice", "token": "tok", "brand": "visa", "last4": "4242"})
    assert status == 201 and method["last4"] == "4242", method
    payload = {"userId": "alice", "merchantId": "store-1", "amountCents": 1299, "currency": "USD"}
    status, payment = request_json("/payments", "POST", payload, {"Idempotency-Key": "idem-1"})
    assert status == 201 and payment["status"] == "captured" and not payment["idempotentReplay"], payment
    status, replay = request_json("/payments", "POST", payload, {"Idempotency-Key": "idem-1"})
    assert status == 201 and replay["paymentId"] == payment["paymentId"] and replay["idempotentReplay"], replay
    status, ledger = request_json(f"/payments/{payment['paymentId']}/ledger")
    assert status == 200 and sum(item["amountCents"] for item in ledger["entries"]) == 0, ledger
    status, refund = request_json(f"/payments/{payment['paymentId']}/refund", "POST")
    assert status == 200 and refund["status"] == "refunded", refund
    status, ledger = request_json(f"/payments/{payment['paymentId']}/ledger")
    assert status == 200 and len(ledger["entries"]) == 4 and sum(item["amountCents"] for item in ledger["entries"]) == 0, ledger
    print(f"ok proxy instances={sorted(instances)}")
    print("ok payment method, idempotent capture, ledger balance, and refund")


if __name__ == "__main__":
    main()
