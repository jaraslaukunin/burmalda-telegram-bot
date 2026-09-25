from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message

from app.db.repository import get_player_profile

router = Router()


def format_joined_at(value: str | None) -> str:
    if not value:
        return "неизвестно"

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y")
    except ValueError:
        return value[:10]


@router.message(F.text == "👤 Профиль")
async def profile_handler(message: Message) -> None:
    profile = await get_player_profile(message.from_user.id)

    if profile is None:
        await message.answer(
            "Профиль ещё не создан. Нажми /start и попробуй снова."
        )
        return

    bird = profile["user_birds"][0]
    definition = bird["bird_definitions"]

    username = profile.get("username")
    username_text = f"@{username}" if username else "не указан"

    language = profile.get("language", "ru")
    bird_title = (
        definition["title_en"]
        if language == "en"
        else definition["title_ru"]
    )

    level = int(bird["level"])
    xp = int(bird["xp"])
    xp_required = 100 + max(level - 1, 0) * 50

    await message.answer(
        "👤 <b>Профиль игрока</b>\n\n"
        f"🧑 {profile['first_name']}\n"
        f"🔗 {username_text}\n"
        f"📅 В Бурмалде с: {format_joined_at(profile.get('joined_at'))}\n\n"
        f"🌰 Жёлуди: <b>{profile['acorns']}</b>\n"
        f"🎮 Сыграно игр: <b>{profile['games_played']}</b>\n\n"
        "🐦 <b>Активная птичка</b>\n"
        f"{definition['emoji']} {bird_title}\n"
        f"⭐ Уровень: <b>{level}</b>\n"
        f"✨ XP: <b>{xp} / {xp_required}</b>\n"
        f"🏷 Редкость: <b>{definition['rarity']}</b>",
    )
