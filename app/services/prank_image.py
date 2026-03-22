from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Swiss timezone
# ---------------------------------------------------------------------------

try:
    from zoneinfo import ZoneInfo as _ZI
    _CH_TZ: object = _ZI("Europe/Zurich")
except Exception:
    _CH_TZ = None


def _to_swiss(dt: datetime) -> datetime:
    """Return dt expressed in Swiss local time (Europe/Zurich)."""
    if _CH_TZ is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_CH_TZ)  # type: ignore[arg-type]
    # Fallback: manual offset (CET=+1, CEST=+2 in summer)
    offset_h = 2 if 3 <= dt.month <= 10 else 1
    from datetime import timedelta as _td
    tz = timezone(_td(hours=offset_h))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Tx:
    title: str
    subtitle: str
    sort_date: object   # datetime.date, used for sorting
    date_text: str
    amount_text: str


# ---------------------------------------------------------------------------
# Swiss merchant list (30 entries)
# ---------------------------------------------------------------------------

_MERCHANTS: list[tuple[str, str]] = [
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
    ("H&M", "Mode"),
    ("Digitec", "Elektronik"),
    ("Manor", "Warenhaus"),
    ("Aldi Suisse", "Supermarkt"),
    ("Lidl", "Lebensmittel"),
    ("Volg", "Einkauf"),
    ("SBB Railaway", "Reise"),
    ("Swiss Air", "Flug"),
    ("Uber", "Fahrt"),
    ("Uber Eats", "Lieferung"),
    ("Zara", "Mode"),
    ("Ochsner Sport", "Sport"),
    ("Interdiscount", "Elektronik"),
    ("Microspot", "Online-Shop"),
    ("Ticketcorner", "Tickets"),
    ("Sunrise", "Telekommunikation"),
]

