from supabase import Client, create_client

from app.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "В .env должны быть SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY"
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    )


supabase = get_supabase()
