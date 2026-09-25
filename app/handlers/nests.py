from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.repository import buy_nest, get_nests_count, open_nest

router = Router()


def nests_keyboard(count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if count > 0:
        builder.button(
            text=f"📦 Открыть гнездо ({count})",
            callback_data="nest:open",
        )

    builder.button(
        text="🌰 Купить гнездо за 250",
        callback_data="nest:buy",
    )

    builder.adjust(1)
    return builder.as_markup()


def rarity_label(rarity: str) -> str:
    labels = {
        "common": "Обычная",
        "rare": "Редкая",
        "epic": "Эпическая",
        "legendary": "Легендарная",
        "mythic": "Мифическая",
    }
    return labels.get(rarity, rarity)


async def nests_text(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    count = await get_nests_count(user_id)

    text = (
        "📦 <b>Гнёзда Бурмалды</b>\n\n"
        f"У тебя неоткрытых гнёзд: <b>{count}</b>\n\n"
        "Цена нового гнезда: <b>250 🌰</b>\n\n"
        "В гнезде может быть новая птичка. "
        "Если выпадет дубликат — получишь компенсацию желудями."
    )

    return text, nests_keyboard(count)


@router.message(F.text == "📦 Гнёзда")
async def nests_handler(message: Message) -> None:
    text, keyboard = await nests_text(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "nest:buy")
async def nest_buy_callback(callback: CallbackQuery) -> None:
    result = await buy_nest(callback.from_user.id)

    if not result["ok"]:
        await callback.answer(
            "Не хватает желудей 🌰",
            show_alert=True,
        )
        return

    text, keyboard = await nests_text(callback.from_user.id)

    await callback.message.edit_text(
        "✅ <b>Гнездо куплено!</b>\n\n"
        f"🌰 Баланс: <b>{result['balance_after']}</b>\n\n"
        f"{text}",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "nest:open")
async def nest_open_callback(callback: CallbackQuery) -> None:
    result = await open_nest(callback.from_user.id)

    if not result["ok"]:
        await callback.answer(
            "Нет доступных гнёзд.",
            show_alert=True,
        )
        return

    if result["is_duplicate"]:
        reward = (
            "Птичка уже была в коллекции.\n"
            f"🌰 Компенсация: <b>+{result['compensation_acorns']}</b>"
        )
    else:
        reward = "🎉 Новая птичка добавлена в коллекцию!"

    text, keyboard = await nests_text(callback.from_user.id)

    await callback.message.edit_text(
        "📦 <b>Гнездо открыто!</b>\n\n"
        f"{result['bird_emoji']} "
        f"<b>{result['bird_title']}</b>\n"
        f"🏷 Редкость: <b>{rarity_label(result['bird_rarity'])}</b>\n\n"
        f"{reward}\n"
        f"🌰 Баланс: <b>{result['balance_after']}</b>\n\n"
        f"{text}",
        reply_markup=keyboard,
    )
    await callback.answer()
