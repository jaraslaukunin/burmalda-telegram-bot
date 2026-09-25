from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message

from app.db.repository import claim_daily

router = Router()


def format_next_claim(value: str | None) -> str:
    if not value:
        return "позже"

    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        seconds = max(0, int((date - now).total_seconds()))
        hours, rest = divmod(seconds, 3600)
        minutes = rest // 60
        return f"{hours} ч {minutes} мин"
    except ValueError:
        return "позже"


@router.message(F.text == "🎁 Ежедневка")
async def daily_handler(message: Message) -> None:
    result = await claim_daily(message.from_user.id)

    if result["ok"]:
        level_up = ""

        if int(result["levels_gained"]) > 0:
            level_up = (
                f"\n🎉 Птичка получила "
                f"+{result['levels_gained']} уровень!"
            )

        await message.answer(
            "🎁 <b>Ежедневная награда получена!</b>\n\n"
            f"🌰 Жёлуди: <b>+{result['acorns_awarded']}</b>\n"
            f"✨ Опыт птичке: <b>+{result['bird_xp_awarded']}</b>\n"
            f"🐦 Уровень птицы: <b>{result['bird_level']}</b>\n"
            f"🌰 Баланс: <b>{result['balance_after']}</b>"
            f"{level_up}",
        )
        return

    if result["reason"] in {"cooldown", "already_claimed_today"}:
        await message.answer(
            "⏳ <b>Ежедневка уже забрана.</b>\n\n"
            f"Следующая награда через: "
            f"<b>{format_next_claim(result.get('next_claim_at'))}</b>"
        )
        return

    await message.answer(
        "Не получилось забрать ежедневную награду. "
        "Попробуй отправить /start."
    )