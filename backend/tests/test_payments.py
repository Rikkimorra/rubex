from types import SimpleNamespace

import app.routers.payments as payments_router
from tests.helpers import auth_headers

BOT_TOKEN = "111111:TEST-BOT-TOKEN"


def test_subscribe_creates_pending_payment(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_payment",
        lambda user_id, amount_rub, bot_username: {
            "id": "fake-payment-1",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/confirm/fake-payment-1",
        },
    )

    headers = auth_headers({"id": 601, "username": "payer"}, BOT_TOKEN)
    res = client.post("/api/subscribe", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["payment_id"] == "fake-payment-1"
    assert body["confirmation_url"].startswith("https://")


def test_subscribe_status_activates_subscription_when_succeeded(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_payment",
        lambda user_id, amount_rub, bot_username: {
            "id": "fake-payment-2",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/confirm/fake-payment-2",
        },
    )
    headers = auth_headers({"id": 602, "username": "payer2"}, BOT_TOKEN)
    client.post("/api/subscribe", headers=headers)

    # Пользователь ещё не подписан
    me_before = client.get("/api/me", headers=headers).json()
    assert me_before["is_subscribed"] is False

    # Эмулируем, что ЮKassa подтвердила оплату
    monkeypatch.setattr(
        payments_router,
        "fetch_payment",
        lambda payment_id: SimpleNamespace(status="succeeded"),
    )

    res = client.get("/api/subscribe/fake-payment-2/status", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "succeeded"

    me_after = client.get("/api/me", headers=headers).json()
    assert me_after["is_subscribed"] is True


def test_webhook_activates_subscription(client, monkeypatch):
    monkeypatch.setattr(
        payments_router,
        "create_subscription_payment",
        lambda user_id, amount_rub, bot_username: {
            "id": "fake-payment-3",
            "status": "pending",
            "confirmation_url": "https://yookassa.example/confirm/fake-payment-3",
        },
    )
    headers = auth_headers({"id": 603, "username": "payer3"}, BOT_TOKEN)
    client.post("/api/subscribe", headers=headers)

    monkeypatch.setattr(
        payments_router,
        "fetch_payment",
        lambda payment_id: SimpleNamespace(status="succeeded"),
    )

    res = client.post(
        "/api/yookassa/webhook",
        json={"event": "payment.succeeded", "object": {"id": "fake-payment-3", "status": "succeeded"}},
    )
    assert res.status_code == 200

    me = client.get("/api/me", headers=headers).json()
    assert me["is_subscribed"] is True
