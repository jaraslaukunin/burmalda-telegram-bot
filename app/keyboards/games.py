from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def games_menu():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎰 Бурмалда-Слот",
            callback_data="game:open:slots",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎲 Кубик",
            callback_data="game:open:dice",
        )
    )

    return builder.as_markup()


def slots_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🌰 Крутить за 10",
            callback_data="game:slots:spin",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К играм",
            callback_data="games:menu",
        )
    )

    return builder.as_markup()


def dice_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎲 Бросить за 10",
            callback_data="game:dice:roll",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К играм",
            callback_data="games:menu",
        )
    )

    return builder.as_markup()
