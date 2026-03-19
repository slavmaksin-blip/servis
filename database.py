import time
import aiosqlite
from config import DATABASE_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                balance REAL DEFAULT 0.0,
                subscription_until INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                amount REAL NOT NULL,
                uses_left INTEGER DEFAULT 1,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                comment TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS email_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                email TEXT,
                password TEXT,
                order_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS product_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        await db.commit()


# ── Users ──────────────────────────────────────────────────────────────────────

async def add_user(telegram_id: int, username: str | None) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username),
        )
        await db.commit()


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_balance(telegram_id: int, delta: float) -> float:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (delta, telegram_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0


async def set_subscription(telegram_id: int, until_ts: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET subscription_until = ? WHERE telegram_id = ?",
            (until_ts, telegram_id),
        )
        await db.commit()


async def ban_user(telegram_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()


async def unban_user(telegram_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_user_count() -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_active_subscription_count() -> int:
    now = int(time.time())
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_until > ?", (now,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ── Categories ─────────────────────────────────────────────────────────────────

async def add_category(name: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        await db.commit()


async def get_categories() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ── Products ───────────────────────────────────────────────────────────────────

async def add_product(
    category_id: int, name: str, description: str, price: float, content: str
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO products (category_id, name, description, price, content) "
            "VALUES (?, ?, ?, ?, ?)",
            (category_id, name, description, price, content),
        )
        await db.commit()


async def get_products_by_category(category_id: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category_id = ?", (category_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_product(product_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ── Promo codes ────────────────────────────────────────────────────────────────

async def add_promo_code(code: str, amount: float, uses: int = 1) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, amount, uses_left) VALUES (?, ?, ?)",
            (code.upper(), amount, uses),
        )
        await db.commit()


async def get_promo_code(code: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code = ? AND uses_left > 0",
            (code.upper(),),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def use_promo_code(code: str) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?",
            (code.upper(),),
        )
        await db.commit()


async def get_all_promo_codes() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ── Transactions ───────────────────────────────────────────────────────────────

async def add_transaction(
    telegram_id: int, amount: float, tx_type: str, comment: str = ""
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO transactions (telegram_id, amount, type, comment) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, amount, tx_type, comment),
        )
        await db.commit()


# ── Email orders ───────────────────────────────────────────────────────────────

async def add_email_order(
    telegram_id: int, domain: str, email: str, password: str, order_id: str
) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO email_orders (telegram_id, domain, email, password, order_id, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (telegram_id, domain, email, password, order_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_email_order(order_db_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM email_orders WHERE id = ?", (order_db_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ── Product purchases ──────────────────────────────────────────────────────────

async def add_product_purchase(
    telegram_id: int, product_id: int, quantity: int, total_price: float
) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO product_purchases (telegram_id, product_id, quantity, total_price) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, product_id, quantity, total_price),
        )
        await db.commit()
