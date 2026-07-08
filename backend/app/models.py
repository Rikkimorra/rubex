import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ListingDirection(str, enum.Enum):
    BUY = "buy"    # хочет купить рубли (отдаёт крипту)
    SELL = "sell"  # хочет продать рубли (получает крипту)


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # telegram user id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    subscription_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    listings: Mapped[list["Listing"]] = relationship(back_populates="user")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")

    @property
    def is_subscribed(self) -> bool:
        return self.subscription_until is not None and self.subscription_until > utcnow()


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    direction: Mapped[ListingDirection] = mapped_column(Enum(ListingDirection))
    amount_rub: Mapped[float] = mapped_column(Float)
    tab: Mapped[str] = mapped_column(String(16), index=True)  # 0-50k / 50-100k / 100-200k / 200k+

    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # курс/условия/валюта и т.п.

    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), default=ListingStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="listings")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    invoice_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # id инвойса CryptoBot
    amount: Mapped[float] = mapped_column(Float)  # сумма в криптоактиве (например USDT)
    asset: Mapped[str] = mapped_column(String(16), default="USDT")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    subscription_days: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")


TAB_RANGES = ("0-50k", "50-100k", "100-200k", "200k+")


def amount_to_tab(amount_rub: float) -> str:
    if amount_rub < 50_000:
        return "0-50k"
    if amount_rub < 100_000:
        return "50-100k"
    if amount_rub < 200_000:
        return "100-200k"
    return "200k+"
