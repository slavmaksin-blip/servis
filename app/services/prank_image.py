from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Tx:
    title: str
    subtitle: str
    date_text: str
    amount_text: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MERCHANTS = [
    ("Migros", "Supermarkt"),
    ("Coop", "Lebensmittel"),
    ("SBB", "Fahrticket"),
    ("Swisscom", "Mobilfunk"),
    ("Denner", "Einkauf"),
    ("Post", "Paket / Post"),
    ("Zalando", "Online-Shop"),
    ("Galaxus", "Elektronik"),
    ("Netflix", "Streaming"),
    ("Spotify", "Musik"),
    ("Apple Store", "App Store"),
    ("McDonalds", "Restaurant"),
    ("Starbucks", "Café"),
    ("Ikea", "Möbel"),
    ("H&M", "Bekleidung"),
]


def _chf(value: float) -> str:
    """Format as -65.50 (CHF style: period thousands, comma decimal)."""
    return f"-{value:,.2f}".replace(",", "\u2019")  # Swiss apostrophe thousands


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a system font; fall back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "arial.ttf",
        "Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _load_bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arialbd.ttf",
        "Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return _load_font(size)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_prank_bank_screen(
    service_name: str,
    amount_chf: float,
    now: datetime | None = None,
) -> bytes:
    """
    Generate a light iOS-style transaction history image.
    Contains a visible 'РОЗЫГРЫШ / FAKE' watermark.
    Does NOT copy any real bank interface 1-to-1.
    """
    if now is None:
        now = datetime.now()

    # -----------------------------------------------------------------------
    # Canvas — iPhone-proportioned but moderate resolution
    # -----------------------------------------------------------------------
    W, H = 390, 844  # logical px (iPhone 12 mini logical)
    SCALE = 3         # render at 3x for crispness
    RW, RH = W * SCALE, H * SCALE

    img = Image.new("RGB", (RW, RH), (242, 242, 247))
    d = ImageDraw.Draw(img)

    # -----------------------------------------------------------------------
    # Fonts (scaled)
    # -----------------------------------------------------------------------
    S = SCALE
    f_status   = _load_font(11 * S)
    f_title    = _load_bold_font(18 * S)
    f_section  = _load_bold_font(12 * S)
    f_tx_name  = _load_bold_font(14 * S)
    f_tx_sub   = _load_font(12 * S)
    f_tx_amt   = _load_bold_font(14 * S)
    f_wm_big   = _load_bold_font(28 * S)
    f_wm_small = _load_bold_font(13 * S)

    # -----------------------------------------------------------------------
    # Status bar
    # -----------------------------------------------------------------------
    sb_h = 44 * S
    # Background already light, draw time left and icons right
    time_str = now.strftime("%H:%M")
    d.text((15 * S, 14 * S), time_str, fill=(0, 0, 0), font=f_status)
    # Battery / signal placeholder (simple shapes)
    bx = RW - 15 * S
    # battery
    batt_w, batt_h = 22 * S, 11 * S
    d.rounded_rectangle(
        (bx - batt_w - 2, 16 * S, bx - 2, 16 * S + batt_h),
        radius=2 * S, outline=(0, 0, 0), width=S,
    )
    d.rectangle(
        (bx - batt_w, 18 * S, bx - batt_w + 14 * S, 16 * S + batt_h - 2 * S - S),
        fill=(0, 0, 0),
    )
    d.rectangle((bx - 1, 19 * S, bx, 23 * S), fill=(0, 0, 0))
    # wifi circles
    wx = bx - batt_w - 8 * S
    for r, a in [(5 * S, 130), (9 * S, 130)]:
        d.arc((wx - r, 20 * S - r // 2, wx + r, 20 * S + r // 2), start=-130, end=-50,
              fill=(0, 0, 0), width=S)
    d.ellipse((wx - S, 22 * S - S, wx + S, 22 * S + S), fill=(0, 0, 0))

    # -----------------------------------------------------------------------
    # Navigation bar — "Транзакции"
    # -----------------------------------------------------------------------
    nav_top = sb_h
    nav_h = 44 * S
    d.text(
        (RW // 2 - _text_w(d, "Транзакции", f_title) // 2, nav_top + 10 * S),
        "Транзакции", fill=(0, 0, 0), font=f_title,
    )
    # Back chevron placeholder
    d.text((15 * S, nav_top + 10 * S), "‹", fill=(0, 122, 255), font=f_title)

    # separator
    sep_y = nav_top + nav_h
    d.line((0, sep_y, RW, sep_y), fill=(210, 210, 213), width=S)

    # -----------------------------------------------------------------------
    # Balance card
    # -----------------------------------------------------------------------
    card_margin = 16 * S
    card_top = sep_y + 16 * S
    card_h = 80 * S
    d.rounded_rectangle(
        (card_margin, card_top, RW - card_margin, card_top + card_h),
        radius=12 * S, fill=(255, 255, 255),
    )
    d.text((card_margin + 16 * S, card_top + 12 * S), "Баланс (CHF)", fill=(142, 142, 147), font=f_tx_sub)
    balance = round(random.uniform(1200, 9800), 2)
    bal_str = f"{balance:,.2f}".replace(",", "\u2019")
    d.text((card_margin + 16 * S, card_top + 34 * S), bal_str, fill=(0, 0, 0), font=f_title)

    # -----------------------------------------------------------------------
    # Build transaction list
    # -----------------------------------------------------------------------
    base_date = now.date()
    txs: list[_Tx] = []

    # User's transaction (most recent — top)
    txs.append(_Tx(
        title=service_name[:24],
        subtitle="Онлайн-платёж",
        date_text=base_date.strftime("%d.%m.%Y"),
        amount_text=_chf(amount_chf),
    ))

    # Random Swiss merchant transactions
    used = set()
    for _ in range(12):
        days_ago = random.randint(1, 14)
        tx_date = base_date - timedelta(days=days_ago)
        merchant, cat = random.choice(_MERCHANTS)
        amt = round(random.uniform(2.5, 189.9), 2)
        key = (merchant, tx_date.isoformat())
        if key in used:
            continue
        used.add(key)
        txs.append(_Tx(
            title=merchant,
            subtitle=cat,
            date_text=tx_date.strftime("%d.%m.%Y"),
            amount_text=_chf(amt),
        ))

    # Sort so user tx stays on top (already is at index 0); rest sorted by date desc
    txs = [txs[0]] + sorted(txs[1:], key=lambda t: t.date_text, reverse=True)

    # -----------------------------------------------------------------------
    # Section header
    # -----------------------------------------------------------------------
    list_top = card_top + card_h + 24 * S
    month_label = now.strftime("%B %Y")
    d.text((card_margin, list_top), month_label.upper(), fill=(142, 142, 147), font=f_section)
    list_top += 20 * S

    # -----------------------------------------------------------------------
    # White card for transaction list
    # -----------------------------------------------------------------------
    row_h = 58 * S
    max_rows = min(len(txs), 8)
    list_h = max_rows * row_h + 4 * S
    list_bottom = list_top + list_h

    d.rounded_rectangle(
        (card_margin, list_top, RW - card_margin, list_bottom),
        radius=12 * S, fill=(255, 255, 255),
    )

    # -----------------------------------------------------------------------
    # Transaction rows
    # -----------------------------------------------------------------------
    ry = list_top + 2 * S
    for i, tx in enumerate(txs[:max_rows]):
        mid_y = ry + row_h // 2

        # Icon circle
        icon_cx = card_margin + 28 * S
        icon_r = 18 * S
        icon_color = (0, 122, 255) if i == 0 else _merchant_color(tx.title)
        d.ellipse(
            (icon_cx - icon_r, mid_y - icon_r, icon_cx + icon_r, mid_y + icon_r),
            fill=icon_color,
        )
        # Icon letter
        letter = tx.title[0].upper()
        lw = _text_w(d, letter, f_tx_sub)
        lh = _text_h(d, letter, f_tx_sub)
        d.text(
            (icon_cx - lw // 2, mid_y - lh // 2),
            letter, fill=(255, 255, 255), font=f_tx_sub,
        )

        # Merchant name
        tx_x = card_margin + 54 * S
        d.text((tx_x, mid_y - 14 * S), tx.title, fill=(0, 0, 0), font=f_tx_name)
        d.text((tx_x, mid_y + 2 * S), tx.date_text, fill=(142, 142, 147), font=f_tx_sub)

        # Amount (right aligned)
        amt_w = _text_w(d, tx.amount_text, f_tx_amt)
        d.text(
            (RW - card_margin - amt_w - 4 * S, mid_y - 8 * S),
            tx.amount_text, fill=(0, 0, 0), font=f_tx_amt,
        )

        ry += row_h
        # Divider (except after last row)
        if i < max_rows - 1:
            div_x = card_margin + 54 * S
            d.line((div_x, ry, RW - card_margin - 4 * S, ry), fill=(210, 210, 213), width=max(1, S // 2))

    # -----------------------------------------------------------------------
    # Watermark overlay — prominent, diagonal, cannot be cropped easily
    # -----------------------------------------------------------------------
    _draw_watermark(img, d, RW, RH, f_wm_big, f_wm_small, S)

    # -----------------------------------------------------------------------
    # Scale down for output (anti-aliasing)
    # -----------------------------------------------------------------------
    out = img.resize((W, H), Image.LANCZOS)

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------

def _draw_watermark(
    img: Image.Image,
    d: ImageDraw.ImageDraw,
    RW: int,
    RH: int,
    f_big: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    f_small: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    S: int,
) -> None:
    """Draw a semi-transparent diagonal watermark over the whole image."""
    overlay = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    wm1 = "РОЗЫГРЫШ"
    wm2 = "FAKE / НЕ НАСТОЯЩИЙ ДОКУМЕНТ"

    # Diagonal band (top-right to bottom-left)
    # Draw repeated diagonal text
    step_y = 120 * S
    for start_y in range(-RH, RH * 2, step_y):
        od.text(
            (RW // 2 - _text_w(od, wm1, f_big) // 2, start_y),
            wm1, fill=(220, 0, 0, 80), font=f_big,
        )
        od.text(
            (RW // 2 - _text_w(od, wm2, f_small) // 2, start_y + 34 * S),
            wm2, fill=(200, 0, 0, 60), font=f_small,
        )

    # Also a solid banner in the middle for maximum visibility
    banner_top = RH // 2 - 30 * S
    banner_bot = RH // 2 + 30 * S
    od.rectangle((0, banner_top, RW, banner_bot), fill=(220, 0, 0, 120))
    label = "⚠  РОЗЫГРЫШ / FAKE  ⚠"
    lw = _text_w(od, label, f_big)
    od.text(
        (RW // 2 - lw // 2, RH // 2 - _text_h(od, label, f_big) // 2),
        label, fill=(255, 255, 255, 255), font=f_big,
    )

    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    try:
        return int(draw.textlength(text, font=font))
    except AttributeError:
        return len(text) * 8


def _text_h(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[3] - bb[1]
    except AttributeError:
        return 14


_COLOR_MAP: dict[str, tuple[int, int, int]] = {
    "A": (88, 86, 214), "B": (52, 199, 89), "C": (255, 149, 0),
    "D": (0, 122, 255), "E": (255, 59, 48), "F": (90, 200, 250),
    "G": (88, 86, 214), "H": (52, 199, 89), "I": (255, 149, 0),
    "J": (255, 45, 85), "K": (100, 210, 255), "L": (255, 159, 10),
    "M": (52, 199, 89), "N": (0, 122, 255), "O": (255, 149, 0),
    "P": (88, 86, 214), "Q": (50, 173, 230), "R": (255, 69, 58),
    "S": (52, 199, 89), "T": (0, 122, 255), "U": (255, 149, 0),
    "V": (88, 86, 214), "W": (50, 173, 230), "X": (255, 59, 48),
    "Y": (52, 199, 89), "Z": (88, 86, 214),
}


def _merchant_color(name: str) -> tuple[int, int, int]:
    first = name[0].upper() if name else "A"
    return _COLOR_MAP.get(first, (142, 142, 147))
