from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.repository import get_player_birds, set_active_bird

router = Router()


def rarity_label(value: str) -> str:
    labels = {
        "common": "Обычная",
        "rare": "Редкая",
        "epic": "Эпическая",
        "legendary": "Легендарная",
        "mythic": "Мифическая",
    }
    return labels.get(value, value)


def effect_label(effect_type: str, effect_value) -> str:
    value = float(effect_value)

    if effect_type == "xp_bonus":
        return f"+{value:g}% опыта в играх"

    if effect_type == "daily_bonus":
        return f"+{value:g} желудей к ежедневке"

    if effect_type == "bonus_drop":
        return f"+{value:g}% шанс малого бонуса"

    return "Уникальный визуальный эффект"


def birds_keyboard(
    birds: list[dict],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for bird in birds:
        status = "✅ " if bird["is_active"] else ""
        builder.button(
            text=(
                f"{status}{bird['bird_emoji']} "
                f"{bird['bird_title']} • ур. {bird['bird_level']}"
            ),
            callback_data=f"bird:open:{bird['user_bird_id']}",
        )

    builder.adjust(1)
    return builder.as_markup()


def bird_detail_keyboard(
    bird: dict,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if not bird["is_active"]:
        builder.button(
            text="✅ Сделать активной",
            callback_data=f"bird:activate:{bird['user_bird_id']}",
        )

    builder.button(
        text="⬅️ Мои птички",
        callback_data="bird:list",
    )

    builder.adjust(1)
    return builder.as_markup()


async def show_birds(
    callback: CallbackQuery,
) -> None:
    birds = await get_player_birds(callback.from_user.id)

    if not birds:
        await callback.message.edit_text(
            "🐦 <b>Птичек пока нет.</b>\n\n"
            "Отправь /start, чтобы получить Птенца Бурмалдички."
        )
        return

    active = next((bird for bird in birds if bird["is_active"]), birds[0])

    await callback.message.edit_text(
        "🐦 <b>Птички-бурмалдички</b>\n\n"
        f"Активная: {active['bird_emoji']} "
        f"<b>{active['bird_title']}</b>\n"
        f"⭐ Уровень: <b>{active['bird_level']}</b>\n"
        f"✨ XP: <b>{active['bird_xp']}</b>\n\n"
        "Выбери птичку, чтобы посмотреть детали:",
        reply_markup=birds_keyboard(birds),
    )


@router.message(F.text == "🐦 Птички")
async def birds_handler(message: Message) -> None:
    birds = await get_player_birds(message.from_user.id)

    if not birds:
        await message.answer(
            "🐦 <b>Птичек пока нет.</b>\n\n"
            "Отправь /start, чтобы получить стартовую птичку."
        )
        return

    active = next((bird for bird in birds if bird["is_active"]), birds[0])

    await message.answer(
        "🐦 <b>Птички-бурмалдички</b>\n\n"
        f"Активная: {active['bird_emoji']} "
        f"<b>{active['bird_title']}</b>\n"
        f"⭐ Уровень: <b>{active['bird_level']}</b>\n"
        f"✨ XP: <b>{active['bird_xp']}</b>\n\n"
        "Выбери птичку, чтобы посмотреть детали:",
        reply_markup=birds_keyboard(birds),
    )


@router.callback_query(F.data == "bird:list")
async def birds_list_callback(callback: CallbackQuery) -> None:
    await show_birds(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("bird:open:"))
async def bird_open_callback(callback: CallbackQuery) -> None:
    try:
        bird_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Некорректная птичка", show_alert=True)
        return

    birds = await get_player_birds(callback.from_user.id)
    bird = next(
        (item for item in birds if item["user_bird_id"] == bird_id),
        None,
    )

    if bird is None:
        await callback.answer("Птичка не найдена", show_alert=True)
        return

    status = "✅ <b>Активная птичка</b>" if bird["is_active"] else "Коллекционная птичка"

    await callback.message.edit_text(
        f"{bird['bird_emoji']} <b>{bird['bird_title']}</b>\n\n"
        f"{status}\n"
        f"🏷 Редкость: <b>{rarity_label(bird['bird_rarity'])}</b>\n"
        f"⭐ Уровень: <b>{bird['bird_level']}</b>\n"
        f"✨ XP: <b>{bird['bird_xp']}</b>\n"
        f"📈 Всего XP: <b>{bird['bird_total_xp']}</b>\n\n"
        f"🪶 {bird['bird_description']}\n\n"
        f"🎁 Эффект: <b>{effect_label(bird['effect_type'], bird['effect_value'])}</b>",
        reply_markup=bird_detail_keyboard(bird),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bird:activate:"))
async def bird_activate_callback(callback: CallbackQuery) -> None:
    try:
        bird_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Некорректная птичка", show_alert=True)
        return

    result = await set_active_bird(
        callback.from_user.id,
        bird_id,
    )

    if not result["ok"]:
        await callback.answer("Не удалось сменить птичку", show_alert=True)
        return

    await callback.answer("Птичка теперь активна ✅")
    await show_birds(callback)
