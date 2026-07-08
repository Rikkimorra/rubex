import hashlib
import hmac
import json

import app.routers.payments as payments_router
from app.services.crypto_pay_service import CryptoPayError
from tests.helpers import auth_headers

BOT_TOKEN = "111111:TEST-BOT-TOKEN"
CRYPTO_TOKEN = "test-crypto-pay-token"


def _sign(raw_body: bytes) -> str:
    secret_key = hashlib.sha256(CRYPTO_TOKEN.encode()).digest()
    return hmac.new(secret_key, raw_body, hashlib.sha256).hexdigest()


def test_subscribe_creates_pending_payment(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_invoice",
        lambda user_id, amount, description: {
            "id": "fake-invoice-1",
            "status": "active",
            "pay_url": "https://t.me/CryptoBot?start=fake-invoice-1",
        },
    )

    headers = auth_headers({"id": 601, "username": "payer"}, BOT_TOKEN)
    res = client.post("/api/subscribe", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["payment_id"] == "fake-invoice-1"
    assert body["confirmation_url"].startswith("https://")


def test_subscribe_status_activates_subscription_when_paid(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_invoice",
        lambda user_id, amount, description: {
            "id": "fake-invoice-2",
            "status": "active",
            "pay_url": "https://t.me/CryptoBot?start=fake-invoice-2",
        },
    )
    headers = auth_headers({"id": 602, "username": "payer2"}, BOT_TOKEN)
    client.post("/api/subscribe", headers=headers)

    me_before = client.get("/api/me", headers=headers).json()
    assert me_before["is_subscribed"] is False

    monkeypatch.setattr(
        payments_router,
        "fetch_invoice",
        lambda invoice_id: {"invoice_id": invoice_id, "status": "paid"},
    )

    res = client.get("/api/subscribe/fake-invoice-2/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "succeeded"

    me_after = client.get("/api/me", headers=headers).json()
    assert me_after["is_subscribed"] is True


def test_subscribe_status_degrades_gracefully_when_cryptobot_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_invoice",
        lambda user_id, amount, description: {
            "id": "fake-invoice-down",
            "status": "active",
            "pay_url": "https://t.me/CryptoBot?start=fake-invoice-down",
        },
    )
    headers = auth_headers({"id": 604, "username": "payer4"}, BOT_TOKEN)
    client.post("/api/subscribe", headers=headers)

    def _boom(invoice_id):
        raise CryptoPayError("CryptoBot API временно недоступен")

    monkeypatch.setattr(payments_router, "fetch_invoice", _boom)

    # Не должно падать 500-й — просто вернуть текущий (pending) статус
    res = client.get("/api/subscribe/fake-invoice-down/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_webhook_rejects_bad_signature(client):
    raw = json.dumps({"update_type": "invoice_paid", "payload": {"invoice_id": 999}}).encode()
    res = client.post(
        "/api/cryptobot/webhook",
        content=raw,
        headers={"crypto-pay-api-signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert res.status_code == 401


def test_webhook_activates_subscription_with_valid_signature(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_invoice",
        lambda user_id, amount, description: {
            "id": "fake-invoice-3",
            "status": "active",
            "pay_url": "https://t.me/CryptoBot?start=fake-invoice-3",
        },
    )
    headers = auth_headers({"id": 603, "username": "payer3"}, BOT_TOKEN)
    client.post("/api/subscribe", headers=headers)

    raw = json.dumps({"update_type": "invoice_paid", "payload": {"invoice_id": "fake-invoice-3"}}).encode()
    signature = _sign(raw)

    res = client.post(
        "/api/cryptobot/webhook",
        content=raw,
        headers={"crypto-pay-api-signature": signature, "Content-Type": "application/json"},
    )
    assert res.status_code == 200

    me = client.get("/api/me", headers=headers).json()
    assert me["is_subscribed"] is True
