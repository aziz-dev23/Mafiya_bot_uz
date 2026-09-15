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
            games INTEGER NOT NULL DEFAULT 0,
            clan_id INTEGER,
            clan_role TEXT
        );

        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            tag TEXT NOT NULL UNIQUE,
            owner_id INTEGER NOT NULL,
            motto TEXT NOT NULL DEFAULT '',
            xp INTEGER NOT NULL DEFAULT 0,
            treasury_dollars INTEGER NOT NULL DEFAULT 0,
            treasury_diamonds INTEGER NOT NULL DEFAULT 0,
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
        """
    )
    await _conn.commit()
    await _ensure_column("users", "coins", "coins INTEGER NOT NULL DEFAULT 0")


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


async def get_clan(clan_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM clans WHERE clan_id = ?", (clan_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def get_clan_by_name_or_tag(value: str) -> aiosqlite.Row | None:
    cur = await _conn.execute(
        "SELECT * FROM clans WHERE name = ? COLLATE NOCASE OR tag = ? COLLATE NOCASE",
        (value, value),
    )
    row = await cur.fetchone()
    await cur.close()
    return row


async def get_user_clan(user_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute(
        "SELECT clans.* FROM clans JOIN users ON users.clan_id = clans.clan_id WHERE users.user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    await cur.close()
    return row


async def create_clan(name: str, tag: str, owner_id: int) -> int:
    cur = await _conn.execute(
        "INSERT INTO clans (name, tag, owner_id, created_at) VALUES (?, ?, ?, ?)",
        (name, tag, owner_id, int(time.time())),
    )
    clan_id = cur.lastrowid
    await _conn.execute(
        "UPDATE users SET clan_id = ?, clan_role = 'don' WHERE user_id = ?",
        (clan_id, owner_id),
    )
    await _conn.commit()
    return clan_id


async def add_member(clan_id: int, user_id: int, role: str = "member") -> None:
    await _conn.execute(
        "UPDATE users SET clan_id = ?, clan_role = ? WHERE user_id = ?",
        (clan_id, role, user_id),
    )
    await _conn.commit()


async def remove_member(user_id: int) -> None:
    await _conn.execute(
        "UPDATE users SET clan_id = NULL, clan_role = NULL WHERE user_id = ?",
        (user_id,),
    )
    await _conn.commit()


async def set_role(user_id: int, role: str) -> None:
    await _conn.execute("UPDATE users SET clan_role = ? WHERE user_id = ?", (role, user_id))
    await _conn.commit()


async def clan_members(clan_id: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM users WHERE clan_id = ? "
        "ORDER BY CASE clan_role WHEN 'don' THEN 0 WHEN 'deputy' THEN 1 ELSE 2 END, full_name",
        (clan_id,),
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def clan_member_count(clan_id: int) -> int:
    cur = await _conn.execute("SELECT COUNT(*) AS c FROM users WHERE clan_id = ?", (clan_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["c"]


async def donate_to_clan(user_id: int, clan_id: int, dollars: int, diamonds: int, xp: int) -> None:
    await _conn.execute(
        "UPDATE users SET dollars = dollars - ?, diamonds = diamonds - ? WHERE user_id = ?",
        (dollars, diamonds, user_id),
    )
    await _conn.execute(
        "UPDATE clans SET treasury_dollars = treasury_dollars + ?, "
        "treasury_diamonds = treasury_diamonds + ?, xp = xp + ? WHERE clan_id = ?",
        (dollars, diamonds, xp, clan_id),
    )
    await _conn.commit()


async def disband_clan(clan_id: int) -> None:
    await _conn.execute("UPDATE users SET clan_id = NULL, clan_role = NULL WHERE clan_id = ?", (clan_id,))
    await _conn.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
    await _conn.commit()


async def top_clans(limit: int = 10) -> list[aiosqlite.Row]:
    cur = await _conn.execute("SELECT * FROM clans ORDER BY xp DESC LIMIT ?", (limit,))
    rows = await cur.fetchall()
    await cur.close()
    return rows


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
