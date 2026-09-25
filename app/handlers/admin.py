from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import ADMIN_TELEGRAM_ID
from app.db.repository import (
    admin_adjust_acorns,
    admin_adjust_bird_xp,
    admin_create_promocode,
    admin_get_player,
    admin_get_stats,
    admin_grant_bird,
    admin_grant_nests,
)

router = Router()


BIRDS = [
    ("forest_burmaldichka", "🐦 Лесная"),
    ("night_burmaldichka", "🦉 Ночная"),
    ("acorn_guardian", "🦅 Жёлудь-Страж"),
    ("firewing_burmaldichka", "🔥 Огнекрылая"),
    ("supreme_burmaldichka", "👑 Верховная"),
    ("mythic_burmalda", "🌌 Мифическая"),
]


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_TELEGRAM_ID


def fmt_date(value: str | None) -> str:
    if not value:
        return "нет данных"

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value[:16]


def admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="🎟 Промокоды", callback_data="admin:promos")
    builder.button(text="🐦 Птицы", callback_data="admin:birds")

    builder.adjust(1)
    return builder.as_markup()


def player_keyboard(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="🌰 +50", callback_data=f"admin:acorns:{target_id}:50")
    builder.button(text="🌰 +100", callback_data=f"admin:acorns:{target_id}:100")
    builder.button(text="🌰 +500", callback_data=f"admin:acorns:{target_id}:500")

    builder.button(text="🌰 −50", callback_data=f"admin:acorns:{target_id}:-50")
    builder.button(text="🌰 −100", callback_data=f"admin:acorns:{target_id}:-100")
    builder.button(text="🌰 −500", callback_data=f"admin:acorns:{target_id}:-500")

    builder.button(text="✨ +50 XP", callback_data=f"admin:xp:{target_id}:50")
    builder.button(text="✨ +100 XP", callback_data=f"admin:xp:{target_id}:100")
    builder.button(text="✨ +500 XP", callback_data=f"admin:xp:{target_id}:500")

    builder.button(text="📦 +1 гнездо", callback_data=f"admin:nest:{target_id}:1")
    builder.button(text="📦 +5 гнёзд", callback_data=f"admin:nest:{target_id}:5")
    builder.button(text="🐦 Выдать птицу", callback_data=f"admin:birds:{target_id}")

    builder.button(text="🔄 Обновить", callback_data=f"admin:player:{target_id}")
    builder.button(text="⬅️ Админка", callback_data="admin:home")

    builder.adjust(3, 3, 3, 2, 1, 1)
    return builder.as_markup()


def birds_keyboard(target_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for code, title in BIRDS:
        builder.button(
            text=title,
            callback_data=f"admin:bird:{target_id}:{code}",
        )

    builder.button(
        text="⬅️ К игроку",
        callback_data=f"admin:player:{target_id}",
    )

    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def promos_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🎁 Создать тестовый +100",
        callback_data="admin:promo:TEST100:100:0:0:100",
    )
    builder.button(
        text="📦 Создать NEST1",
        callback_data="admin:promo:NEST1:0:0:1:100",
    )
    builder.button(
        text="✨ Создать XP100",
        callback_data="admin:promo:XP100:0:100:0:100",
    )
    builder.button(text="⬅️ Админка", callback_data="admin:home")

    builder.adjust(1)
    return builder.as_markup()


async def player_text(target_id: int) -> str | None:
    player = await admin_get_player(
        ADMIN_TELEGRAM_ID,
        target_id,
    )

    if player is None:
        return None

    username = (
        f"@{player['username']}"
        if player.get("username")
        else "username отсутствует"
    )

    bird = (
        f"{player.get('active_bird_emoji') or '🐦'} "
        f"{player.get('active_bird_title') or 'Нет птицы'}"
    )

    return (
        "👤 <b>Карточка игрока</b>\n\n"
        f"🆔 <code>{player['telegram_id']}</code>\n"
        f"🧑 {player['first_name']}\n"
        f"🔗 {username}\n"
        f"📅 Регистрация: {fmt_date(player.get('joined_at'))}\n"
        f"🕒 Последняя активность: {fmt_date(player.get('last_seen_at'))}\n\n"
        f"🌰 Жёлуди: <b>{player['acorns']}</b>\n"
        f"🎮 Игр сыграно: <b>{player['games_played']}</b>\n"
        f"📦 Неоткрытых гнёзд: <b>{player['nests_count']}</b>\n"
        f"🚫 Бан: <b>{'да' if player['is_banned'] else 'нет'}</b>\n\n"
        f"🐦 Активная птица: <b>{bird}</b>\n"
        f"⭐ Уровень: <b>{player.get('active_bird_level') or 0}</b>\n"
        f"✨ XP: <b>{player.get('active_bird_xp') or 0}</b>"
    )


