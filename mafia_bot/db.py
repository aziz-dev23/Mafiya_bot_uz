import time

import aiosqlite

from config import DB_PATH

_conn: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _conn
    _conn = await aiosqlite.connect(DB_PATH)
    _conn.row_factory = aiosqlite.Row
    await _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            dollars INTEGER NOT NULL DEFAULT 0,
            diamonds INTEGER NOT NULL DEFAULT 0,
            coins INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            games INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS points_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS diamond_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            price_som INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            sell_currency TEXT NOT NULL,
            sell_amount INTEGER NOT NULL,
            price_currency TEXT NOT NULL,
            price_amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER NOT NULL,
            item_key TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (user_id, item_key)
        );

        CREATE TABLE IF NOT EXISTS hero (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    await _conn.commit()
    await _ensure_column("users", "coins", "coins INTEGER NOT NULL DEFAULT 0")
    await _refund_legacy_hero_shot_items()


async def _refund_legacy_hero_shot_items() -> None:
    """Bir martalik migratsiya: bekor qilingan hero_shot buyumi zaxiralarini olmosga qaytaradi.
    Ikkinchi marta ishga tushganda count allaqachon 0 bo'lgani uchun hech narsa qilmaydi."""
    cur = await _conn.execute("SELECT user_id, count FROM inventory WHERE item_key = 'hero_shot' AND count > 0")
    rows = await cur.fetchall()
    await cur.close()
    if not rows:
        return
    for row in rows:
        refund = row["count"] * 90
        await _conn.execute(
            "UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (refund, row["user_id"])
        )
        await _conn.execute(
            "UPDATE inventory SET count = 0 WHERE user_id = ? AND item_key = 'hero_shot'", (row["user_id"],)
        )
    await _conn.commit()


async def _ensure_column(table: str, column: str, ddl: str) -> None:
    """Safety net so an existing mafia.db from before the coins column existed still works."""
    cur = await _conn.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in await cur.fetchall()]
    await cur.close()
    if column not in cols:
        await _conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        await _conn.commit()


async def close_db() -> None:
    if _conn:
        await _conn.close()


async def ensure_user(user_id: int, full_name: str, username: str | None) -> None:
    await _conn.execute(
        "INSERT INTO users (user_id, full_name, username) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name, username=excluded.username",
        (user_id, full_name, username),
    )
    await _conn.commit()


async def ensure_user_exists(user_id: int) -> None:
    """Insert a placeholder row only if the user is unknown; never overwrite an existing profile."""
    await _conn.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)",
        (user_id, str(user_id)),
    )
    await _conn.commit()


async def get_user(user_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def get_user_by_username(username: str) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def add_balance(user_id: int, dollars: int = 0, diamonds: int = 0, coins: int = 0) -> None:
    await _conn.execute(
        "UPDATE users SET dollars = dollars + ?, diamonds = diamonds + ?, coins = coins + ? WHERE user_id = ?",
        (dollars, diamonds, coins, user_id),
    )
    await _conn.commit()


async def record_game_result(user_id: int, won: bool) -> None:
    await _conn.execute(
        "UPDATE users SET games = games + 1, wins = wins + ? WHERE user_id = ?",
        (1 if won else 0, user_id),
    )
    await _conn.commit()


async def add_points(user_id: int, points: int) -> None:
    await _conn.execute(
        "INSERT INTO points_log (user_id, points, created_at) VALUES (?, ?, ?)",
        (user_id, points, int(time.time())),
    )
    await _conn.commit()


async def points_summary(user_id: int) -> dict[str, int]:
    now = int(time.time())
    cur = await _conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS daily, "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS weekly, "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS monthly, "
        "COALESCE(SUM(points), 0) AS total "
        "FROM points_log WHERE user_id = ?",
        (now - 86_400, now - 7 * 86_400, now - 30 * 86_400, user_id),
    )
    row = await cur.fetchone()
    await cur.close()
    return {"daily": row["daily"], "weekly": row["weekly"], "monthly": row["monthly"], "total": row["total"]}


