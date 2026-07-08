from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Payment, PaymentStatus, User, utcnow
from app.schemas import SubscribeResponse
from app.services.crypto_pay_service import create_subscription_invoice, fetch_invoice, verify_webhook_signature

router = APIRouter(prefix="/api", tags=["payments"])

# Соответствие статусов CryptoBot нашим внутренним статусам
_STATUS_MAP = {
    "active": PaymentStatus.PENDING,
    "paid": PaymentStatus.SUCCEEDED,
    "expired": PaymentStatus.CANCELED,
}


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = create_subscription_invoice(
        user_id=user.id,
        amount=settings.SUBSCRIPTION_PRICE_USDT,
        description=f"Подписка RUBex на {settings.SUBSCRIPTION_DAYS} дней",
    )

    payment = Payment(
        user_id=user.id,
        invoice_id=result["id"],
        amount=settings.SUBSCRIPTION_PRICE_USDT,
        asset=settings.CRYPTO_PAY_ASSET,
        status=PaymentStatus.PENDING,
        subscription_days=settings.SUBSCRIPTION_DAYS,
    )
    db.add(payment)
    db.commit()

    return SubscribeResponse(payment_id=result["id"], confirmation_url=result["pay_url"])


def _activate_subscription(db: Session, payment: Payment):
    user = db.get(User, payment.user_id)
    base = user.subscription_until if (user.subscription_until and user.subscription_until > utcnow()) else utcnow()
    user.subscription_until = base + timedelta(days=payment.subscription_days)
    payment.status = PaymentStatus.SUCCEEDED
    payment.confirmed_at = utcnow()
    db.commit()


@router.post("/cryptobot/webhook", status_code=status.HTTP_200_OK)
async def cryptobot_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Обработчик вебхука CryptoBot. Проверяем подпись заголовка crypto-pay-api-signature
    по RAW-телу запроса — это защищает от поддельных POST-запросов на этот адрес
    (в отличие от доверия телу запроса "на слово").
    """
    raw_body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature", "")

    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")

    body = await request.json()
    if body.get("update_type") != "invoice_paid":
        return {"ok": True}

    invoice = body.get("payload") or {}
    invoice_id = str(invoice.get("invoice_id", ""))
    if not invoice_id:
        return {"ok": True}

    payment = db.query(Payment).filter(Payment.invoice_id == invoice_id).first()
    if payment is None or payment.status == PaymentStatus.SUCCEEDED:
        return {"ok": True}

    _activate_subscription(db, payment)
    return {"ok": True}


@router.get("/subscribe/{payment_id}/status")
def subscribe_status(payment_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Фронтенд поллит этот эндпоинт после возврата из оплаты, чтобы не ждать вебхук."""
    payment = db.query(Payment).filter(
        Payment.invoice_id == payment_id, Payment.user_id == user.id
    ).first()
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "payment not found")

    if payment.status == PaymentStatus.PENDING:
        remote = fetch_invoice(payment_id)
        mapped = _STATUS_MAP.get(remote["status"])
        if mapped == PaymentStatus.SUCCEEDED:
            _activate_subscription(db, payment)
        elif mapped == PaymentStatus.CANCELED:
            payment.status = PaymentStatus.CANCELED
            db.commit()

    return {"status": payment.status, "subscription_until": user.subscription_until}
