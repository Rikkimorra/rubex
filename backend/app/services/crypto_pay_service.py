"""
Обёртка над Crypto Pay API от @CryptoBot — приём оплаты в криптовалюте (USDT/TON/...).

Как получить токен: в Telegram открыть @CryptoBot (или @CryptoTestnetBot для теста) ->
Crypto Pay -> Create App -> скопировать API Token.

Документация: https://help.send.tg/en/articles/10279948-crypto-pay-api
"""
import hashlib
import hmac

import httpx

from app.config import settings


class CryptoPayError(Exception):
    pass


def _headers() -> dict:
    return {"Crypto-Pay-API-Token": settings.CRYPTO_PAY_API_TOKEN}


def create_subscription_invoice(user_id: int, amount: float, description: str) -> dict:
    """Создаёт инвойс на оплату подписки. Возвращает id, статус и ссылку на оплату."""
    resp = httpx.post(
        f"{settings.CRYPTO_PAY_BASE_URL}/api/createInvoice",
        headers=_headers(),
        json={
            "asset": settings.CRYPTO_PAY_ASSET,
            "amount": f"{amount:.2f}",
            "description": description[:1024],
            "payload": str(user_id),
            "expires_in": 3600,  # инвойс действителен 1 час
        },
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("ok"):
        raise CryptoPayError(f"createInvoice failed: {body}")

    result = body["result"]
    return {
        "id": str(result["invoice_id"]),
        "status": result["status"],
        "pay_url": result.get("bot_invoice_url") or result.get("pay_url"),
    }


def fetch_invoice(invoice_id: str) -> dict:
    """Достаём актуальный статус инвойса напрямую у CryptoBot (не доверяем телу вебхука)."""
    resp = httpx.get(
        f"{settings.CRYPTO_PAY_BASE_URL}/api/getInvoices",
        headers=_headers(),
        params={"invoice_ids": invoice_id},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body.get("ok"):
        raise CryptoPayError(f"getInvoices failed: {body}")

    items = body["result"]["items"]
    if not items:
        raise CryptoPayError(f"invoice {invoice_id} not found")
    return items[0]


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """
    Проверка подписи вебхука CryptoBot: HMAC-SHA256(sha256(API_TOKEN), raw_body).
    Обязательно использовать RAW-тело запроса (до парсинга JSON) для точного совпадения.
    """
    if not signature:
        return False
    secret_key = hashlib.sha256(settings.CRYPTO_PAY_API_TOKEN.encode()).digest()
    computed = hmac.new(secret_key, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)
