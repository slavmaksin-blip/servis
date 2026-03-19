import aiosqlite
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "database.db")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                sub_end TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                limit_uses INTEGER NOT NULL,
                used_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (code_id) REFERENCES promo_codes(id),
                UNIQUE(code_id, user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)
        # Each row = one unique stock unit (file) for a product.
        # Purchasing N units consumes N rows from this table.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS product_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(
    user_id: int, username: Optional[str], first_name: Optional[str]
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name),
        )
        await db.commit()


async def update_user_balance(user_id: int, delta: float) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (delta, user_id),
        )
        await db.commit()
        async with db.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0


async def update_user_sub(user_id: int, new_sub_end: datetime) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET sub_end = ? WHERE user_id = ?",
            (new_sub_end.isoformat(), user_id),
        )
        await db.commit()


async def ban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def unban_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_all_balances() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, balance FROM users ORDER BY balance DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_categories() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def add_category(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


async def delete_category(category_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        # Remove stock files first to avoid orphaned rows
        async with db.execute(
            "SELECT id FROM products WHERE category_id = ?", (category_id,)
        ) as cursor:
            product_ids = [row[0] for row in await cursor.fetchall()]
        for pid in product_ids:
            await db.execute(
                "DELETE FROM product_files WHERE product_id = ?", (pid,)
            )
        await db.execute(
            "DELETE FROM products WHERE category_id = ?", (category_id,)
        )
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()


async def get_products(category_id: int) -> list[dict]:
    """Return products with a computed 'stock' field."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT p.*, COUNT(pf.id) AS stock
            FROM products p
            LEFT JOIN product_files pf ON pf.product_id = p.id
            WHERE p.category_id = ?
            GROUP BY p.id
            """,
            (category_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_product(product_id: int) -> Optional[dict]:
    """Return product with a computed 'stock' field."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT p.*, COUNT(pf.id) AS stock
            FROM products p
            LEFT JOIN product_files pf ON pf.product_id = p.id
            WHERE p.id = ?
            GROUP BY p.id
            """,
            (product_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_product(
    category_id: int, name: str, description: str, price: float
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO products (category_id, name, description, price) VALUES (?, ?, ?, ?)",
            (category_id, name, description, price),
        )
        await db.commit()
        return cursor.lastrowid


async def delete_product(product_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM product_files WHERE product_id = ?", (product_id,)
        )
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def add_product_file(product_id: int, file_id: str) -> int:
    """Add one stock unit (file) to a product. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO product_files (product_id, file_id) VALUES (?, ?)",
            (product_id, file_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_product_stock(product_id: int) -> int:
    """Return the number of available stock units for a product."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM product_files WHERE product_id = ?", (product_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def pop_product_files(product_id: int, quantity: int) -> list[str]:
    """
    Atomically remove and return ``quantity`` file_ids from a product's stock.
    Returns an empty list if there are not enough stock units.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, file_id FROM product_files WHERE product_id = ? LIMIT ?",
            (product_id, quantity),
        ) as cursor:
            rows = await cursor.fetchall()

        if len(rows) < quantity:
            return []

        ids = [row[0] for row in rows]
        file_ids = [row[1] for row in rows]
        placeholders = ",".join("?" * len(ids))
        await db.execute(
            f"DELETE FROM product_files WHERE id IN ({placeholders})", ids
        )
        await db.commit()
        return file_ids


async def create_promo(code: str, amount: float, limit_uses: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, amount, limit_uses) VALUES (?, ?, ?)",
            (code, amount, limit_uses),
        )
        await db.commit()


async def get_promo(code: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code = ?", (code,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def delete_promo(promo_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_uses WHERE code_id = ?", (promo_id,))
        await db.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
        await db.commit()


async def use_promo(promo_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promo_uses (code_id, user_id) VALUES (?, ?)",
            (promo_id, user_id),
        )
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
            (promo_id,),
        )
        await db.commit()


async def has_used_promo(promo_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM promo_uses WHERE code_id = ? AND user_id = ?",
            (promo_id, user_id),
        ) as cursor:
            return await cursor.fetchone() is not None


async def log_purchase(
    user_id: int, product_id: int, quantity: int, total_price: float
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO purchases (user_id, product_id, quantity, total_price) VALUES (?, ?, ?, ?)",
            (user_id, product_id, quantity, total_price),
        )
        await db.commit()
