"""Per-template email settings (sender name and subject prefix).

Persisted to ``template_settings.json``.  Updated at runtime by the /smtp
admin command; changes survive bot restarts.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

_FILE = Path(__file__).parent / "template_settings.json"

# Canonical IDs, display labels and template file paths.
TEMPLATE_IDS: tuple[str, ...] = ("ricardo", "postfinance")

TEMPLATE_LABELS: dict[str, str] = {
    "ricardo": "Ricardo 2.0",
    "postfinance": "PostFinance 2.0",
}

TEMPLATE_FILES: dict[str, Path] = {
    "ricardo": Path(__file__).parent / "PDF" / "ricardo.txt",
    "postfinance": Path(__file__).parent / "PDF" / "postfinance.txt",
}


@dataclass
class TemplateConfig:
    sender_name: str = ""
    subject: str = ""


def _load() -> dict[str, TemplateConfig]:
    if _FILE.exists():
        raw = json.loads(_FILE.read_text(encoding="utf-8"))
        result: dict[str, TemplateConfig] = {}
        for tid in TEMPLATE_IDS:
            entry = raw.get(tid, {})
            result[tid] = TemplateConfig(
                sender_name=entry.get("sender_name", ""),
                subject=entry.get("subject", ""),
            )
        return result
    return {tid: TemplateConfig() for tid in TEMPLATE_IDS}


# Runtime-mutable singleton — updated by /smtp command without restart.
current: dict[str, TemplateConfig] = _load()


def apply(tid: str, cfg: TemplateConfig) -> None:
    """Update settings for one template and persist all to disk."""
    if tid not in TEMPLATE_IDS:
        raise ValueError(f"Unknown template ID: {tid!r}. Must be one of {TEMPLATE_IDS}")
    global current
    current[tid] = cfg
    _FILE.write_text(
        json.dumps(
            {k: asdict(v) for k, v in current.items()},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
