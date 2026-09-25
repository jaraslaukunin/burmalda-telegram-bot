from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎮 Игры"),
            KeyboardButton(text="👤 Профиль"),
        ],
        [
            KeyboardButton(text="🐦 Птички"),
            KeyboardButton(text="📦 Гнёзда"),
        ],
        [
            KeyboardButton(text="🎁 Ежедневка"),
            KeyboardButton(text="🏆 Топ"),
        ],
        [
            KeyboardButton(text="🎟 Промокод"),
            KeyboardButton(text="📜 Правила"),
        ],
    ],
    resize_keyboard=True,
)