async def top_points(since: int | None = None, limit: int = 10) -> list[aiosqlite.Row]:
    """Reyting: `since` bo'lsa shu unix-vaqtdan beri, aks holda umumiy ball bo'yicha TOP."""
    if since is None:
        cur = await _conn.execute(
            "SELECT points_log.user_id AS user_id, users.full_name AS full_name, SUM(points_log.points) AS total "
            "FROM points_log JOIN users ON users.user_id = points_log.user_id "
            "GROUP BY points_log.user_id ORDER BY total DESC LIMIT ?",
            (limit,),
        )
    else:
        cur = await _conn.execute(
            "SELECT points_log.user_id AS user_id, users.full_name AS full_name, SUM(points_log.points) AS total "
            "FROM points_log JOIN users ON users.user_id = points_log.user_id "
            "WHERE points_log.created_at >= ? GROUP BY points_log.user_id ORDER BY total DESC LIMIT ?",
            (since, limit),
        )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def get_hero_level(user_id: int) -> int:
    cur = await _conn.execute("SELECT level FROM hero WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["level"] if row else 0


async def set_hero_level(user_id: int, level: int) -> None:
    await _conn.execute(
        "INSERT INTO hero (user_id, level) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET level = excluded.level",
        (user_id, level),
    )
    await _conn.commit()


async def create_order(user_id: int, amount: int, price_som: int) -> int:
    cur = await _conn.execute(
        "INSERT INTO diamond_orders (user_id, amount, price_som, created_at) VALUES (?, ?, ?, ?)",
        (user_id, amount, price_som, int(time.time())),
    )
    await _conn.commit()
    return cur.lastrowid


async def get_order(order_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM diamond_orders WHERE order_id = ?", (order_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def set_order_status(order_id: int, status: str) -> None:
    await _conn.execute("UPDATE diamond_orders SET status = ? WHERE order_id = ?", (status, order_id))
    await _conn.commit()


async def create_listing(seller_id: int, sell_currency: str, sell_amount: int, price_currency: str, price_amount: int) -> int:
    cur = await _conn.execute(
        "INSERT INTO market_listings "
        "(seller_id, sell_currency, sell_amount, price_currency, price_amount, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (seller_id, sell_currency, sell_amount, price_currency, price_amount, int(time.time())),
    )
    await _conn.commit()
    return cur.lastrowid


async def get_listing(listing_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM market_listings WHERE listing_id = ?", (listing_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def active_listings() -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM market_listings WHERE status = 'active' ORDER BY created_at"
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def seller_listings(seller_id: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM market_listings WHERE seller_id = ? AND status = 'active' ORDER BY created_at",
        (seller_id,),
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def transition_listing(listing_id: int, to_status: str) -> bool:
    """Atomically move a listing out of 'active' so two buyers can't both claim it."""
    cur = await _conn.execute(
        "UPDATE market_listings SET status = ? WHERE listing_id = ? AND status = 'active'",
        (to_status, listing_id),
    )
    await _conn.commit()
    return cur.rowcount > 0


async def add_item(user_id: int, item_key: str, qty: int = 1) -> None:
    await _conn.execute(
        "INSERT INTO inventory (user_id, item_key, count) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, item_key) DO UPDATE SET count = count + excluded.count",
        (user_id, item_key, qty),
    )
    await _conn.commit()


async def get_inventory(user_id: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM inventory WHERE user_id = ? AND count > 0 ORDER BY item_key", (user_id,)
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def consume_item(user_id: int, item_key: str) -> bool:
    """Atomically spend one unit of an item; returns False if none was available."""
    cur = await _conn.execute(
        "UPDATE inventory SET count = count - 1 WHERE user_id = ? AND item_key = ? AND count > 0",
        (user_id, item_key),
    )
    await _conn.commit()
    return cur.rowcount > 0


async def set_item_enabled(user_id: int, item_key: str, enabled: bool) -> None:
    await _conn.execute(
        "INSERT INTO inventory (user_id, item_key, count, enabled) VALUES (?, ?, 0, ?) "
        "ON CONFLICT(user_id, item_key) DO UPDATE SET enabled = excluded.enabled",
        (user_id, item_key, int(enabled)),
    )
    await _conn.commit()


async def get_enabled_items(user_id: int) -> dict[str, int]:
    cur = await _conn.execute(
        "SELECT item_key, count FROM inventory WHERE user_id = ? AND enabled = 1 AND count > 0",
        (user_id,),
    )
    rows = await cur.fetchall()
    await cur.close()
    return {row["item_key"]: row["count"] for row in rows}
