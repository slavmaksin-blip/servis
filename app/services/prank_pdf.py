"""
Generates a fake Swiss-bank debit-notification PDF (Belastungsanzeige).
Clearly marked as FAKE / ATTRAPPE — not a real bank document.
Uses DejaVu Unicode TTF fonts so all characters (umlauts, dashes, etc.)
render correctly on any platform (fonts are bundled with the project).
"""
from __future__ import annotations

import os
import random
import string
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

# ---------------------------------------------------------------------------
# Font paths — bundled DejaVu first, then common system locations
# ---------------------------------------------------------------------------

_ASSETS = Path(__file__).parent.parent / "assets" / "fonts"

_FONT_CANDIDATES = [
    str(_ASSETS / "DejaVuSans.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
]
_FONT_BOLD_CANDIDATES = [
    str(_ASSETS / "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\calibrib.ttf",
]


def _find_font(candidates: list[str]) -> str | None:
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Swiss timezone helper
# ---------------------------------------------------------------------------

try:
    from zoneinfo import ZoneInfo as _ZI
    _CH_TZ: object = _ZI("Europe/Zurich")
except Exception:
    _CH_TZ = None


def _last_sunday(year: int, month: int) -> int:
    """Return the day-of-month of the last Sunday in the given month."""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    # weekday(): Monday=0 … Sunday=6
    offset = datetime(year, month, last_day).weekday()
    return last_day - ((offset + 1) % 7)


def _now_ch() -> datetime:
    now = datetime.now(timezone.utc)
    if _CH_TZ is not None:
        return now.astimezone(_CH_TZ)  # type: ignore[arg-type]
    # Accurate DST: last Sunday in March → last Sunday in October
    dst_start = datetime(now.year, 3, _last_sunday(now.year, 3), 1, 0, 0, tzinfo=timezone.utc)
    dst_end   = datetime(now.year, 10, _last_sunday(now.year, 10), 1, 0, 0, tzinfo=timezone.utc)
    offset_h = 2 if dst_start <= now < dst_end else 1
    return now.astimezone(timezone(timedelta(hours=offset_h)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DE_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def _chf_fmt(value: float) -> str:
    """Swiss CHF format with apostrophe thousands separator: 1'234.50"""
    return f"{value:,.2f}".replace(",", "'")


def _random_ref() -> str:
    """Generate a plausible Swiss payment reference number."""
    return (
        "".join(random.choices(string.digits, k=6))
        + " "
        + "".join(random.choices(string.digits, k=5))
        + " "
        + "".join(random.choices(string.digits, k=5))
    )


def _build_iban(suffix: str) -> str:
    """Build a masked IBAN display: CH** **** **** **** **XXXX."""
    s = suffix.zfill(4)[:4]
    return f"CH** **** **** **** **{s}"


def _random_balance(amount: float) -> float:
    """Random remaining balance after deduction."""
    prev = round(random.uniform(amount + 50, amount + 8000), 2)
    return round(prev - amount, 2)


# ---------------------------------------------------------------------------
# PDF document class
# ---------------------------------------------------------------------------

class _BankPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(left=20, top=15, right=20)

        font_reg = _find_font(_FONT_CANDIDATES)
        font_bold = _find_font(_FONT_BOLD_CANDIDATES)

        if not font_reg or not font_bold:
            raise RuntimeError(
                "No Unicode TTF font found. "
                "Expected bundled font at app/assets/fonts/DejaVuSans*.ttf "
                "or a system DejaVu/Liberation/Arial font."
            )

        self.add_font("Sans", style="", fname=font_reg)
        self.add_font("Sans", style="B", fname=font_bold)

    def _sf(self, bold: bool = False, size: int = 9) -> None:
        """Set font."""
        self.set_font("Sans", style="B" if bold else "", size=size)

    def _hline(self, lw: float = 0.3, color: tuple = (180, 180, 180)) -> None:
        self.set_line_width(lw)
        self.set_draw_color(*color)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def _field_row(self, label: str, value: str, bold_value: bool = False) -> None:
        """Two-column label / value row."""
        col_w = (self.w - self.l_margin - self.r_margin) / 2
        self._sf(bold=False, size=9)
        self.set_text_color(100, 100, 100)
        self.cell(col_w, 6, label, new_x="RIGHT", new_y="TOP")
        self._sf(bold=bold_value, size=9)
        self.set_text_color(20, 20, 20)
        self.cell(col_w, 6, value, new_x="LMARGIN", new_y="NEXT")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_prank_bank_pdf(
    account_holder: str,
    iban_suffix: str,
    service_name: str,
    amount_chf: float,
) -> bytes:
    """
    Generate a fake Swiss-bank debit-notification PDF (all German text).
    Clearly marked FAKE / ATTRAPPE throughout — no legal value whatsoever.
    """
    now = _now_ch()
    date_str = f"{now.day:02d}.{now.month:02d}.{now.year}"
    date_long = f"{now.day}. {_DE_MONTHS[now.month]} {now.year}"
    value_date = now.date() + timedelta(days=1)
    value_date_str = f"{value_date.day:02d}.{value_date.month:02d}.{value_date.year}"

    ref_number = _random_ref()
    iban_display = _build_iban(iban_suffix)
    balance_after = _random_balance(amount_chf)
    amount_str = _chf_fmt(amount_chf)
    balance_str = _chf_fmt(balance_after)
    creditor_ref = "RF" + "".join(random.choices(string.digits, k=14))

    pdf = _BankPDF()
    pdf.add_page()
    page_w = pdf.w - pdf.l_margin - pdf.r_margin

    # -----------------------------------------------------------------------
    # Header — bank name + date
    # -----------------------------------------------------------------------
    pdf._sf(bold=True, size=18)
    pdf.set_text_color(210, 0, 0)
    pdf.cell(page_w, 9, "PostFinance AG", new_x="RIGHT", new_y="TOP")

    pdf._sf(bold=False, size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 9, f"Bern, {date_long}", new_x="LMARGIN", new_y="NEXT", align="R")

    pdf._sf(bold=False, size=8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(page_w, 5, "Nordring 8  |  3030 Bern  |  www.postfinance.ch",
             new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_line_width(0.8)
    pdf.set_draw_color(210, 0, 0)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # -----------------------------------------------------------------------
    # Document title
    # -----------------------------------------------------------------------
    pdf._sf(bold=True, size=14)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(page_w, 8, "Belastungsanzeige", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf._sf(bold=False, size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(page_w, 5, "Kontobelastung / Zahlungsbestätigung",
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(5)
    pdf._hline()

    # -----------------------------------------------------------------------
    # Account section
    # -----------------------------------------------------------------------
    pdf._sf(bold=True, size=10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(page_w, 6, "KONTODATEN", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf._field_row("Kontoinhaber:", account_holder)
    pdf._field_row("IBAN:", iban_display)
    pdf._field_row("Währung:", "CHF – Schweizer Franken")

    pdf.ln(4)
    pdf._hline()

    # -----------------------------------------------------------------------
    # Transaction details
    # -----------------------------------------------------------------------
    pdf._sf(bold=True, size=10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(page_w, 6, "TRANSAKTIONSDETAILS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf._field_row("Buchungsdatum:", date_str)
    pdf._field_row("Valutadatum:", value_date_str)
    pdf._field_row("Zahlungsempfänger:", service_name)
    pdf._field_row("Verwendungszweck:", "Online-Zahlung / Dienstleistung")
    pdf._field_row("Transaktionsart:", "Lastschrift (Debit)")
    pdf._field_row("Referenznummer:", ref_number)
    pdf._field_row("Gläubiger-ID:", creditor_ref)

    pdf.ln(5)
    pdf._hline()

    # -----------------------------------------------------------------------
    # Amount block — highlighted background
    # -----------------------------------------------------------------------
    pdf.set_fill_color(245, 245, 245)
    stripe_y = pdf.get_y()
    pdf.rect(pdf.l_margin, stripe_y, page_w, 22, style="F")
    pdf.set_y(stripe_y + 3)

    pdf._sf(bold=False, size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(page_w, 5, "Belasteter Betrag", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf._sf(bold=True, size=22)
    pdf.set_text_color(210, 0, 0)
    pdf.cell(page_w, 11, f"CHF {amount_str}", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(5)
    pdf._hline()

    # -----------------------------------------------------------------------
    # Balance after transaction
    # -----------------------------------------------------------------------
    pdf._field_row("Verfügbares Guthaben nach Buchung:", f"CHF {balance_str}",
                   bold_value=True)

    pdf.ln(5)
    pdf._hline()

    # -----------------------------------------------------------------------
    # Info notice
    # -----------------------------------------------------------------------
    pdf._sf(bold=False, size=8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        page_w, 4.5,
        "Bei Fragen zu dieser Transaktion wenden Sie sich bitte an den PostFinance "
        "Kundendienst unter 0800 888 710 (kostenlos aus der Schweiz) oder per "
        "E-Mail an info@postfinance.ch.",
    )

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    pdf.set_y(pdf.h - 20)
    pdf._hline(lw=0.3, color=(180, 180, 180))

    pdf._sf(bold=False, size=7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(page_w / 2, 4, "PostFinance AG · Nordring 8 · 3030 Bern",
             new_x="RIGHT", new_y="TOP")
    pdf.cell(page_w / 2, 4, f"Erstellt am: {date_str}",
             new_x="LMARGIN", new_y="NEXT", align="R")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
