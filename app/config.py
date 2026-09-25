import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY",
    "",
)
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))


def validate_config() -> None:
    required = {
        "BOT_TOKEN": BOT_TOKEN,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
        "ADMIN_TELEGRAM_ID": str(ADMIN_TELEGRAM_ID),
    }

    missing = [name for name, value in required.items() if not value or value == "0"]

    if missing:
        raise RuntimeError(
            "Заполни .env. Не найдены: " + ", ".join(missing)
        )
