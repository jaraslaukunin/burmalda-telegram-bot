from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.repository import get_leaderboard

router = Router()


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🌰 По желудям",
        callback_data="leaderboard:acorns",
    )
    builder.button(
        text="🐦 По уровню",
        callback_data="leaderboard:level",
    )

    builder.adjust(2)
    return builder.as_markup()


async def leaderboard_text(mode: str) -> str:
    rows = await get_leaderboard(mode=mode, limit=10)

    title = (
        "🌰 <b>Топ по желудям</b>"
        if mode == "acorns"
        else "🐦 <b>Топ по уровню птиц</b>"
    )

    if not rows:
        return f"{title}\n\nПока в рейтинге никого нет."

    lines = [title, ""]

    for row in rows:
        username = row.get("username")
        name = f"@{username}" if username else row["first_name"]

        lines.append(
            f"{row['place']}. {row['bird_emoji']} "
            f"<b>{name}</b> — "
            f"{row['acorns']} 🌰 • ур. {row['bird_level']}"
        )

    return "\n".join(lines)


@router.message(F.text == "🏆 Топ")
async def leaderboard_handler(message: Message) -> None:
    await message.answer(
        await leaderboard_text("acorns"),
        reply_markup=leaderboard_keyboard(),
    )


@router.callback_query(F.data.startswith("leaderboard:"))
async def leaderboard_callback(callback: CallbackQuery) -> None:
    mode = callback.data.split(":")[1]

    if mode not in {"acorns", "level"}:
        await callback.answer("Некорректный рейтинг", show_alert=True)
        return

    await callback.message.edit_text(
        await leaderboard_text(mode),
        reply_markup=leaderboard_keyboard(),
    )
    await callback.answer()