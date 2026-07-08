import hashlib
import hmac
import json
import time
from urllib.parse import urlencode


def build_init_data(user: dict, bot_token: str, auth_date: int | None = None) -> str:
    """Строит валидную (подписанную) строку initData — как это делает клиент Telegram —
    чтобы можно было протестировать backend-проверку подписи и защищённые эндпоинты."""
    auth_date = auth_date if auth_date is not None else int(time.time())
    params = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date),
        "query_id": "AAEXAMPLEQUERYID",
    }
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = computed_hash
    return urlencode(params)


def auth_headers(user: dict, bot_token: str) -> dict:
    return {"Authorization": f"tma {build_init_data(user, bot_token)}"}
