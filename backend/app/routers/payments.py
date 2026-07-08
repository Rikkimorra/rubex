from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Payment, PaymentStatus, User, utcnow
from app.schemas import SubscribeResponse
from app.services.yookassa_service import create_subscription_payment, fetch_payment

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = create_subscription_payment(
        user_id=user.id,
        amount_rub=settings.SUBSCRIPTION_PRICE_RUB,
        bot_username=settings.BOT_USERNAME,
    )

    payment = Payment(
        user_id=user.id,
        yookassa_payment_id=result["id"],
        amount_rub=settings.SUBSCRIPTION_PRICE_RUB,
        status=PaymentStatus.PENDING,
        subscription_days=settings.SUBSCRIPTION_DAYS,
    )
    db.add(payment)
    db.commit()

    return SubscribeResponse(payment_id=result["id"], confirmation_url=result["confirmation_url"])


def _activate_subscription(db: Session, payment: Payment):
    user = db.get(User, payment.user_id)
    base = user.subscription_until if (user.subscription_until and user.subscription_until > utcnow()) else utcnow()
    user.subscription_until = base + timedelta(days=payment.subscription_days)
    payment.status = PaymentStatus.SUCCEEDED
    payment.confirmed_at = utcnow()
    db.commit()


@router.post("/yookassa/webhook", status_code=status.HTTP_200_OK)
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Обработчик уведомлений ЮKassa. Из соображений безопасности мы НЕ доверяем
    статусу из тела запроса напрямую (его можно подделать, отправив POST на
    этот URL), а перезапрашиваем актуальный статус платежа через API ЮKassa
    по его id.
    """
    body = await request.json()
    payment_id = (body.get("object") or {}).get("id")
    if not payment_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no payment id in payload")

    payment = db.query(Payment).filter(Payment.yookassa_payment_id == payment_id).first()
    if payment is None:
        # Неизвестный платёж — игнорируем, но отвечаем 200, чтобы ЮKassa не повторяла запрос бесконечно
        return {"ok": True}

    if payment.status == PaymentStatus.SUCCEEDED:
        return {"ok": True}

    remote = fetch_payment(payment_id)
    if remote.status == "succeeded":
        _activate_subscription(db, payment)
    elif remote.status == "canceled":
        payment.status = PaymentStatus.CANCELED
        db.commit()

    return {"ok": True}


@router.get("/subscribe/{payment_id}/status")
def subscribe_status(payment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Фронтенд может поллить этот эндпоинт после возврата из оплаты, чтобы обновить статус без ожидания вебхука."""
    payment = db.query(Payment).filter(
        Payment.yookassa_payment_id == payment_id, Payment.user_id == user.id
    ).first()
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "payment not found")

    if payment.status == PaymentStatus.PENDING:
        remote = fetch_payment(payment_id)
        if remote.status == "succeeded":
            _activate_subscription(db, payment)
        elif remote.status == "canceled":
            payment.status = PaymentStatus.CANCELED
            db.commit()

    return {"status": payment.status, "subscription_until": user.subscription_until}
