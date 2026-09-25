from typing import Any

from app.db.supabase import supabase


def _first(response) -> dict[str, Any]:
    if not response.data:
        raise RuntimeError("Supabase RPC вернул пустой ответ")

    return response.data[0]


async def ensure_player(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    language: str = "ru",
) -> dict[str, Any]:
    response = supabase.rpc(
        "ensure_player",
        {
            "p_telegram_id": telegram_id,
            "p_username": username,
            "p_first_name": first_name,
            "p_language": language,
        },
    ).execute()
    return _first(response)


async def claim_daily(telegram_id: int) -> dict[str, Any]:
    response = supabase.rpc(
        "claim_daily",
        {"p_telegram_id": telegram_id},
    ).execute()
    return _first(response)


async def play_slots(
    telegram_id: int,
    bet: int,
) -> dict[str, Any]:
    response = supabase.rpc(
        "play_slots",
        {
            "p_telegram_id": telegram_id,
            "p_bet": bet,
        },
    ).execute()
    return _first(response)


async def play_dice(
    telegram_id: int,
    bet: int,
) -> dict[str, Any]:
    response = supabase.rpc(
        "play_dice",
        {
            "p_telegram_id": telegram_id,
            "p_bet": bet,
        },
    ).execute()
    return _first(response)


async def play_coin(
    telegram_id: int,
    bet: int,
    choice: str,
) -> dict[str, Any]:
    response = supabase.rpc(
        "play_coin",
        {
            "p_telegram_id": telegram_id,
            "p_bet": bet,
            "p_choice": choice,
        },
    ).execute()
    return _first(response)


async def get_leaderboard(
    mode: str = "acorns",
    limit: int = 10,
) -> list[dict[str, Any]]:
    response = supabase.rpc(
        "get_leaderboard",
        {
            "p_mode": mode,
            "p_limit": limit,
        },
    ).execute()

    return response.data or []


async def get_player_profile(
    telegram_id: int,
) -> dict[str, Any] | None:
    response = (
        supabase.table("profiles")
        .select(
            "telegram_id, username, first_name, acorns, games_played, "
            "joined_at, language, user_birds!inner("
            "id, level, xp, total_xp, is_active, "
            "bird_definitions!inner("
            "code, title_ru, title_en, emoji, rarity, "
            "effect_type, effect_value"
            ")"
            ")"
        )
        .eq("telegram_id", telegram_id)
        .eq("user_birds.is_active", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


async def get_player_birds(
    telegram_id: int,
    language: str = "ru",
) -> list[dict[str, Any]]:
    response = supabase.rpc(
        "get_player_birds",
        {
            "p_telegram_id": telegram_id,
            "p_language": language,
        },
    ).execute()
    return response.data or []


async def set_active_bird(
    telegram_id: int,
    user_bird_id: int,
) -> dict[str, Any]:
    response = supabase.rpc(
        "set_active_bird",
        {
            "p_telegram_id": telegram_id,
            "p_user_bird_id": user_bird_id,
        },
    ).execute()
    return _first(response)


async def admin_get_stats() -> dict[str, Any]:
    response = supabase.rpc("admin_get_stats").execute()
    return _first(response)


async def admin_adjust_acorns(
    target_telegram_id: int,
    amount: int,
    admin_telegram_id: int,
    reason: str | None = None,
) -> dict[str, Any]:
    response = supabase.rpc(
        "admin_adjust_acorns",
        {
            "p_target_telegram_id": target_telegram_id,
            "p_amount": amount,
            "p_admin_telegram_id": admin_telegram_id,
            "p_reason": reason,
        },
    ).execute()
    return _first(response)


async def admin_adjust_bird_xp(
    target_telegram_id: int,
    amount: int,
    admin_telegram_id: int,
    reason: str | None = None,
) -> dict[str, Any]:
    response = supabase.rpc(
        "admin_adjust_bird_xp",
        {
            "p_target_telegram_id": target_telegram_id,
            "p_amount": amount,
            "p_admin_telegram_id": admin_telegram_id,
            "p_reason": reason,
        },
    ).execute()
    return _first(response)


async def admin_get_player(
    admin_telegram_id: int,
    target_telegram_id: int,
) -> dict[str, Any] | None:
    response = supabase.rpc(
        "admin_get_player",
        {
            "p_admin_telegram_id": admin_telegram_id,
            "p_target_telegram_id": target_telegram_id,
        },
    ).execute()

    return response.data[0] if response.data else None


async def admin_grant_nests(
    admin_telegram_id: int,
    target_telegram_id: int,
    amount: int,
    reason: str | None = None,
) -> dict[str, Any]:
    response = supabase.rpc(
        "admin_grant_nests",
        {
            "p_admin_telegram_id": admin_telegram_id,
            "p_target_telegram_id": target_telegram_id,
            "p_amount": amount,
            "p_reason": reason,
        },
    ).execute()
    return _first(response)


async def admin_grant_bird(
    admin_telegram_id: int,
    target_telegram_id: int,
    bird_code: str,
    reason: str | None = None,
) -> dict[str, Any]:
    response = supabase.rpc(
        "admin_grant_bird",
        {
            "p_admin_telegram_id": admin_telegram_id,
            "p_target_telegram_id": target_telegram_id,
            "p_bird_code": bird_code,
            "p_reason": reason,
        },
    ).execute()
    return _first(response)


async def admin_create_promocode(
    admin_telegram_id: int,
    code: str,
    reward_acorns: int = 0,
    reward_xp: int = 0,
    reward_nests: int = 0,
    max_uses: int | None = None,
) -> dict[str, Any]:
    response = supabase.rpc(
        "admin_create_promocode",
        {
            "p_admin_telegram_id": admin_telegram_id,
            "p_code": code,
            "p_reward_acorns": reward_acorns,
            "p_reward_xp": reward_xp,
            "p_reward_nests": reward_nests,
            "p_max_uses": max_uses,
            "p_expires_at": None,
        },
    ).execute()
    return _first(response)


async def get_nests_count(telegram_id: int) -> int:
    response = (
        supabase.table("user_nests")
        .select("id", count="exact")
        .eq("telegram_id", telegram_id)
        .eq("is_opened", False)
        .execute()
    )
    return int(response.count or 0)


async def buy_nest(telegram_id: int) -> dict[str, Any]:
    response = supabase.rpc(
        "buy_nest",
        {"p_telegram_id": telegram_id},
    ).execute()
    return _first(response)


async def open_nest(telegram_id: int) -> dict[str, Any]:
    response = supabase.rpc(
        "open_nest",
        {"p_telegram_id": telegram_id},
    ).execute()
    return _first(response)


async def redeem_promocode(
    telegram_id: int,
    code: str,
) -> dict[str, Any]:
    response = supabase.rpc(
        "redeem_promocode",
        {
            "p_telegram_id": telegram_id,
            "p_code": code,
        },
    ).execute()
    return _first(response)