async def show_player(
    callback: CallbackQuery,
    target_id: int,
) -> None:
    text = await player_text(target_id)

    if text is None:
        await callback.message.edit_text(
            "Игрок не найден.",
            reply_markup=admin_main_keyboard(),
        )
        return

    await callback.message.edit_text(
        text,
        reply_markup=player_keyboard(target_id),
    )


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🛠 <b>Админка Бурмалды</b>\n\n"
        "Поиск игрока:\n"
        "<code>/player TELEGRAM_ID</code>\n\n"
        "Пример:\n"
        "<code>/player 855318466</code>",
        reply_markup=admin_main_keyboard(),
    )


@router.message(Command("player"))
async def player_command(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()

    if len(parts) != 2:
        await message.answer(
            "Формат: <code>/player TELEGRAM_ID</code>"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID должен быть числом.")
        return

    text = await player_text(target_id)

    if text is None:
        await message.answer("Игрок не найден.")
        return

    await message.answer(
        text,
        reply_markup=player_keyboard(target_id),
    )


@router.callback_query(F.data == "admin:home")
async def admin_home_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "🛠 <b>Админка Бурмалды</b>\n\n"
        "Найти игрока: <code>/player TELEGRAM_ID</code>",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    stats = await admin_get_stats()

    await callback.message.edit_text(
        "📊 <b>Статистика Бурмалды</b>\n\n"
        f"👥 Игроков: <b>{stats['players_count']}</b>\n"
        f"🟢 Активных за 24ч: <b>{stats['active_players_24h']}</b>\n"
        f"🎮 Игр сыграно: <b>{stats['games_count']}</b>\n"
        f"🌰 Всего желудей: <b>{stats['total_acorns']}</b>\n"
        f"🐦 Птичек у игроков: <b>{stats['birds_count']}</b>\n"
        f"🚫 Бан-лист: <b>{stats['banned_count']}</b>",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:player:"))
async def admin_player_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        target_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Некорректный ID", show_alert=True)
        return

    await show_player(callback, target_id)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:acorns:"))
async def admin_acorns_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        _, _, target_raw, amount_raw = callback.data.split(":")
        target_id = int(target_raw)
        amount = int(amount_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    result = await admin_adjust_acorns(
        target_telegram_id=target_id,
        amount=amount,
        admin_telegram_id=callback.from_user.id,
        reason="admin_button",
    )

    if not result["ok"]:
        await callback.answer(
            "Не удалось изменить баланс.",
            show_alert=True,
        )
        return

    await callback.answer(
        f"{amount:+d} 🌰 • баланс: {result['balance_after']}"
    )
    await show_player(callback, target_id)


@router.callback_query(F.data.startswith("admin:xp:"))
async def admin_xp_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        _, _, target_raw, amount_raw = callback.data.split(":")
        target_id = int(target_raw)
        amount = int(amount_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    result = await admin_adjust_bird_xp(
        target_telegram_id=target_id,
        amount=amount,
        admin_telegram_id=callback.from_user.id,
        reason="admin_button",
    )

    if not result["ok"]:
        await callback.answer(
            "У игрока нет активной птички.",
            show_alert=True,
        )
        return

    await callback.answer(
        f"+{amount} XP • ур. {result['bird_level']}"
    )
    await show_player(callback, target_id)


@router.callback_query(F.data.startswith("admin:nest:"))
async def admin_nest_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        _, _, target_raw, amount_raw = callback.data.split(":")
        target_id = int(target_raw)
        amount = int(amount_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    result = await admin_grant_nests(
        admin_telegram_id=callback.from_user.id,
        target_telegram_id=target_id,
        amount=amount,
        reason="admin_button",
    )

    if not result["ok"]:
        await callback.answer("Игрок не найден.", show_alert=True)
        return

    await callback.answer(
        f"+{amount} 📦 • всего: {result['nests_after']}"
    )
    await show_player(callback, target_id)


@router.callback_query(F.data.startswith("admin:birds:"))
async def admin_birds_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    parts = callback.data.split(":")

    if len(parts) == 2:
        await callback.message.edit_text(
            "🐦 <b>Выдача птицы</b>\n\n"
            "Сначала открой игрока через:\n"
            "<code>/player TELEGRAM_ID</code>",
            reply_markup=admin_main_keyboard(),
        )
        await callback.answer()
        return

    try:
        target_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    await callback.message.edit_text(
        "🐦 <b>Выдать птицу игроку</b>\n\n"
        "Если эта птица уже есть — игрок получит "
        "компенсацию желудями по редкости.",
        reply_markup=birds_keyboard(target_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:bird:"))
async def admin_bird_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        _, _, target_raw, bird_code = callback.data.split(":", maxsplit=3)
        target_id = int(target_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных", show_alert=True)
        return

    result = await admin_grant_bird(
        admin_telegram_id=callback.from_user.id,
        target_telegram_id=target_id,
        bird_code=bird_code,
        reason="admin_button",
    )

    if not result["ok"]:
        await callback.answer("Не удалось выдать птицу.", show_alert=True)
        return

    if result["is_duplicate"]:
        await callback.answer(
            f"Дубликат → +{result['compensation_acorns']} 🌰",
            show_alert=True,
        )
    else:
        await callback.answer(
            f"Выдана птица: {result['bird_title']}",
            show_alert=True,
        )

    await show_player(callback, target_id)


@router.callback_query(F.data == "admin:promos")
async def admin_promos_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "🎟 <b>Промокоды</b>\n\n"
        "Быстрые кнопки создают/обновляют тестовые коды.\n\n"
        "Для своего кода используй команду:\n"
        "<code>/promo КОД ЖЁЛУДИ XP ГНЁЗДА ЛИМИТ</code>\n\n"
        "Пример:\n"
        "<code>/promo HELLO100 100 0 0 100</code>",
        reply_markup=promos_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:promo:"))
async def admin_promo_button_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return

    try:
        _, _, code, acorns_raw, xp_raw, nests_raw, uses_raw = (
            callback.data.split(":")
        )
        acorns = int(acorns_raw)
        xp = int(xp_raw)
        nests = int(nests_raw)
        max_uses = int(uses_raw)
    except (ValueError, IndexError):
        await callback.answer("Ошибка промокода", show_alert=True)
        return

    result = await admin_create_promocode(
        admin_telegram_id=callback.from_user.id,
        code=code,
        reward_acorns=acorns,
        reward_xp=xp,
        reward_nests=nests,
        max_uses=max_uses,
    )

    await callback.answer(f"Промокод {result['code']} готов ✅", show_alert=True)


@router.message(Command("promo"))
async def promo_command(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()

    if len(parts) != 6:
        await message.answer(
            "Формат:\n"
            "<code>/promo КОД ЖЁЛУДИ XP ГНЁЗДА ЛИМИТ</code>\n\n"
            "Лимит `0` = безлимитный.\n"
            "Пример:\n"
            "<code>/promo HELLO100 100 0 0 100</code>"
        )
        return

    try:
        code = parts[1]
        acorns = int(parts[2])
        xp = int(parts[3])
        nests = int(parts[4])
        raw_limit = int(parts[5])
        max_uses = None if raw_limit == 0 else raw_limit
    except ValueError:
        await message.answer("Награды и лимит должны быть числами.")
        return

    result = await admin_create_promocode(
        admin_telegram_id=message.from_user.id,
        code=code,
        reward_acorns=acorns,
        reward_xp=xp,
        reward_nests=nests,
        max_uses=max_uses,
    )

    limit_text = (
        "безлимитный"
        if result["max_uses"] is None
        else str(result["max_uses"])
    )

    await message.answer(
        "✅ <b>Промокод создан</b>\n\n"
        f"🎟 Код: <code>{result['promo_code']}</code>\n"
        f"🌰 Жёлуди: <b>{result['reward_acorns']}</b>\n"
        f"✨ XP: <b>{result['reward_xp']}</b>\n"
        f"📦 Гнёзда: <b>{result['reward_nests']}</b>\n"
        f"👥 Лимит: <b>{limit_text}</b>"
    )
