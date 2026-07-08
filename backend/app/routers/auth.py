from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.models import User
from app.schemas import MeResponse

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        is_subscribed=user.is_subscribed,
        subscription_until=user.subscription_until,
        subscription_price_rub=settings.SUBSCRIPTION_PRICE_RUB,
        subscription_days=settings.SUBSCRIPTION_DAYS,
    )
