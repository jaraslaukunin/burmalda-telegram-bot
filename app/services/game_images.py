from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1080

ROOT_DIR = Path(__file__).resolve().parents[2]
ICONS_DIR = ROOT_DIR / "assets" / "slot" / "icons"

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"

SLOT_ICONS = {
    "🍂": "leaf.png",
    "🐦": "bird.png",
    "🌰": "acorn.png",
    "🪵": "log.png",
    "🔥": "fire.png",
}


def get_font(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def text_center(draw, xy, text, font, fill):
    draw.text(xy, text, font=font, fill=fill, anchor="mm")


def card(draw, box, fill, outline="#2F8366", radius=28, width=3):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#071C18")
    draw = ImageDraw.Draw(image)

    for y in range(0, HEIGHT, 8):
        t = y / HEIGHT
        color = (
            int(6 + t * 8),
            int(29 + t * 28),
            int(24 + t * 13),
        )
        draw.rectangle((0, y, WIDTH, y + 8), fill=color)

    for x, y, radius, color in [
        (110, 110, 110, "#0E3B2F"),
        (950, 180, 150, "#123F32"),
        (170, 910, 180, "#10392F"),
        (930, 900, 100, "#1A4E3D"),
    ]:
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=color,
        )

    return image


def header(draw, title: str, subtitle: str):
    title_font = get_font(48, bold=True)
    subtitle_font = get_font(22)

    text_center(draw, (WIDTH // 2, 62), title, title_font, "#F7D46C")
    text_center(draw, (WIDTH // 2, 106), subtitle, subtitle_font, "#A8DDBE")

    draw.line((70, 136, WIDTH - 70, 136), fill="#317D62", width=3)


def footer(draw, balance: int, xp: int, level: int):
    label_font = get_font(25, bold=True)
    value_font = get_font(32, bold=True)

    card(draw, (65, 910, 1015, 1020), "#0A2821", "#286E58", radius=26)

    text_center(draw, (245, 947), "ЖЁЛУДИ", label_font, "#99CDB2")
    text_center(draw, (245, 985), str(balance), value_font, "#F7D46C")

    text_center(draw, (540, 947), "ОПЫТ ПТИЧКИ", label_font, "#99CDB2")
    text_center(draw, (540, 985), f"+{xp}", value_font, "#D7F8E6")

    text_center(draw, (835, 947), "УРОВЕНЬ", label_font, "#99CDB2")
    text_center(draw, (835, 985), str(level), value_font, "#D7F8E6")


def paste_icon(
    image: Image.Image,
    emoji: str,
    cx: int,
    cy: int,
    size: int,
):
    name = SLOT_ICONS.get(emoji)
    if not name:
        return

    path = ICONS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Нет ассета: {path}")

    with Image.open(path) as source:
        icon = source.convert("RGBA")

    icon.thumbnail((size, size), Image.Resampling.LANCZOS)

    image.paste(
        icon,
        (cx - icon.width // 2, cy - icon.height // 2),
        icon,
    )


def slot_result_text(payout: int, bet: int) -> tuple[str, str]:
    if payout == bet * 8:
        return "ДЖЕКПОТ!", "#FFD45E"

    if payout > 0:
        return "ЕСТЬ КОМБИНАЦИЯ!", "#8DF1BC"

    return "НЕ ПОВЕЗЛО", "#F2A2A2"


def build_slots_card(
    symbols: list[str],
    bet: int,
    payout: int,
    balance: int,
    xp: int,
    level: int,
    levels_gained: int = 0,
) -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    header(draw, "БУРМАЛДА • СЛОТ", f"СТАВКА: {bet} ЖЁЛУДЕЙ")

    card(draw, (55, 170, 1025, 625), "#102F27", "#D2B04A", radius=42, width=6)

    reel_w = 250
    reel_h = 260
    gap = 35
    left = (WIDTH - (reel_w * 3 + gap * 2)) // 2
    top = 260

    for i, symbol in enumerate(symbols[:3]):
        x1 = left + i * (reel_w + gap)
        x2 = x1 + reel_w

        card(draw, (x1, top, x2, top + reel_h), "#EFE4C5", "#E0B94B", radius=28, width=5)
        draw.ellipse(
            (x1 + 18, top + 18, x2 - 18, top + reel_h - 18),
            fill="#DDD0A9",
        )

        paste_icon(
            image,
            symbol,
            (x1 + x2) // 2,
            top + reel_h // 2,
            150,
        )

    result_text, result_color = slot_result_text(payout, bet)

    card(draw, (85, 670, 995, 850), "#0A2720", result_color, radius=34, width=4)

    text_center(draw, (WIDTH // 2, 724), result_text, get_font(34, True), result_color)
    text_center(
        draw,
        (WIDTH // 2, 775),
        f"ВЫИГРЫШ: {payout} ЖЁЛУДЕЙ",
        get_font(29, True),
        "#F5F1DF",
    )

    if levels_gained:
        text_center(
            draw,
            (WIDTH // 2, 821),
            f"ПТИЧКА ПОЛУЧИЛА +{levels_gained} УРОВЕНЬ!",
            get_font(22, True),
            "#F7D46C",
        )

    footer(draw, balance, xp, level)

    return save(image)


def draw_dice(draw, x: int, y: int, size: int, value: int):
    card(draw, (x, y, x + size, y + size), "#EFE4C5", "#E0B94B", radius=45, width=7)

    points = {
        1: [(0.5, 0.5)],
        2: [(0.28, 0.28), (0.72, 0.72)],
        3: [(0.28, 0.28), (0.5, 0.5), (0.72, 0.72)],
        4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
        5: [(0.28, 0.28), (0.72, 0.28), (0.5, 0.5), (0.28, 0.72), (0.72, 0.72)],
        6: [(0.28, 0.23), (0.72, 0.23), (0.28, 0.5), (0.72, 0.5), (0.28, 0.77), (0.72, 0.77)],
    }

    radius = 18
    for px, py in points[value]:
        cx = x + int(size * px)
        cy = y + int(size * py)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill="#13382E",
        )


def build_dice_card(
    roll: int,
    bet: int,
    payout: int,
    balance: int,
    xp: int,
    level: int,
    levels_gained: int = 0,
) -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    header(draw, "ЖЁЛУДЬ-КУБИК", f"СТАВКА: {bet} ЖЁЛУДЕЙ")

    draw_dice(draw, 300, 210, 480, roll)

    win = payout > 0
    result = "ПОБЕДА!" if win else "НЕ ПОВЕЗЛО"
    color = "#8DF1BC" if win else "#F2A2A2"

    card(draw, (85, 720, 995, 850), "#0A2720", color, radius=34, width=4)

    text_center(draw, (WIDTH // 2, 764), result, get_font(34, True), color)
    text_center(
        draw,
        (WIDTH // 2, 812),
        f"ВЫПАЛО: {roll}  •  ВЫИГРЫШ: {payout}",
        get_font(27, True),
        "#F5F1DF",
    )

    footer(draw, balance, xp, level)
    return save(image)


def draw_coin(draw, cx: int, cy: int, radius: int, is_eagle: bool):
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill="#E1B94A",
        outline="#7D5914",
        width=10,
    )
    draw.ellipse(
        (cx - radius + 28, cy - radius + 28, cx + radius - 28, cy + radius - 28),
        outline="#FFF0A7",
        width=6,
    )

    if is_eagle:
        draw.polygon(
            [
                (cx - 75, cy + 40),
                (cx - 5, cy - 92),
                (cx + 80, cy + 40),
                (cx + 14, cy + 10),
                (cx, cy + 86),
                (cx - 14, cy + 10),
            ],
            fill="#173B30",
        )
    else:
        draw.ellipse(
            (cx - 65, cy - 20, cx + 65, cy + 120),
            fill="#9B592B",
            outline="#5A2C16",
            width=6,
        )
        draw.pieslice(
            (cx - 75, cy - 72, cx + 75, cy + 25),
            start=180,
            end=360,
            fill="#5E8E43",
            outline="#365625",
            width=6,
        )


def build_coin_card(
    choice: str,
    result: str,
    bet: int,
    payout: int,
    balance: int,
    xp: int,
    level: int,
    levels_gained: int = 0,
) -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    header(draw, "ОРЁЛ ИЛИ ЖЁЛУДЬ", f"СТАВКА: {bet} ЖЁЛУДЕЙ")

    is_eagle = result == "eagle"
    draw_coin(draw, WIDTH // 2, 430, 205, is_eagle)

    result_label = "ОРЁЛ" if is_eagle else "ЖЁЛУДЬ"
    choice_label = "ОРЁЛ" if choice == "eagle" else "ЖЁЛУДЬ"
    win = payout > 0
    color = "#8DF1BC" if win else "#F2A2A2"

    card(draw, (85, 690, 995, 850), "#0A2720", color, radius=34, width=4)

    text_center(
        draw,
        (WIDTH // 2, 732),
        "УГАДАЛ!" if win else "НЕ УГАДАЛ",
        get_font(34, True),
        color,
    )
    text_center(
        draw,
        (WIDTH // 2, 778),
        f"ТЫ: {choice_label}  •  ВЫПАЛО: {result_label}",
        get_font(24, True),
        "#F5F1DF",
    )
    text_center(
        draw,
        (WIDTH // 2, 820),
        f"ВЫИГРЫШ: {payout} ЖЁЛУДЕЙ",
        get_font(25, True),
        "#F7D46C",
    )

    footer(draw, balance, xp, level)
    return save(image)


def save(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build_games_menu_card() -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    header(draw, "ИГРЫ БУРМАЛДЫ", "ВЫБЕРИ РЕЖИМ И ПРОКАЧИВАЙ ПТИЧКУ")

    font_title = get_font(32, bold=True)
    font_body = get_font(23)
    font_small = get_font(20)

    items = [
        ("СЛОТ", "ТРИ СИМВОЛА • ПАРА X2 • ТРИ ОДИНАКОВЫХ X8"),
        ("КУБИК", "ВЫПАДАЕТ 5 ИЛИ 6 — ВЫИГРЫШ X2.5"),
        ("ОРЁЛ ИЛИ ЖЁЛУДЬ", "УГАДАЙ СТОРОНУ — ВЫИГРЫШ X2"),
    ]

    top = 205

    for index, (title, description) in enumerate(items):
        y = top + index * 190

        card(
            draw,
            (80, y, 1000, y + 150),
            "#102F27",
            "#3C9A78",
            radius=30,
            width=4,
        )

        draw.ellipse(
            (112, y + 39, 182, y + 109),
            fill="#D6B449",
            outline="#F5E0A1",
            width=3,
        )

        text_center(
            draw,
            (535, y + 62),
            title,
            font_title,
            "#F5DD87",
        )
        text_center(
            draw,
            (535, y + 105),
            description,
            font_small,
            "#B7DDC8",
        )

    card(draw, (80, 825, 1000, 910), "#0A2821", "#286E58", radius=25, width=3)
    text_center(
        draw,
        (WIDTH // 2, 866),
        "КАЖДАЯ ИГРА ДАЁТ ОПЫТ АКТИВНОЙ ПТИЧКЕ",
        font_body,
        "#D9F3E4",
    )

    text_center(
        draw,
        (WIDTH // 2, 1000),
        "ВАЛЮТА ВИРТУАЛЬНАЯ • БЕЗ РЕАЛЬНЫХ СТАВОК",
        get_font(18),
        "#78A998",
    )

    return save(image)


def build_bet_card(game_code: str) -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    titles = {
        "slots": ("БУРМАЛДА-СЛОТ", "ПАРА X2 • ТРИ ОДИНАКОВЫХ X8"),
        "dice": ("ЖЁЛУДЬ-КУБИК", "5 ИЛИ 6 — ВЫИГРЫШ X2.5"),
        "coin": ("ОРЁЛ ИЛИ ЖЁЛУДЬ", "УГАДАЙ СТОРОНУ — ВЫИГРЫШ X2"),
    }

    title, subtitle = titles.get(game_code, ("ИГРА", "ВЫБЕРИ СТАВКУ"))

    header(draw, title, subtitle)

    card(draw, (90, 235, 990, 730), "#102F27", "#D2B04A", radius=40, width=5)

    text_center(
        draw,
        (WIDTH // 2, 320),
        "ВЫБЕРИ СТАВКУ",
        get_font(42, bold=True),
        "#F7D46C",
    )

    text_center(
        draw,
        (WIDTH // 2, 395),
        "ЧЕМ ВЫШЕ СТАВКА — ТЕМ БОЛЬШЕ ОПЫТА ПТИЧКЕ",
        get_font(22),
        "#B7DDC8",
    )

    for index, value in enumerate((10, 25, 50)):
        x = 240 + index * 300

        card(
            draw,
            (x - 105, 475, x + 105, 635),
            "#0A2821",
            "#3C9A78",
            radius=30,
            width=4,
        )

        text_center(
            draw,
            (x, 530),
            str(value),
            get_font(44, bold=True),
            "#F7D46C",
        )
        text_center(
            draw,
            (x, 588),
            "ЖЁЛУДЕЙ",
            get_font(18, bold=True),
            "#B7DDC8",
        )

    text_center(
        draw,
        (WIDTH // 2, 825),
        "МИНИМАЛЬНАЯ СТАВКА: 10 ЖЁЛУДЕЙ",
        get_font(24, bold=True),
        "#D9F3E4",
    )

    text_center(
        draw,
        (WIDTH // 2, 1000),
        "ВАЛЮТА ВИРТУАЛЬНАЯ • БЕЗ РЕАЛЬНЫХ СТАВОК",
        get_font(18),
        "#78A998",
    )

    return save(image)


def build_coin_choice_card(bet: int) -> bytes:
    image = background()
    draw = ImageDraw.Draw(image)

    header(draw, "ОРЁЛ ИЛИ ЖЁЛУДЬ", f"СТАВКА: {bet} ЖЁЛУДЕЙ")

    card(draw, (90, 215, 990, 770), "#102F27", "#D2B04A", radius=40, width=5)

    text_center(
        draw,
        (WIDTH // 2, 292),
        "ВЫБЕРИ СТОРОНУ",
        get_font(40, bold=True),
        "#F7D46C",
    )

    draw_coin(draw, 315, 510, 160, True)
    draw_coin(draw, 765, 510, 160, False)

    text_center(
        draw,
        (315, 710),
        "ОРЁЛ",
        get_font(30, bold=True),
        "#D9F3E4",
    )

    text_center(
        draw,
        (765, 710),
        "ЖЁЛУДЬ",
        get_font(30, bold=True),
        "#D9F3E4",
    )

    text_center(
        draw,
        (WIDTH // 2, 840),
        "УГАДАЙ СТОРОНУ И ПОЛУЧИ X2",
        get_font(25, bold=True),
        "#B7DDC8",
    )

    text_center(
        draw,
        (WIDTH // 2, 1000),
        "ВАЛЮТА ВИРТУАЛЬНАЯ • БЕЗ РЕАЛЬНЫХ СТАВОК",
        get_font(18),
        "#78A998",
    )

    return save(image)
