"""
Проверка данных авторизации Telegram Mini App (initData).

Как это работает:
- Telegram Mini App при открытии даёт фронтенду строку `initData`
  (подписанную HMAC-SHA256 секретом, производным от токена бота).
- Фронтенд отправляет initData на бэкенд в заголовке Authorization.
- Бэкенд обязан проверить подпись — иначе кто угодно может подделать
  telegram_id и представиться другим пользователем.

Алгоритм проверки описан в официальной документации Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.config import settings

# Максимальный допустимый "возраст" initData (защита от replay-атак).
MAX_INIT_DATA_AGE_SECONDS = 24 * 60 * 60  # 24 часа


class InitDataError(Exception):
    pass


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str, bot_token: str | None = None, max_age: int = MAX_INIT_DATA_AGE_SECONDS) -> dict:
    """
    Проверяет подпись initData и возвращает распарсенные поля (включая user).
    Бросает InitDataError, если подпись невалидна или данные устарели.
    """
    bot_token = bot_token or settings.BOT_TOKEN
    if not init_data:
        raise InitDataError("initData is empty")

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as e:
        raise InitDataError(f"malformed initData: {e}")

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash is missing")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    secret_key = _build_secret_key(bot_token)
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("invalid signature")

    auth_date = int(pairs.get("auth_date", "0"))
    if max_age and (time.time() - auth_date) > max_age:
        raise InitDataError("initData expired")

    result = dict(pairs)
    if "user" in result:
        result["user"] = json.loads(result["user"])
    return result
