"""
SQLite database helpers.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple

from config import DATABASE_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                tg_id       INTEGER UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                balance     REAL    NOT NULL DEFAULT 0.0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id  INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                description TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_tg_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS sms_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id  INTEGER NOT NULL,
                phone       TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                sms_id      TEXT,
                status      INTEGER,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_tg_id) REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS email_orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id      INTEGER NOT NULL,
                activation_id   TEXT    NOT NULL,
                email           TEXT    NOT NULL,
                site            TEXT    NOT NULL,
                domain          TEXT    NOT NULL,
                status          TEXT    NOT NULL DEFAULT 'active',
                created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_tg_id) REFERENCES users(tg_id)
            );
            """
        )


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_or_create_user(tg_id: int, username: str, full_name: str) -> sqlite3.Row:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (tg_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
            """,
            (tg_id, username, full_name),
        )
        return conn.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()


def get_user(tg_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()


def get_all_users() -> List[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()


def update_balance(tg_id: int, delta: float, description: str = "") -> float:
    """Add *delta* (positive or negative) to the user's balance and log it."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE tg_id = ?",
            (delta, tg_id),
        )
        conn.execute(
            "INSERT INTO transactions (user_tg_id, amount, description) VALUES (?, ?, ?)",
            (tg_id, delta, description),
        )
        row = conn.execute(
            "SELECT balance FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()
        return row["balance"]


def get_balance(tg_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT balance FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()
        return row["balance"] if row else 0.0


def get_transaction_history(tg_id: int, limit: int = 10) -> List[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM transactions
            WHERE user_tg_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tg_id, limit),
        ).fetchall()


# ---------------------------------------------------------------------------
# SMS log helpers
# ---------------------------------------------------------------------------

def log_sms(
    user_tg_id: int,
    phone: str,
    content: str,
    sms_id: Optional[str] = None,
    status: Optional[int] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sms_logs (user_tg_id, phone, content, sms_id, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_tg_id, phone, content, sms_id, status),
        )


# ---------------------------------------------------------------------------
# Email order helpers
# ---------------------------------------------------------------------------

def save_email_order(
    user_tg_id: int,
    activation_id: str,
    email: str,
    site: str,
    domain: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO email_orders (user_tg_id, activation_id, email, site, domain)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_tg_id, activation_id, email, site, domain),
        )


def get_email_orders(user_tg_id: int) -> List[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM email_orders
            WHERE user_tg_id = ?
            ORDER BY created_at DESC
            """,
            (user_tg_id,),
        ).fetchall()


def update_email_order_status(activation_id: str, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE email_orders SET status = ? WHERE activation_id = ?",
            (status, activation_id),
        )