_MONTH_DE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def _chf(value: float) -> str:
    """Format in Swiss CHF style: -1'234.50"""
    if value >= 1000:
        t = int(value) // 1000
        r = value - t * 1000
        return f"-{t}\u2019{r:06.2f}"
    return f"-{value:.2f}"


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _load_bold(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arialbd.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return _load_font(size)


# ---------------------------------------------------------------------------
# Text / drawing utilities
# ---------------------------------------------------------------------------

def _tw(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    """Text width in pixels."""
    try:
        return int(draw.textlength(text, font=font))
    except AttributeError:
        return len(text) * 8


def _tbb(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int, int, int]:
    """Tight bounding box (left, top, right, bottom)."""
    try:
        return draw.textbbox((0, 0), text, font=font)
    except AttributeError:
        w = len(text) * 8
        return (0, 0, w, 14)


def _draw_vc(draw: ImageDraw.ImageDraw, x: int, y_center: int,
             text: str, font, fill) -> None:
    """Draw text at x, vertically centered on y_center."""
    bb = _tbb(draw, text, font)
    y = y_center - (bb[3] - bb[1]) // 2 - bb[1]
    draw.text((x, y), text, fill=fill, font=font)


def _draw_cc(draw: ImageDraw.ImageDraw, x_center: int, y_center: int,
             text: str, font, fill) -> None:
    """Draw text horizontally and vertically centered."""
    w = _tw(draw, text, font)
    bb = _tbb(draw, text, font)
    y = y_center - (bb[3] - bb[1]) // 2 - bb[1]
    draw.text((x_center - w // 2, y), text, fill=fill, font=font)


def _draw_rc(draw: ImageDraw.ImageDraw, x_right: int, y_center: int,
             text: str, font, fill) -> None:
    """Draw text right-aligned and vertically centered."""
    w = _tw(draw, text, font)
    bb = _tbb(draw, text, font)
    y = y_center - (bb[3] - bb[1]) // 2 - bb[1]
    draw.text((x_right - w, y), text, fill=fill, font=font)


# ---------------------------------------------------------------------------
# iPhone status bar icons
# ---------------------------------------------------------------------------

def _draw_status_bar(
    draw: ImageDraw.ImageDraw,
    rw: int, sb_h: int,
    time_str: str,
    S: int,
    f_time,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """Draw a realistic iPhone-like status bar."""
    cy = sb_h // 2

    # --- Time (left side) ---
    _draw_vc(draw, 18 * S, cy, time_str, f_time, fill)

    # --- Right side (right → left): battery, wifi, signal bars ---
    rx = rw - 16 * S

    # Battery
    bw = 24 * S
    bh = 12 * S
    tip_w = 2 * S
    tip_h = 6 * S
    batt_fill = random.uniform(0.60, 0.92)

    bx1 = rx - tip_w - 1
    bx0 = bx1 - bw
    by0 = cy - bh // 2
    by1 = cy + bh // 2

    draw.rounded_rectangle((bx0, by0, bx1, by1),
                            radius=max(1, 2 * S), outline=fill, width=max(1, S))
    pad = 2 * S
    fill_w = int((bw - 2 * pad) * batt_fill)
    if fill_w > 0:
        draw.rounded_rectangle(
            (bx0 + pad, by0 + pad, bx0 + pad + fill_w, by1 - pad),
            radius=max(1, S), fill=fill,
        )
    # tip nub
    draw.rounded_rectangle(
        (bx1 + 1, cy - tip_h // 2, bx1 + 1 + tip_w, cy + tip_h // 2),
        radius=max(1, S), fill=fill,
    )
    rx -= (bw + tip_w + 8 * S)

    # WiFi (3 arcs + dot)
    wifi_w = 15 * S
    wcx = rx - wifi_w // 2
    dot_y = cy + 5 * S
    dot_r = max(1, S)
    draw.ellipse((wcx - dot_r, dot_y - dot_r, wcx + dot_r, dot_y + dot_r), fill=fill)
    for r in (4 * S, 7 * S, 10 * S):
        draw.arc(
            (wcx - r, dot_y - r, wcx + r, dot_y + r),
            start=220, end=320, fill=fill, width=max(1, S),
        )
    rx -= (wifi_w + 8 * S)

    # Cellular signal bars (4 bars, tallest on right)
    bar_w = max(2, 2 * S + 1)
    bar_gap = max(1, S)
    bar_heights = [3 * S, 5 * S, 7 * S, 9 * S]
    total_bars_w = len(bar_heights) * bar_w + (len(bar_heights) - 1) * bar_gap
    bar_bottom = cy + 5 * S
    bx = rx - total_bars_w
    for i, bh_ in enumerate(bar_heights):
        x0 = bx + i * (bar_w + bar_gap)
        draw.rounded_rectangle(
            (x0, bar_bottom - bh_, x0 + bar_w, bar_bottom),
            radius=max(1, S // 2), fill=fill,
        )


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
    Time shown is Swiss local time (Europe/Zurich).
    Contains a visible 'SCHERZ / FAKE' watermark.
    Does NOT copy any real bank interface 1-to-1.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_ch = _to_swiss(now)

    # -----------------------------------------------------------------------
    # Canvas — iPhone 12/13 logical proportions, rendered at 3×
    # -----------------------------------------------------------------------
    W, H = 390, 844
    S = 3
    RW, RH = W * S, H * S

    BG    = (242, 242, 247)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY  = (142, 142, 147)
    BLUE  = (0, 122, 255)
    SEP   = (210, 210, 213)

    img = Image.new("RGB", (RW, RH), BG)
    d = ImageDraw.Draw(img)

    # -----------------------------------------------------------------------
    # Fonts
    # -----------------------------------------------------------------------
    f_time    = _load_bold(17 * S)
    f_nav     = _load_bold(17 * S)
    f_back    = _load_font(17 * S)
    f_bal_lbl = _load_font(13 * S)
    f_bal     = _load_bold(22 * S)
    f_section = _load_bold(12 * S)
    f_tx_name = _load_bold(15 * S)
    f_tx_sub  = _load_font(13 * S)
    f_tx_amt  = _load_bold(15 * S)

    # -----------------------------------------------------------------------
    # Layout constants (in scaled pixels)
    # -----------------------------------------------------------------------
    M      = 16 * S   # horizontal margin
    SB_H   = 44 * S   # status bar height
    NAV_H  = 44 * S   # nav bar height
    CARD_R = 12 * S   # card corner radius
    ROW_H  = 54 * S   # transaction row height
    ICON_R = 19 * S   # icon circle radius
    ICON_CX = M + ICON_R + 4 * S  # icon center x
    TX_X   = ICON_CX + ICON_R + 12 * S  # text left edge

    # -----------------------------------------------------------------------
    # 1. Status bar (Swiss time + icons)
    # -----------------------------------------------------------------------
    time_str = now_ch.strftime("%H:%M")
    _draw_status_bar(d, RW, SB_H, time_str, S, f_time, fill=BLACK)

    # -----------------------------------------------------------------------
    # 2. Navigation bar
    # -----------------------------------------------------------------------
    nav_top = SB_H
    nav_cy  = nav_top + NAV_H // 2
    _draw_cc(d, RW // 2, nav_cy, "Transaktionen", f_nav, BLACK)
    _draw_vc(d, 16 * S, nav_cy, "‹  Zurück", f_back, BLUE)

    sep_y = nav_top + NAV_H
    d.line((0, sep_y, RW, sep_y), fill=SEP, width=max(1, S))

    # -----------------------------------------------------------------------
    # 3. Balance card
    # -----------------------------------------------------------------------
    bal_top = sep_y + 16 * S
    bal_h   = 76 * S
    bal_bot = bal_top + bal_h
    d.rounded_rectangle((M, bal_top, RW - M, bal_bot), radius=CARD_R, fill=WHITE)

    _draw_vc(d, M + 16 * S, bal_top + 22 * S, "Kontostand (CHF)", f_bal_lbl, GRAY)
    balance = round(random.uniform(1500, 12000), 2)
    bal_str = f"{balance:,.2f}".replace(",", "\u2019")
    _draw_vc(d, M + 16 * S, bal_top + 54 * S, bal_str, f_bal, BLACK)

    # -----------------------------------------------------------------------
    # 4. Section header (German month name)
    # -----------------------------------------------------------------------
    SECT_H   = 30 * S
    SECT_GAP = 8 * S
    section_y = bal_bot + 14 * S
    month_de  = _MONTH_DE[now_ch.month]
    d.text((M, section_y), f"{month_de.upper()} {now_ch.year}",
           fill=GRAY, font=f_section)

    # -----------------------------------------------------------------------
    # 5. Build transaction list (enough to fill screen)
    # -----------------------------------------------------------------------
    list_top    = section_y + SECT_H + SECT_GAP
    bottom_pad  = 16 * S
    avail_h     = RH - list_top - bottom_pad
    max_rows    = max(6, avail_h // ROW_H)

    base_date = now_ch.date()
    txs: list[_Tx] = []

    # User's transaction — pinned at top
    txs.append(_Tx(
        title=service_name[:24],
        subtitle="Online-Zahlung",
        sort_date=base_date,
        date_text=base_date.strftime("%d.%m.%Y"),
        amount_text=_chf(amount_chf),
    ))

    # Random Swiss merchants — generate plenty of candidates
    used: set[tuple[str, str]] = set()
    attempts = 0
    while len(txs) < max_rows + 5 and attempts < 80:
        attempts += 1
        days_ago = random.randint(1, 21)
        tx_date  = base_date - timedelta(days=days_ago)
        merchant, cat = random.choice(_MERCHANTS)
        key = (merchant, tx_date.isoformat())
        if key in used:
            continue
        used.add(key)
        amt = round(random.uniform(2.5, 249.9), 2)
        txs.append(_Tx(
            title=merchant,
            subtitle=cat,
            sort_date=tx_date,
            date_text=tx_date.strftime("%d.%m.%Y"),
            amount_text=_chf(amt),
        ))

    # Keep user tx on top; sort rest by date descending (using actual date objects)
    txs = [txs[0]] + sorted(txs[1:], key=lambda t: t.sort_date, reverse=True)
    rows = txs[:max_rows]

    # -----------------------------------------------------------------------
    # 6. Transaction list card (extends to fill available space)
    # -----------------------------------------------------------------------
    list_bot = list_top + len(rows) * ROW_H
    d.rounded_rectangle((M, list_top, RW - M, list_bot), radius=CARD_R, fill=WHITE)

    # -----------------------------------------------------------------------
    # 7. Transaction rows
    # -----------------------------------------------------------------------
    for i, tx in enumerate(rows):
        row_top = list_top + i * ROW_H
        row_cy  = row_top + ROW_H // 2

        # Coloured icon circle
        icon_col = BLUE if i == 0 else _merchant_color(tx.title)
        d.ellipse(
            (ICON_CX - ICON_R, row_cy - ICON_R, ICON_CX + ICON_R, row_cy + ICON_R),
            fill=icon_col,
        )
        _draw_cc(d, ICON_CX, row_cy, tx.title[0].upper(), f_tx_sub, WHITE)

        # Title — placed above center
        title_y = row_cy - 14 * S
        d.text((TX_X, title_y), tx.title, fill=BLACK, font=f_tx_name)

        # Subtitle / date — below center
        sub_y = row_cy + 3 * S
        d.text((TX_X, sub_y), tx.date_text, fill=GRAY, font=f_tx_sub)

        # Amount — right-aligned and vertically centered in row
        _draw_rc(d, RW - M - 8 * S, row_cy, tx.amount_text, f_tx_amt, BLACK)

        # Divider (not after last row)
        if i < len(rows) - 1:
            div_y = row_top + ROW_H
            d.line((TX_X, div_y, RW - M - 8 * S, div_y),
                   fill=SEP, width=max(1, S // 2))

    # -----------------------------------------------------------------------
    # 8. Rounded corners (phone-screenshot look)
    # -----------------------------------------------------------------------
    mask = Image.new("L", (RW, RH), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, RW - 1, RH - 1), radius=40 * S, fill=255,
    )
    result = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    result.paste(img, mask=mask)

    out = result.resize((W, H), Image.LANCZOS)

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

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
