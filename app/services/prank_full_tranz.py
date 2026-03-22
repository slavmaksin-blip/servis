"""
Generates a fake iOS-style detailed bank transaction screenshot
("Transaktionsdetails" view — like tapping on a single transaction).

Clearly marked as FAKE — not a real bank document.
Uses the same font helpers as prank_image.py.
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image, ImageDraw

from app.services.prank_image import (
    _load_bold,
    _load_font,
    _draw_cc,
    _draw_rc,
    _draw_vc,
    _draw_status_bar,
    _to_swiss,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CATEGORIES = [
    "Online-Dienste",
    "Streaming",
    "Einkauf",
    "Restaurant & Café",
    "Reise",
    "Telekommunikation",
    "Software & Apps",
    "Abonnement",
    "Unterhaltung",
    "Dienstleistung",
]


def _rand_ref() -> str:
    """Random Swiss-style payment reference number."""
    return " ".join([
        "".join(random.choices(string.digits, k=3)),
        "".join(random.choices(string.digits, k=3)),
        "".join(random.choices(string.digits, k=3)),
        "".join(random.choices(string.digits, k=2)),
    ])


def _rand_iban() -> str:
    suffix = "".join(random.choices(string.digits, k=4))
    return f"CH** **** **** **** **{suffix}"


def _rand_mandate() -> str:
    return "RF" + "".join(random.choices(string.digits, k=16))


def _rand_creditor() -> str:
    return "AT" + "".join(random.choices(string.digits, k=2)) + "ZZZ" + \
           "".join(random.choices(string.digits, k=9))


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_prank_full_tranz_screen(
    service_name: str,
    amount_chf: float,
    now: datetime | None = None,
) -> bytes:
    """
    Generate a fake iOS-style detailed transaction detail screenshot.
    The user supplies service name and amount; everything else is randomised.
    Contains a red FAKE watermark (no boxes or highlights).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_ch = _to_swiss(now)

    # Randomise transaction time: within the last 8 hours
    minutes_ago = random.randint(3, 480)
    tx_time = now_ch - timedelta(minutes=minutes_ago)
    date_str      = tx_time.strftime("%d.%m.%Y")
    time_str      = tx_time.strftime("%H:%M:%S")
    date_time_str = f"{date_str}  ·  {time_str}"
    value_date    = (tx_time + timedelta(days=1)).strftime("%d.%m.%Y")

    ref      = _rand_ref()
    iban     = _rand_iban()
    mandate  = _rand_mandate()
    creditor = _rand_creditor()
    category = random.choice(_CATEGORIES)

    # -----------------------------------------------------------------------
    # Canvas — same proportions as prank_image (iPhone 12/13 @ 3×)
    # -----------------------------------------------------------------------
    W, H   = 390, 844
    S      = 3
    RW, RH = W * S, H * S

    BG    = (242, 242, 247)
    WHITE = (255, 255, 255)
    BLACK = (20, 20, 20)
    GRAY  = (142, 142, 147)
    BLUE  = (0, 122, 255)
    RED   = (210, 0, 0)
    GREEN = (52, 199, 89)
    SEP   = (210, 210, 213)

    img = Image.new("RGB", (RW, RH), BG)
    d   = ImageDraw.Draw(img)

    # -----------------------------------------------------------------------
    # Fonts
    # -----------------------------------------------------------------------
    f_time    = _load_bold(17 * S)
    f_nav     = _load_bold(17 * S)
    f_back    = _load_font(17 * S)
    f_svc     = _load_font(13 * S)
    f_amount  = _load_bold(32 * S)
    f_status  = _load_bold(13 * S)
    f_dt      = _load_font(12 * S)
    f_row_lbl = _load_font(14 * S)
    f_row_val = _load_bold(13 * S)
    f_sect    = _load_bold(11 * S)

    M      = 16 * S
    SB_H   = 44 * S
    NAV_H  = 44 * S
    CARD_R = 12 * S
    ROW_H  = 44 * S

    # -----------------------------------------------------------------------
    # 1. Status bar
    # -----------------------------------------------------------------------
    _draw_status_bar(d, RW, SB_H, now_ch.strftime("%H:%M"), S, f_time, fill=BLACK)

    # -----------------------------------------------------------------------
    # 2. Navigation bar
    # -----------------------------------------------------------------------
    nav_top = SB_H
    nav_cy  = nav_top + NAV_H // 2
    _draw_cc(d, RW // 2, nav_cy, "Transaktionsdetails", f_nav, BLACK)
    _draw_vc(d, 16 * S, nav_cy, "‹ Назад", f_back, BLUE)
    d.line((0, nav_top + NAV_H, RW, nav_top + NAV_H), fill=SEP, width=max(1, S))

    y = nav_top + NAV_H + 16 * S

    # -----------------------------------------------------------------------
    # 3. Amount card (service name / amount / status / date+time)
    # -----------------------------------------------------------------------
    amt_card_h = 108 * S
    d.rounded_rectangle((M, y, RW - M, y + amt_card_h), radius=CARD_R, fill=WHITE)

    # Service label (gray, small, centered near top)
    svc_label = service_name[:28]
    _draw_cc(d, RW // 2, y + 20 * S, svc_label, f_svc, GRAY)

    # Amount (large, red, centered)
    amt_str = f"CHF {amount_chf:,.2f}".replace(",", "\u2019")
    _draw_cc(d, RW // 2, y + 52 * S, f"\u2212 {amt_str}", f_amount, RED)

    # Status (green, centered)
    _draw_cc(d, RW // 2, y + 78 * S, "\u2713  Abgeschlossen", f_status, GREEN)

    # Date + time (gray, centered)
    _draw_cc(d, RW // 2, y + 96 * S, date_time_str, f_dt, GRAY)

    y += amt_card_h + 12 * S

    # -----------------------------------------------------------------------
    # 4. Transaction details card
    # -----------------------------------------------------------------------
    detail_rows: list[tuple[str, str]] = [
        ("Empfänger",       service_name[:26]),
        ("Datum",           date_str),
        ("Uhrzeit",         time_str),
        ("Referenz-Nr.",    ref),
        ("Kategorie",       category),
        ("Transaktionsart", "Online-Lastschrift"),
        ("Konto",           iban),
        ("Währung",         "CHF"),
    ]

    # Section label
    d.text((M + 4 * S, y), "TRANSAKTIONSDETAILS", fill=GRAY, font=f_sect)
    y += 20 * S + 4 * S

    card_h = len(detail_rows) * ROW_H
    d.rounded_rectangle((M, y, RW - M, y + card_h), radius=CARD_R, fill=WHITE)

    for i, (lbl, val) in enumerate(detail_rows):
        row_y  = y + i * ROW_H
        row_cy = row_y + ROW_H // 2
        _draw_vc(d, M + 16 * S, row_cy, lbl, f_row_lbl, GRAY)
        _draw_rc(d, RW - M - 16 * S, row_cy, val, f_row_val, BLACK)
        if i < len(detail_rows) - 1:
            d.line((M + 16 * S, row_y + ROW_H, RW - M - 8 * S, row_y + ROW_H),
                   fill=SEP, width=max(1, S // 2))

    y += card_h + 12 * S

    # -----------------------------------------------------------------------
    # 5. Booking details card (draw only as many rows as fit)
    # -----------------------------------------------------------------------
    booking_rows: list[tuple[str, str]] = [
        ("Valutadatum",  value_date),
        ("Buchungstext", service_name.upper()[:18]),
        ("Mandat-ID",    mandate[:22]),
        ("Gläubiger-ID", creditor[:22]),
    ]

    remaining = RH - 16 * S - y  # pixels remaining before bottom padding
    max_brows = max(1, min(len(booking_rows), remaining // ROW_H - 1))
    booking_rows = booking_rows[:max_brows]

    if booking_rows and y + 24 * S + len(booking_rows) * ROW_H < RH - 8 * S:
        d.text((M + 4 * S, y), "BUCHUNGSDETAILS", fill=GRAY, font=f_sect)
        y += 20 * S + 4 * S

        book_h = len(booking_rows) * ROW_H
        d.rounded_rectangle((M, y, RW - M, y + book_h), radius=CARD_R, fill=WHITE)

        for i, (lbl, val) in enumerate(booking_rows):
            row_y  = y + i * ROW_H
            row_cy = row_y + ROW_H // 2
            _draw_vc(d, M + 16 * S, row_cy, lbl, f_row_lbl, GRAY)
            _draw_rc(d, RW - M - 16 * S, row_cy, val, f_row_val, BLACK)
            if i < len(booking_rows) - 1:
                d.line((M + 16 * S, row_y + ROW_H, RW - M - 8 * S, row_y + ROW_H),
                       fill=SEP, width=max(1, S // 2))

    # -----------------------------------------------------------------------
    # 6. Rounded corners (phone-screenshot look)
    # -----------------------------------------------------------------------
    mask = Image.new("L", (RW, RH), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, RW - 1, RH - 1), radius=40 * S, fill=255,
    )
    result = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    result.paste(img, mask=mask)

    out = result.resize((W, H), Image.Resampling.LANCZOS)

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
