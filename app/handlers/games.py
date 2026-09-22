import random

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.db.repository import add_game_history
from app.keyboards.games import dice_keyboard, games_menu, slots_keyboard
from app.services.economy import add_acorns, get_balance, take_acorns

router = Router()

SLOT_BET = 10
DICE_BET = 10


@router.message(F.text == "🎮 Игры")
async def games_handler(message: Message) -> None:
    balance = await get_balance(message.from_user.id)

    await message.answer(
        "🎮 <b>Игры Бурмалды</b>\n\n"
        f"🌰 Баланс: <b>{balance}</b>\n\n"
        "Выбирай игру:",
        reply_markup=games_menu(),
    )


@router.callback_query(F.data == "games:menu")
async def games_menu_callback(callback: CallbackQuery) -> None:
    balance = await get_balance(callback.from_user.id)

    await callback.message.edit_text(
        "🎮 <b>Игры Бурмалды</b>\n\n"
        f"🌰 Баланс: <b>{balance}</b>\n\n"
        "Выбирай игру:",
        reply_markup=games_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "game:open:slots")
async def open_slots(callback: CallbackQuery) -> None:
    balance = await get_balance(callback.from_user.id)

    await callback.message.edit_text(
        "🎰 <b>Бурмалда-Слот</b>\n\n"
        f"Ставка: {SLOT_BET} 🌰\n"
        "Три одинаковых символа — джекпот.\n"
        "Два одинаковых — маленький выигрыш.\n\n"
        f"Баланс: <b>{balance}</b> 🌰",
        reply_markup=slots_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "game:slots:spin")
async def slots_spin(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    if not await take_acorns(user_id, SLOT_BET):
        await callback.answer("Не хватает жёлудей 🌰", show_alert=True)
        return

    symbols = ["🍂", "🐦", "🌰", "🪵", "🔥"]
    result = [random.choice(symbols) for _ in range(3)]

    payout = 0
    title = "🥀 Птички унесли ставку"

    if len(set(result)) == 1:
        payout = 80
        title = "🔥 ДЖЕКПОТ БУРМАЛДЫ!"
    elif len(set(result)) == 2:
        payout = 20
        title = "✨ Есть пара!"

    if payout:
        await add_acorns(user_id, payout)

    await add_game_history(
        telegram_id=user_id,
        game_type="slots",
        bet=SLOT_BET,
        payout=payout,
        result={"symbols": result},
    )

    balance = await get_balance(user_id)

    await callback.message.edit_text(
        f"🎰 {' | '.join(result)}\n\n"
        f"<b>{title}</b>\n"
        f"Выигрыш: {payout} 🌰\n"
        f"Баланс: <b>{balance}</b> 🌰",
        reply_markup=slots_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "game:open:dice")
async def open_dice(callback: CallbackQuery) -> None:
    balance = await get_balance(callback.from_user.id)

    await callback.message.edit_text(
        "🎲 <b>Кубик Бурмалды</b>\n\n"
        f"Ставка: {DICE_BET} 🌰\n"
        "5 или 6 — выигрываешь 25 желудей.\n"
        "Иначе ставка сгорает.\n\n"
        f"Баланс: <b>{balance}</b> 🌰",
        reply_markup=dice_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "game:dice:roll")
async def dice_roll(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    if not await take_acorns(user_id, DICE_BET):
        await callback.answer("Не хватает жёлудей 🌰", show_alert=True)
        return

    roll = random.randint(1, 6)
    payout = 25 if roll >= 5 else 0

    if payout:
        await add_acorns(user_id, payout)

    await add_game_history(
        telegram_id=user_id,
        game_type="dice",
        bet=DICE_BET,
        payout=payout,
        result={"roll": roll},
    )

    balance = await get_balance(user_id)
    verdict = "🔥 Победа!" if payout else "🥀 Не повезло."

    await callback.message.edit_text(
        f"🎲 Выпало: <b>{roll}</b>\n\n"
        f"{verdict}\n"
        f"Выигрыш: {payout} 🌰\n"
        f"Баланс: <b>{balance}</b> 🌰",
        reply_markup=dice_keyboard(),
    )
    await callback.answer()


@router.message(F.text == "📜 Правила")
async def rules_handler(message: Message) -> None:
    await message.answer(
        "📜 <b>Правила</b>\n\n"
        "• Жёлуди — исключительно виртуальная валюта.\n"
        "• Нет пополнений, депозитов, реальных ставок или вывода.\n"
        "• Результаты игр сохраняются в истории.\n"
        "• Не нажимай кнопки слишком быстро: антиспам добавим следующим шагом.",
    )
