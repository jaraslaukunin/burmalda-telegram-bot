from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎮 Игры"),
            KeyboardButton(text="👤 Профиль"),
        ],
        [
            KeyboardButton(text="🎁 Ежедневка"),
            KeyboardButton(text="🐦 Птички"),
        ],
        [
            KeyboardButton(text="🏆 Топ"),
            KeyboardButton(text="📜 Правила"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбирай действие...",
)
