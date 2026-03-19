import aiosqlite
from config import DATABASE_URL


async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                tg_id       INTEGER UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                balance     REAL DEFAULT 0.0,
                sub_end     TEXT,
                is_banned   INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                name        TEXT NOT NULL,
                description TEXT,
                price       REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                file_id     TEXT NOT NULL,
                file_name   TEXT,
                sold        INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                quantity    INTEGER NOT NULL,
                total       REAL NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mail_orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                domain      TEXT NOT NULL,
                email       TEXT,
                price       REAL NOT NULL,
                external_id TEXT,
                status      TEXT DEFAULT 'pending',
                full_data   TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                code            TEXT UNIQUE NOT NULL,
                amount          REAL NOT NULL,
                max_uses        INTEGER NOT NULL,
                used_count      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS promo_activations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                promo_id    INTEGER NOT NULL REFERENCES promo_codes(id),
                UNIQUE(tg_id, promo_id)
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id           INTEGER NOT NULL,
                invoice_id      TEXT UNIQUE NOT NULL,
                amount          REAL NOT NULL,
                payment_system  TEXT NOT NULL,
                credited        INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()


# ──────────────────────── USER ────────────────────────

async def get_user(tg_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def register_user(tg_id: int, username: str, full_name: str) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
            (tg_id, username, full_name),
        )
        await db.commit()


async def update_balance(tg_id: int, delta: float) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE tg_id = ?",
            (delta, tg_id),
        )
        await db.commit()


async def set_balance(tg_id: int, amount: float) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET balance = ? WHERE tg_id = ?",
            (amount, tg_id),
        )
        await db.commit()


async def set_subscription(tg_id: int, sub_end: str) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET sub_end = ? WHERE tg_id = ?",
            (sub_end, tg_id),
        )
        await db.commit()


async def ban_user(tg_id: int) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE tg_id = ?", (tg_id,)
        )
        await db.commit()


async def unban_user(tg_id: int) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE tg_id = ?", (tg_id,)
        )
        await db.commit()


async def get_user_by_username(username: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uname = username.lstrip("@")
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (uname,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_active_users() -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE balance > 0 OR (sub_end IS NOT NULL AND sub_end > datetime('now'))"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ──────────────────────── CATEGORIES ────────────────────────

async def get_categories() -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def add_category(name: str) -> int:
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


async def delete_category(cat_id: int) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        await db.commit()


# ──────────────────────── PRODUCTS ────────────────────────

async def get_products(category_id: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE category_id = ?", (category_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_product(product_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_product(
    category_id: int, name: str, description: str, price: float
) -> int:
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "INSERT INTO products (category_id, name, description, price) VALUES (?, ?, ?, ?)",
            (category_id, name, description, price),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_product(product_id: int) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("DELETE FROM stock_items WHERE product_id = ?", (product_id,))
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def get_stock_count(product_id: int) -> int:
    async with aiosqlite.connect(DATABASE_URL) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM stock_items WHERE product_id = ? AND sold = 0",
            (product_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def add_stock_item(product_id: int, file_id: str, file_name: str) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO stock_items (product_id, file_id, file_name) VALUES (?, ?, ?)",
            (product_id, file_id, file_name),
        )
        await db.commit()


async def take_stock_items(product_id: int, quantity: int) -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? AND sold = 0 LIMIT ?",
            (product_id, quantity),
        ) as cursor:
            rows = await cursor.fetchall()
        if len(rows) < quantity:
            return []
        ids = [r["id"] for r in rows]
        placeholders = ",".join(["?"] * len(ids))
        await db.execute(
            f"UPDATE stock_items SET sold = 1 WHERE id IN ({placeholders})",
            ids,
        )
        await db.commit()
        return [dict(r) for r in rows]


# ──────────────────────── ORDERS ────────────────────────

async def create_order(tg_id: int, product_id: int, quantity: int, total: float) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO orders (tg_id, product_id, quantity, total) VALUES (?, ?, ?, ?)",
            (tg_id, product_id, quantity, total),
        )
        await db.commit()


# ──────────────────────── MAIL ORDERS ────────────────────────

async def create_mail_order(
    tg_id: int, domain: str, email: str, price: float,
    external_id: str, full_data: str
) -> int:
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            """INSERT INTO mail_orders
               (tg_id, domain, email, price, external_id, full_data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tg_id, domain, email, price, external_id, full_data),
        )
        await db.commit()
        return cursor.lastrowid


async def get_mail_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mail_orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_mail_order(order_id: int, status: str, full_data: str) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "UPDATE mail_orders SET status = ?, full_data = ? WHERE id = ?",
            (status, full_data, order_id),
        )
        await db.commit()


# ──────────────────────── PROMO CODES ────────────────────────

async def get_promo(code: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code = ?", (code,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def activate_promo(tg_id: int, promo_id: int) -> bool:
    """Returns True if activation succeeded, False if already used."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            await db.execute(
                "INSERT INTO promo_activations (tg_id, promo_id) VALUES (?, ?)",
                (tg_id, promo_id),
            )
            await db.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
                (promo_id,),
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            return False
        # Remove promo if max uses exhausted
        async with db.execute(
            "SELECT used_count, max_uses FROM promo_codes WHERE id = ?", (promo_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] >= row[1]:
                await db.execute(
                    "DELETE FROM promo_codes WHERE id = ?", (promo_id,)
                )
                await db.commit()
        return True


async def create_promo(code: str, amount: float, max_uses: int) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, amount, max_uses) VALUES (?, ?, ?)",
            (code, amount, max_uses),
        )
        await db.commit()


async def get_all_promos() -> list[dict]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ──────────────────────── INVOICES ────────────────────────

async def create_invoice(
    tg_id: int, invoice_id: str, amount: float, payment_system: str
) -> None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute(
            """INSERT OR IGNORE INTO invoices
               (tg_id, invoice_id, amount, payment_system)
               VALUES (?, ?, ?, ?)""",
            (tg_id, invoice_id, amount, payment_system),
        )
        await db.commit()


async def get_invoice(invoice_id: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_invoice_credited(invoice_id: str) -> bool:
    """Returns True if marked, False if already credited (double-credit guard)."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "UPDATE invoices SET credited = 1 WHERE invoice_id = ? AND credited = 0",
            (invoice_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
