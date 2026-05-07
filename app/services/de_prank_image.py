"""
Generates a fake iOS-style German bank transaction list screenshot.
Adapted from prank_image.py for Germany: EUR currency, Berlin timezone,
German merchants and banks.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
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
    _merchant_color,
)

# ---------------------------------------------------------------------------
# German timezone
# ---------------------------------------------------------------------------

try:
    from zoneinfo import ZoneInfo as _ZI
    _DE_TZ: object = _ZI("Europe/Berlin")
except Exception:
    _DE_TZ = None


def _to_berlin(dt: datetime) -> datetime:
    """Return dt expressed in German local time (Europe/Berlin)."""
    if _DE_TZ is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_DE_TZ)  # type: ignore[arg-type]
    # Fallback: CET=+1, CEST=+2 in summer (same switch dates as Switzerland)
    offset_h = 2 if 3 <= dt.month <= 10 else 1
    tz = timezone(timedelta(hours=offset_h))
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
    sort_date: object   # datetime.date
    date_text: str
    amount_text: str


# ---------------------------------------------------------------------------
# German merchant list
# ---------------------------------------------------------------------------

_DE_MERCHANTS: list[tuple[str, str]] = [
    ("Rewe", "Lebensmittel"),
    ("Edeka", "Supermarkt"),
    ("Kaufland", "Einkauf"),
    ("Lidl", "Discounter"),
    ("Aldi", "Discounter"),
    ("dm", "Drogerie"),
    ("Rossmann", "Drogerie"),
    ("MediaMarkt", "Elektronik"),
    ("Saturn", "Elektronik"),
    ("Deutsche Bahn", "Ticket"),
    ("Amazon", "Online-Shop"),
    ("Zalando", "Mode"),
    ("Otto", "Online-Shop"),
    ("H&M", "Mode"),
    ("Zara", "Mode"),
    ("McDonalds", "Restaurant"),
    ("Burger King", "Restaurant"),
    ("Starbucks", "Café"),
    ("Netflix", "Streaming"),
    ("Spotify", "Musik"),
    ("Apple", "App Store"),
    ("Telekom", "Mobilfunk"),
    ("Vodafone", "Telekommunikation"),
    ("O2", "Telekommunikation"),
    ("Decathlon", "Sport"),
    ("Ikea", "Möbel"),
    ("Hornbach", "Baumarkt"),
    ("Obi", "Baumarkt"),
    ("Netto", "Supermarkt"),
    ("Penny", "Discounter"),
]

_MONTH_DE = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def _eur(value: float) -> str:
    """Format German EUR debit: -1.234,50"""
    s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{s}"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_de_prank_bank_screen(
    service_name: str,
    amount_eur: float,
    now: datetime | None = None,
) -> bytes:
    """
    Generate a light iOS-style German bank transaction history screenshot.
    Time shown is German local time (Europe/Berlin). Currency: EUR.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    now_de = _to_berlin(now)

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

    f_time    = _load_bold(17 * S)
    f_nav     = _load_bold(17 * S)
    f_back    = _load_font(17 * S)
    f_bal_lbl = _load_font(13 * S)
    f_bal     = _load_bold(22 * S)
    f_section = _load_bold(12 * S)
    f_tx_name = _load_bold(15 * S)
    f_tx_sub  = _load_font(13 * S)
    f_tx_amt  = _load_bold(15 * S)

    M       = 16 * S
    SB_H    = 44 * S
    NAV_H   = 44 * S
    CARD_R  = 12 * S
    ROW_H   = 54 * S
    ICON_R  = 19 * S
    ICON_CX = M + ICON_R + 4 * S
    TX_X    = ICON_CX + ICON_R + 12 * S

    # Status bar
    _draw_status_bar(d, RW, SB_H, now_de.strftime("%H:%M"), S, f_time, fill=BLACK)

    # Navigation bar
    nav_top = SB_H
    nav_cy  = nav_top + NAV_H // 2
    _draw_cc(d, RW // 2, nav_cy, "Umsätze", f_nav, BLACK)
    _draw_vc(d, 16 * S, nav_cy, "‹  Zurück", f_back, BLUE)
    d.line((0, nav_top + NAV_H, RW, nav_top + NAV_H), fill=SEP, width=max(1, S))

    # Balance card
    bal_top = nav_top + NAV_H + 16 * S
    bal_h   = 76 * S
    bal_bot = bal_top + bal_h
    d.rounded_rectangle((M, bal_top, RW - M, bal_bot), radius=CARD_R, fill=WHITE)

    _draw_vc(d, M + 16 * S, bal_top + 22 * S, "Kontostand (EUR)", f_bal_lbl, GRAY)
    balance = round(random.uniform(1500, 12000), 2)
    bal_str = f"{balance:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    _draw_vc(d, M + 16 * S, bal_top + 54 * S, bal_str, f_bal, BLACK)

    # Section header
    SECT_H    = 30 * S
    SECT_GAP  = 8 * S
    section_y = bal_bot + 14 * S
    month_de  = _MONTH_DE[now_de.month]
    d.text((M, section_y), f"{month_de.upper()} {now_de.year}",
           fill=GRAY, font=f_section)

    # Transaction list
    list_top   = section_y + SECT_H + SECT_GAP
    bottom_pad = 16 * S
    avail_h    = RH - list_top - bottom_pad
    max_rows   = max(6, avail_h // ROW_H)

    base_date = now_de.date()
    txs: list[_Tx] = []

    txs.append(_Tx(
        title=service_name[:24],
        subtitle="Online-Zahlung",
        sort_date=base_date,
        date_text=base_date.strftime("%d.%m.%Y"),
        amount_text=_eur(amount_eur),
    ))

    used: set[tuple[str, str]] = set()
    attempts = 0
    while len(txs) < max_rows + 5 and attempts < 80:
        attempts += 1
        days_ago = random.randint(1, 21)
        tx_date  = base_date - timedelta(days=days_ago)
        merchant, cat = random.choice(_DE_MERCHANTS)
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
            amount_text=_eur(amt),
        ))

    txs = [txs[0]] + sorted(txs[1:], key=lambda t: t.sort_date, reverse=True)
    rows = txs[:max_rows]

    list_bot = list_top + len(rows) * ROW_H
    d.rounded_rectangle((M, list_top, RW - M, list_bot), radius=CARD_R, fill=WHITE)

    for i, tx in enumerate(rows):
        row_top = list_top + i * ROW_H
        row_cy  = row_top + ROW_H // 2

        icon_col = BLUE if i == 0 else _merchant_color(tx.title)
        d.ellipse(
            (ICON_CX - ICON_R, row_cy - ICON_R, ICON_CX + ICON_R, row_cy + ICON_R),
            fill=icon_col,
        )
        _draw_cc(d, ICON_CX, row_cy, tx.title[0].upper(), f_tx_sub, WHITE)

        title_y = row_cy - 14 * S
        d.text((TX_X, title_y), tx.title, fill=BLACK, font=f_tx_name)

        sub_y = row_cy + 3 * S
        d.text((TX_X, sub_y), tx.date_text, fill=GRAY, font=f_tx_sub)

        _draw_rc(d, RW - M - 8 * S, row_cy, tx.amount_text, f_tx_amt, BLACK)

        if i < len(rows) - 1:
            div_y = row_top + ROW_H
            d.line((TX_X, div_y, RW - M - 8 * S, div_y),
                   fill=SEP, width=max(1, S // 2))

    # Rounded corners
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
