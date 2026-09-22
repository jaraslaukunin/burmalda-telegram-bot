from app.db.repository import change_balance, ensure_profile, get_profile


async def ensure_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> dict:
    return await ensure_profile(user_id, username, first_name)


async def get_balance(user_id: int) -> int:
    profile = await get_profile(user_id)

    if not profile:
        return 0

    return int(profile["acorns"])


async def add_acorns(user_id: int, amount: int) -> int:
    profile = await change_balance(user_id, amount)
    return int(profile["acorns"]) if profile else 0


async def take_acorns(user_id: int, amount: int) -> bool:
    profile = await change_balance(user_id, -amount)
    return profile is not None
