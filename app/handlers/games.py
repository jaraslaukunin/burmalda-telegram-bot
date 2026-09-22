from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.repository import play_coin, play_dice, play_slots
from app.services.game_images import (
    build_bet_card,
    build_coin_card,
    build_coin_choice_card,
    build_dice_card,
    build_games_menu_card,
    build_slots_card,
)

router = Router()

BET_VALUES = (10, 25, 50)
processing_users: set[int] = set()


def games_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎰 Бурмалда-Слот", callback_data="game:open:slots")
    builder.button(text="🎲 Жёлудь-Кубик", callback_data="game:open:dice")
    builder.button(text="🪙 Орёл или жёлудь", callback_data="game:open:coin")
    builder.adjust(1)
    return builder.as_markup()


def bets_keyboard(game_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for bet in BET_VALUES:
        builder.button(
            text=f"🌰 {bet}",
            callback_data=f"game:bet:{game_code}:{bet}",
        )

    builder.button(text="⬅️ К играм", callback_data="games:menu")
    builder.adjust(3, 1)
    return builder.as_markup()


def coin_keyboard(bet: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🦅 Орёл",
        callback_data=f"game:coin:eagle:{bet}",
    )
    builder.button(
        text="🌰 Жёлудь",
        callback_data=f"game:coin:acorn:{bet}",
    )
    builder.button(
        text="💰 Изменить ставку",
        callback_data="game:open:coin",
    )
    builder.button(
        text="🎮 К играм",
        callback_data="games:menu",
    )

    builder.adjust(2, 1, 1)
    return builder.as_markup()


def result_keyboard(game_code: str, bet: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text=f"🔁 Играть ещё за {bet} 🌰",
        callback_data=f"game:repeat:{game_code}:{bet}",
    )
    builder.button(
        text="💰 Изменить ставку",
        callback_data=f"game:open:{game_code}",
    )
    builder.button(
        text="🎮 К играм",
        callback_data="games:menu",
    )

    builder.adjust(1, 1, 1)
    return builder.as_markup()


async def send_game_screen(
    message: Message,
    image: bytes,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    await message.answer_photo(
        photo=BufferedInputFile(image, filename="burmalda-game.png"),
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def replace_game_screen(
    callback: CallbackQuery,
    image: bytes,
    caption: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    if callback.message is None:
        return

    media = InputMediaPhoto(
        media=BufferedInputFile(image, filename="burmalda-game.png"),
        caption=caption,
        parse_mode="HTML",
    )

    await callback.message.edit_media(
        media=media,
        reply_markup=keyboard,
    )


async def show_games_callback(callback: CallbackQuery) -> None:
    await replace_game_screen(
        callback,
        build_games_menu_card(),
        "🎮 <b>Игры Бурмалды</b>",
        games_menu(),
    )


async def show_bets(
    callback: CallbackQuery,
    game_code: str,
) -> None:
    await replace_game_screen(
        callback,
        build_bet_card(game_code),
        "🌰 <b>Выбери ставку</b>",
        bets_keyboard(game_code),
    )


async def show_coin_choice(
    callback: CallbackQuery,
    bet: int,
) -> None:
    await replace_game_screen(
        callback,
        build_coin_choice_card(bet),
        f"🪙 <b>Ставка: {bet} желудей</b>",
        coin_keyboard(bet),
    )


async def show_slots_result(
    callback: CallbackQuery,
    bet: int,
    result: dict,
) -> None:
    await replace_game_screen(
        callback,
        build_slots_card(
            symbols=result["symbols"],
            bet=bet,
            payout=int(result["payout"]),
            balance=int(result["balance_after"]),
            xp=int(result["xp_awarded"]),
            level=int(result["bird_level"]),
            levels_gained=int(result["levels_gained"]),
        ),
        "🎰 <b>Бурмалда-Слот</b>",
        result_keyboard("slots", bet),
    )


async def show_dice_result(
    callback: CallbackQuery,
    bet: int,
    result: dict,
) -> None:
    await replace_game_screen(
        callback,
        build_dice_card(
            roll=int(result["roll"]),
            bet=bet,
            payout=int(result["payout"]),
            balance=int(result["balance_after"]),
            xp=int(result["xp_awarded"]),
            level=int(result["bird_level"]),
            levels_gained=int(result["levels_gained"]),
        ),
        "🎲 <b>Жёлудь-Кубик</b>",
        result_keyboard("dice", bet),
    )


async def show_coin_result(
    callback: CallbackQuery,
    bet: int,
    result: dict,
) -> None:
    await replace_game_screen(
        callback,
        build_coin_card(
            choice=result["choice"],
            result=result["result"],
            bet=bet,
            payout=int(result["payout"]),
            balance=int(result["balance_after"]),
            xp=int(result["xp_awarded"]),
            level=int(result["bird_level"]),
            levels_gained=int(result["levels_gained"]),
        ),
        "🪙 <b>Орёл или жёлудь</b>",
        result_keyboard("coin", bet),
    )


async def play_game(
    callback: CallbackQuery,
    game_code: str,
    bet: int,
    choice: str | None = None,
) -> None:
    user_id = callback.from_user.id

    if user_id in processing_users:
        await callback.answer("Игра уже обрабатывается")
        return

    processing_users.add(user_id)

    try:
        if game_code == "slots":
            result = await play_slots(user_id, bet)

            if not result["ok"]:
                await callback.answer("Не хватает желудей 🌰", show_alert=True)
                return

            await show_slots_result(callback, bet, result)
            return

        if game_code == "dice":
            result = await play_dice(user_id, bet)

            if not result["ok"]:
                await callback.answer("Не хватает желудей 🌰", show_alert=True)
                return

            await show_dice_result(callback, bet, result)
            return

        if game_code == "coin" and choice is not None:
            result = await play_coin(user_id, bet, choice)

            if not result["ok"]:
                await callback.answer("Не хватает желудей 🌰", show_alert=True)
                return

            await show_coin_result(callback, bet, result)
            return

        await callback.answer("Игра недоступна", show_alert=True)

    finally:
        processing_users.discard(user_id)


@router.message(F.text == "🎮 Игры")
async def games_handler(message: Message) -> None:
    await send_game_screen(
        message,
        build_games_menu_card(),
        "🎮 <b>Игры Бурмалды</b>",
        games_menu(),
    )


@router.callback_query(F.data == "games:menu")
async def games_menu_callback(callback: CallbackQuery) -> None:
    await show_games_callback(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("game:open:"))
async def open_game_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    game_code = parts[2]

    if game_code not in {"slots", "dice", "coin"}:
        await callback.answer("Скоро появится", show_alert=True)
        return

    await show_bets(callback, game_code)
    await callback.answer()


@router.callback_query(F.data.startswith("game:bet:"))
async def bet_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer("Некорректная ставка", show_alert=True)
        return

    _, _, game_code, raw_bet = parts

    try:
        bet = int(raw_bet)
    except ValueError:
        await callback.answer("Некорректная ставка", show_alert=True)
        return

    if bet not in BET_VALUES:
        await callback.answer("Ставка недоступна", show_alert=True)
        return

    if game_code == "coin":
        await show_coin_choice(callback, bet)
    else:
        await play_game(callback, game_code, bet)

    await callback.answer()


@router.callback_query(F.data.startswith("game:repeat:"))
async def repeat_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    _, _, game_code, raw_bet = parts

    try:
        bet = int(raw_bet)
    except ValueError:
        await callback.answer("Некорректная ставка", show_alert=True)
        return

    if bet not in BET_VALUES:
        await callback.answer("Ставка недоступна", show_alert=True)
        return

    if game_code == "coin":
        await show_coin_choice(callback, bet)
    else:
        await play_game(callback, game_code, bet)

    await callback.answer()


@router.callback_query(F.data.startswith("game:coin:"))
async def coin_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer("Некорректный выбор", show_alert=True)
        return

    _, _, choice, raw_bet = parts

    try:
        bet = int(raw_bet)
    except ValueError:
        await callback.answer("Некорректная ставка", show_alert=True)
        return

    if choice not in {"eagle", "acorn"}:
        await callback.answer("Некорректный выбор", show_alert=True)
        return

    if bet not in BET_VALUES:
        await callback.answer("Ставка недоступна", show_alert=True)
        return

    await play_game(callback, "coin", bet, choice)
    await callback.answer()


@router.message(F.text == "📜 Правила")
async def rules_handler(message: Message) -> None:
    await message.answer(
        "📜 <b>Правила Бурмалды</b>\n\n"
        "• Жёлуди — виртуальная игровая валюта.\n"
        "• Никаких депозитов, реальных ставок и вывода.\n"
        "• Игры дают опыт активной птичке.\n"
        "• Собирай птичек и прокачивайся.",
    )
