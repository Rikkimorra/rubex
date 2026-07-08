"""
Telegram-бот: приветствие, кнопка открытия Mini App и пара служебных команд.

Вся бизнес-логика (объявления, оплата, подписка) живёт в Mini App и backend API.
Бот здесь — это "входная дверь": показывает кнопку WebApp и статус подписки.

Запуск: python bot.py (переменные окружения берутся из .env через app.config)
"""
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from app.config import settings
from app.db import SessionLocal
from app.models import User, utcnow

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()


def webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4b1 Открыть RUBex", web_app=WebAppInfo(url=settings.WEBAPP_URL))]
        ]
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет! Это RUBex — площадка обмена рублями внутри Telegram.\n\n"
        "Вкладки по суммам: до 50к, 50-100к, 100-200к, 200к+.\n"
        f"Доступ к размещению объявлений и контактам — по подписке "
        f"({settings.SUBSCRIPTION_PRICE_USDT:.0f} USDT / {settings.SUBSCRIPTION_DAYS} дней).\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение."
    )
    await message.answer(text, reply_markup=webapp_keyboard())


@dp.message(Command("status"))
async def cmd_status(message: Message):
    db = SessionLocal()
    try:
        user = db.get(User, message.from_user.id)
        if user is None or not user.is_subscribed:
            await message.answer("Подписка не активна. Оформить её можно в приложении.", reply_markup=webapp_keyboard())
        else:
            until = user.subscription_until.strftime("%d.%m.%Y %H:%M")
            await message.answer(f"Подписка активна до {until} (МСК может отличаться от UTC).")
    finally:
        db.close()


@dp.message(Command("admin_grant"))
async def cmd_admin_grant(message: Message):
    """/admin_grant <user_id> <days> — ручная выдача подписки администратором (например, до подключения оплаты)."""
    if message.from_user.id not in settings.admin_ids_list:
        return  # молча игнорируем не-админов

    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Использование: /admin_grant <user_id> <days>")
        return

    try:
        target_id, days = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("user_id и days должны быть числами")
        return

    db = SessionLocal()
    try:
        user = db.get(User, target_id)
        if user is None:
            user = User(id=target_id)
            db.add(user)
        base = user.subscription_until if (user.subscription_until and user.subscription_until > utcnow()) else utcnow()
        user.subscription_until = base + timedelta(days=days)
        db.commit()
        await message.answer(f"Пользователю {target_id} выдана подписка на {days} дней.")
    finally:
        db.close()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
