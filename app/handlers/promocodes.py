from aiogram import F, Router
from aiogram.types import Message

from app.db.repository import redeem_promocode

router = Router()

waiting_for_code: set[int] = set()


@router.message(F.text == "🎟 Промокод")
async def promocode_start(message: Message) -> None:
    waiting_for_code.add(message.from_user.id)

    await message.answer(
        "🎟 <b>Активация промокода</b>\n\n"
        "Отправь следующим сообщением код.\n"
        "Например: <code>HELLO100</code>\n\n"
        "Для отмены отправь: <code>отмена</code>"
    )


@router.message(F.text)
async def promocode_input(message: Message) -> None:
    user_id = message.from_user.id

    if user_id not in waiting_for_code:
        return

    raw_code = (message.text or "").strip()

    if raw_code.lower() == "отмена":
        waiting_for_code.discard(user_id)
        await message.answer("Активация промокода отменена.")
        return

    if len(raw_code) > 32:
        await message.answer("Код слишком длинный. Попробуй ещё раз.")
        return

    result = await redeem_promocode(user_id, raw_code)
    waiting_for_code.discard(user_id)

    if not result["ok"]:
        reasons = {
            "promocode_not_found": "Промокод не найден, выключен или истёк.",
            "promocode_limit_reached": "Лимит активаций промокода закончился.",
            "already_redeemed": "Ты уже использовал этот промокод.",
            "player_not_found": "Сначала отправь /start.",
        }

        await message.answer(
            f"❌ {reasons.get(result['reason'], 'Не удалось активировать код.')}"
        )
        return

    parts = []

    if int(result["reward_acorns"]) > 0:
        parts.append(f"🌰 +{result['reward_acorns']} желудей")

    if int(result["reward_xp"]) > 0:
        parts.append(f"✨ +{result['reward_xp']} XP птице")

    if int(result["reward_nests"]) > 0:
        parts.append(f"📦 +{result['reward_nests']} гнёзд")

    await message.answer(
        "✅ <b>Промокод активирован!</b>\n\n"
        + "\n".join(parts)
        + f"\n\n🌰 Баланс: <b>{result['balance_after']}</b>"
    )
