from app.models import amount_to_tab
from tests.conftest import grant_subscription
from tests.helpers import auth_headers

BOT_TOKEN = "111111:TEST-BOT-TOKEN"


def test_amount_to_tab_ranges():
    assert amount_to_tab(1) == "0-50k"
    assert amount_to_tab(49_999) == "0-50k"
    assert amount_to_tab(50_000) == "50-100k"
    assert amount_to_tab(99_999) == "50-100k"
    assert amount_to_tab(100_000) == "100-200k"
    assert amount_to_tab(199_999) == "100-200k"
    assert amount_to_tab(200_000) == "200k+"
    assert amount_to_tab(5_000_000) == "200k+"


def test_me_requires_auth(client):
    res = client.get("/api/me")
    assert res.status_code == 401


def test_me_creates_user_on_first_call(client):
    headers = auth_headers({"id": 501, "username": "newuser", "first_name": "New"}, BOT_TOKEN)
    res = client.get("/api/me", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == 501
    assert body["is_subscribed"] is False


def test_create_listing_requires_subscription(client):
    headers = auth_headers({"id": 502, "username": "nosub"}, BOT_TOKEN)
    res = client.post(
        "/api/listings",
        headers=headers,
        json={"direction": "buy", "amount_rub": 10000, "details": "test"},
    )
    assert res.status_code == 402


def test_create_and_list_listing_with_subscription(client):
    user_id = 503
    grant_subscription(user_id)
    headers = auth_headers({"id": user_id, "username": "subbed"}, BOT_TOKEN)

    res = client.post(
        "/api/listings",
        headers=headers,
        json={"direction": "sell", "amount_rub": 75_000, "details": "курс 95.5"},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["tab"] == "50-100k"
    assert created["author_username"] == "subbed"  # автору свои данные видны

    res = client.get("/api/listings?tab=50-100k", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert any(i["id"] == created["id"] for i in items)


def test_listing_contact_locked_for_unsubscribed_viewer(client):
    owner_id = 504
    grant_subscription(owner_id)
    owner_headers = auth_headers({"id": owner_id, "username": "owner504"}, BOT_TOKEN)
    client.post(
        "/api/listings",
        headers=owner_headers,
        json={"direction": "buy", "amount_rub": 30_000, "details": None},
    )

    viewer_headers = auth_headers({"id": 505, "username": "viewer505"}, BOT_TOKEN)
    res = client.get("/api/listings?tab=0-50k", headers=viewer_headers)
    assert res.status_code == 200
    items = res.json()
    target = [i for i in items if i["author_username"] is None or i.get("contact_locked")]
    assert len(target) >= 1
    assert target[0]["contact_locked"] is True
    assert target[0]["author_username"] is None


def test_close_own_listing(client):
    user_id = 506
    grant_subscription(user_id)
    headers = auth_headers({"id": user_id, "username": "closer"}, BOT_TOKEN)

    created = client.post(
        "/api/listings",
        headers=headers,
        json={"direction": "buy", "amount_rub": 20_000},
    ).json()

    res = client.delete(f"/api/listings/{created['id']}", headers=headers)
    assert res.status_code == 204

    mine = client.get("/api/listings/mine", headers=headers).json()
    assert all(i["id"] != created["id"] for i in mine)


def test_invalid_tab_returns_400(client):
    headers = auth_headers({"id": 507}, BOT_TOKEN)
    res = client.get("/api/listings?tab=not-a-tab", headers=headers)
    assert res.status_code == 400
