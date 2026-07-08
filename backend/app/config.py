"""
Конфигурация приложения. Все значения берутся из переменных окружения (.env).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Токен бота, выданный @BotFather. Используется и ботом, и бэкендом
    # (бэкенд нужен для проверки подписи Telegram WebApp initData).
    BOT_TOKEN: str = "PUT_YOUR_BOT_TOKEN_HERE"

    # Username бота без @ (например my_p2p_bot) — нужен для return_url после оплаты
    BOT_USERNAME: str = "my_p2p_bot"

    # ID администраторов бота (через запятую), например "123456789,987654321"
    ADMIN_IDS: str = ""

    # Строка подключения к БД. По умолчанию SQLite-файл рядом с приложением.
    # Для продакшена рекомендуется Postgres:
    # postgresql+psycopg://user:password@host:5432/dbname
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # Публичный HTTPS-адрес, на котором будет открываться Mini App
    # (нужен боту, чтобы прислать кнопку). Например: https://mydomain.ru
    WEBAPP_URL: str = "https://example.com"

    # Учётные данные ЮKassa (https://yookassa.ru/my/merchant/integration/api-keys)
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # Параметры подписки
    SUBSCRIPTION_PRICE_RUB: float = 990.0
    SUBSCRIPTION_DAYS: int = 30

    # Секрет для подписи собственных JWT/сессий (сгенерировать случайную строку)
    APP_SECRET: str = "change_me_to_a_random_string"

    @property
    def admin_ids_list(self) -> list[int]:
        return [int(x) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]


settings = Settings()
