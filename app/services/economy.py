from app.db.repository import ensure_player


async def ensure_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> dict:
    return await ensure_player(
        telegram_id=user_id,
        username=username,
        first_name=first_name,
    )
