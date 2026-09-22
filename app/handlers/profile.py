from aiogram import F, Router
from aiogram.types import Message

from app.services.economy import get_balance

router = Router()


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message) -> None:
    balance = await get_balance(message.from_user.id)
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"

    await message.answer(
        "👤 <b>Твой профиль</b>\n\n"
        f"🧑 Игрок: {message.from_user.full_name}\n"
        f"🔗 Username: {username}\n"
        f"🌰 Жёлуди: {balance}\n"
        "⭐ Уровень: 1\n"
        "🐦 Птички-бурмалдички: 0",
        parse_mode="HTML",
    )
