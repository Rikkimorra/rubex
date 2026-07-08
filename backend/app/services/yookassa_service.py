"""
Обёртка над YooKassa SDK.

Документация: https://yookassa.ru/developers/api
Ключи (shopId / secretKey) берутся в личном кабинете ЮKassa:
Настройки -> API ключи и HTTP-уведомления.

ВАЖНО: чтобы принимать оплату картами через ЮKassa как юридическое лицо/ИП/
самозанятый, нужен зарегистрированный магазин в ЮKassa — просто физлицу
подключить приём карт напрямую нельзя. Уточните требования на сайте ЮKassa
или у их поддержки, это не юридическая консультация.
"""
import uuid

from yookassa import Configuration, Payment as YooPayment

from app.config import settings

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_subscription_payment(user_id: int, amount_rub: float, bot_username: str) -> dict:
    idempotence_key = str(uuid.uuid4())
    payment = YooPayment.create(
        {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot_username}",
            },
            "capture": True,
            "description": f"Подписка ({settings.SUBSCRIPTION_DAYS} дней) для пользователя {user_id}",
            "metadata": {"user_id": str(user_id)},
        },
        idempotence_key,
    )
    return {
        "id": payment.id,
        "status": payment.status,
        "confirmation_url": payment.confirmation.confirmation_url,
    }


def fetch_payment(payment_id: str):
    """Достаём актуальный статус платежа напрямую у ЮKassa (не доверяем телу вебхука)."""
    return YooPayment.find_one(payment_id)
