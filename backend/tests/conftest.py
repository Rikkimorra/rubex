import os
import tempfile

# ВАЖНО: переменные окружения должны быть выставлены до первого импорта app.*,
# иначе pydantic-settings успеет прочитать значения по умолчанию.
os.environ.setdefault("BOT_TOKEN", "111111:TEST-BOT-TOKEN")
os.environ.setdefault("BOT_USERNAME", "test_bot")
os.environ.setdefault("ADMIN_IDS", "")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("YOOKASSA_SHOP_ID", "test-shop")
os.environ.setdefault("YOOKASSA_SECRET_KEY", "test-secret")
os.environ.setdefault("SUBSCRIPTION_PRICE_RUB", "990")
os.environ.setdefault("SUBSCRIPTION_DAYS", "30")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models import User, utcnow
from datetime import timedelta


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def grant_subscription(user_id: int, days: int = 30):
    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if user is None:
            user = User(id=user_id)
            session.add(user)
        user.subscription_until = utcnow() + timedelta(days=days)
        session.commit()
    finally:
        session.close()
