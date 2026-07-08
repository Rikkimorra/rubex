from datetime import datetime
from pydantic import BaseModel, Field

from app.models import ListingDirection


class MeResponse(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    is_subscribed: bool
    subscription_until: datetime | None
    subscription_price_rub: float
    subscription_days: int


class ListingCreate(BaseModel):
    direction: ListingDirection
    amount_rub: float = Field(gt=0, le=100_000_000)
    details: str | None = Field(default=None, max_length=500)


class ListingOut(BaseModel):
    id: int
    direction: ListingDirection
    amount_rub: float
    tab: str
    details: str | None
    created_at: datetime
    author_username: str | None
    author_first_name: str | None
    contact_locked: bool  # True, если у смотрящего нет подписки — контакт скрыт

    model_config = {"from_attributes": True}


class SubscribeResponse(BaseModel):
    payment_id: str
    confirmation_url: str
