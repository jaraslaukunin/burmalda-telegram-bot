from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1350

ROOT_DIR = Path(__file__).resolve().parents[2]
ICONS_DIR = ROOT_DIR / "assets" / "slot" / "icons"

FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"

SYMBOL_TO_ICON = {
    "🍂": "leaf.png",
    "🐦": "bird.png",
    "🌰": "acorn.png",
    "🪵": "log.png",
    "🔥": "fire.png",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH

    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    draw.text(
        (x, y),
        text,
        font=text_font,
        fill=fill,
        anchor="mm",
    )


def rounded_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str,
    radius: int = 36,
    width: int = 4,
) -> None:
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def gradient_background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#071A18")
    pixels = image.load()

    for y in range(HEIGHT):
        ratio = y / HEIGHT

        for x in range(WIDTH):
            center_glow = max(
                0,
                1 - abs(x - WIDTH * 0.5) / (WIDTH * 0.72),
            )

            pixels[x, y] = (
                min(7 + int(ratio * 12) + int(center_glow * 10), 255),
                min(26 + int(ratio * 36) + int(center_glow * 16), 255),
                min(24 + int(ratio * 20) + int(center_glow * 7), 255),
            )

    return image.convert("RGBA")


def paste_symbol(
    canvas: Image.Image,
    symbol: str,
    center_x: int,
    center_y: int,
    max_size: int = 155,
) -> None:
    icon_name = SYMBOL_TO_ICON.get(symbol)

    if icon_name is None:
        return

    icon_path = ICONS_DIR / icon_name

    if not icon_path.exists():
        raise FileNotFoundError(
            f"Не найдена иконка {icon_path}. "
            "Сначала выполни команду curl для Twemoji."
        )

    with Image.open(icon_path) as source:
        icon = source.convert("RGBA")

    icon.thumbnail(
        (max_size, max_size),
        Image.Resampling.LANCZOS,
    )

    x = center_x - icon.width // 2
    y = center_y - icon.height // 2

    canvas.alpha_composite(icon, (x, y))


def slot_verdict(payout: int, bet: int) -> tuple[str, str]:
    if payout == bet * 8:
        return "JACKPOT!", "#FFD65A"

    if payout > 0:
        return "MATCH!", "#86F7C0"

    return "NO LUCK", "#E4A5A5"


def build_slots_image(
    symbols: list[str],
    bet: int,
    payout: int,
    balance: int,
    xp_awarded: int,
    bird_level: int,
    levels_gained: int = 0,
) -> bytes:
    image = gradient_background()
    draw = ImageDraw.Draw(image)

    title_font = font(58, bold=True)
    subtitle_font = font(28, bold=True)
    body_font = font(32, bold=False)
    body_bold = font(34, bold=True)
    tiny_font = font(23, bold=False)

    for x, y, radius, color in [
        (110, 170, 16, "#D5A62A"),
        (915, 125, 11, "#5DC997"),
        (970, 530, 20, "#D5A62A"),
        (85, 870, 14, "#5DC997"),
        (180, 1190, 18, "#D5A62A"),
        (900, 1160, 12, "#5DC997"),
    ]:
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color,
        )

    centered(draw, "BURMALDA", WIDTH // 2, 88, title_font, "#F9D66A")
    centered(
        draw,
        "ACORN WORLD • BIRDS • LEVELS",
        WIDTH // 2,
        145,
        tiny_font,
        "#A8D7BF",
    )

    rounded_card(
        draw,
        (55, 205, 1025, 760),
        fill="#102C28",
        outline="#CFAE49",
        radius=54,
        width=7,
    )

    centered(draw, "BURMALDA SLOT", WIDTH // 2, 270, subtitle_font, "#F5E3A6")

    reel_width = 255
    reel_height = 280
    gap = 35
    start_x = (WIDTH - (reel_width * 3 + gap * 2)) // 2
    reel_y = 350

    for index, symbol in enumerate(symbols[:3]):
        x1 = start_x + index * (reel_width + gap)
        x2 = x1 + reel_width

        rounded_card(
            draw,
            (x1, reel_y, x2, reel_y + reel_height),
            fill="#F2E9C9",
            outline="#E1B74A",
            radius=30,
            width=6,
        )

        draw.ellipse(
            (x1 + 24, reel_y + 22, x2 - 24, reel_y + reel_height - 22),
            fill="#E2D7AE",
        )

        paste_symbol(
            image,
            symbol,
            (x1 + x2) // 2,
            reel_y + reel_height // 2,
        )

    verdict, verdict_color = slot_verdict(payout, bet)

    rounded_card(
        draw,
        (80, 805, 1000, 940),
        fill="#0B211E",
        outline=verdict_color,
        radius=34,
        width=4,
    )

    centered(draw, verdict, WIDTH // 2, 855, subtitle_font, verdict_color)
    centered(
        draw,
        f"BET {bet}  •  PAYOUT {payout} ACORNS",
        WIDTH // 2,
        907,
        body_font,
        "#EAE8D6",
    )

    rounded_card(
        draw,
        (80, 985, 1000, 1200),
        fill="#0C2924",
        outline="#2D745C",
        radius=34,
        width=3,
    )

    centered(
        draw,
        f"BALANCE: {balance} ACORNS",
        WIDTH // 2,
        1040,
        body_bold,
        "#F9D66A",
    )
    centered(
        draw,
        f"BIRD XP +{xp_awarded}  •  BIRD LEVEL {bird_level}",
        WIDTH // 2,
        1102,
        body_font,
        "#BDEBCC",
    )

    if levels_gained > 0:
        centered(
            draw,
            f"LEVEL UP +{levels_gained}!",
            WIDTH // 2,
            1160,
            subtitle_font,
            "#FFD65A",
        )

    centered(
        draw,
        "VIRTUAL ACORNS • NO REAL MONEY",
        WIDTH // 2,
        1285,
        tiny_font,
        "#78A998",
    )

    buffer = BytesIO()
    image.convert("RGB").save(
        buffer,
        format="PNG",
        optimize=True,
    )

    return buffer.getvalue()
