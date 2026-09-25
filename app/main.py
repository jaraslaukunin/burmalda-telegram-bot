import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN, validate_config
from app.handlers import (
    admin,
    birds,
    daily,
    games,
    leaderboard,
    nests,
    profile,
    promocodes,
    start,
)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    validate_config()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Сначала конкретные команды/разделы.
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(profile.router)
    dp.include_router(daily.router)
    dp.include_router(birds.router)
    dp.include_router(nests.router)
    dp.include_router(leaderboard.router)
    dp.include_router(games.router)

    # Последним: здесь есть общий @router.message(F.text),
    # который ожидает код промокода.
    dp.include_router(promocodes.router)

    await bot.delete_webhook(drop_pending_updates=False)

    print("🍂 Бот Бурмалда запущен через long polling")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
