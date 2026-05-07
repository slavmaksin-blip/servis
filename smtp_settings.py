"""Runtime-mutable SMTP configuration.

On startup the config is loaded from ``smtp_override.json`` (if it exists)
and falls back to environment variables.  The ``apply()`` function replaces
the in-process singleton *and* writes the new values to ``smtp_override.json``
so the new config survives a bot restart.

**Security note:** ``smtp_override.json`` stores the SMTP password in
plaintext.  Ensure the file is readable only by the bot process (e.g.
``chmod 600 smtp_override.json``) and is excluded from version control.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

_OVERRIDE_FILE = Path(__file__).parent / "smtp_override.json"


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    use_ssl: bool  # True → implicit SSL/TLS (port 465); False → STARTTLS (port 587)


def _load() -> SmtpConfig:
    if _OVERRIDE_FILE.exists():
        data = json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
        return SmtpConfig(**data)
    return SmtpConfig(
        host=os.getenv("SMTP_HOST", "smtp.mail.ch"),
        port=int(os.getenv("SMTP_PORT", "465")),
        user=os.environ["SMTP_USER"],
        password=os.environ["SMTP_PASS"],
        use_ssl=os.getenv("SMTP_SSL", "true").lower() in ("1", "true", "yes"),
    )


# Runtime-mutable singleton — replaced by /smtp command without restart.
current: SmtpConfig = _load()


def apply(cfg: SmtpConfig) -> None:
    """Replace the active SMTP config and persist it to disk."""
    global current
    current = cfg
    _OVERRIDE_FILE.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
