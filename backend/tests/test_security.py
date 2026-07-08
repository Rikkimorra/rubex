import time

import pytest

from app.security import validate_init_data, InitDataError
from tests.helpers import build_init_data

BOT_TOKEN = "111111:TEST-BOT-TOKEN"


def test_valid_init_data_is_accepted():
    data = build_init_data({"id": 111, "username": "alice", "first_name": "Alice"}, BOT_TOKEN)
    result = validate_init_data(data, bot_token=BOT_TOKEN)
    assert result["user"]["id"] == 111
    assert result["user"]["username"] == "alice"


def test_tampered_hash_is_rejected():
    data = build_init_data({"id": 111}, BOT_TOKEN)
    tampered = data[:-4] + "dead"  # портим хвост хеша
    with pytest.raises(InitDataError):
        validate_init_data(tampered, bot_token=BOT_TOKEN)


def test_wrong_bot_token_is_rejected():
    data = build_init_data({"id": 111}, BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(data, bot_token="222222:OTHER-TOKEN")


def test_expired_init_data_is_rejected():
    old_auth_date = int(time.time()) - 999_999
    data = build_init_data({"id": 111}, BOT_TOKEN, auth_date=old_auth_date)
    with pytest.raises(InitDataError):
        validate_init_data(data, bot_token=BOT_TOKEN, max_age=3600)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError):
        validate_init_data("user=%7B%22id%22%3A111%7D&auth_date=123", bot_token=BOT_TOKEN)
