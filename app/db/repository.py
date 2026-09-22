from datetime import datetime, timezone
from typing import Any

from app.db.supabase import supabase


def _one(response) -> dict[str, Any] | None:
    data = response.data
    return data[0] if data else None


async def ensure_profile(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> dict[str, Any]:
    existing = _one(
        supabase.table("profiles")
        .select("*")
        .eq("telegram_id", telegram_id)
        .limit(1)
        .execute()
    )

    if existing:
        return existing

    response = (
        supabase.table("profiles")
        .insert(
            {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name or "Игрок",
                "acorns": 100,
            }
        )
        .execute()
    )

    return _one(response) or {}


async def get_profile(telegram_id: int) -> dict[str, Any] | None:
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("telegram_id", telegram_id)
        .limit(1)
        .execute()
    )
    return _one(response)


async def change_balance(
    telegram_id: int,
    delta: int,
) -> dict[str, Any] | None:
    profile = await get_profile(telegram_id)

    if not profile:
        return None

    new_balance = int(profile["acorns"]) + delta

    if new_balance < 0:
        return None

    response = (
        supabase.table("profiles")
        .update(
            {
                "acorns": new_balance,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("telegram_id", telegram_id)
        .execute()
    )

    return _one(response)


async def add_game_history(
    telegram_id: int,
    game_type: str,
    bet: int,
    payout: int,
    result: dict[str, Any],
) -> None:
    (
        supabase.table("game_history")
        .insert(
            {
                "telegram_id": telegram_id,
                "game_type": game_type,
                "bet": bet,
                "payout": payout,
                "result": result,
            }
        )
        .execute()
    )
