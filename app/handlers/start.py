from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.menu import main_menu
from app.services.economy import ensure_user

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await ensure_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    name = message.from_user.first_name or "Игрок"

    await message.answer(
        f"🍂 Привет, {name}!\n\n"
        "Добро пожаловать в <b>Бурмалда: Жёлудь-Ленд</b>.\n"
        "На старте тебе выдано 100 виртуальных жёлудей 🌰\n\n"
        "Выбирай режим в меню ниже.",
        reply_markup=main_menu,
        parse_mode="HTML",
    )
