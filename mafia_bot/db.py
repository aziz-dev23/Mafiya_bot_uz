import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone

import aiosqlite

from config import DB_PATH, TIMEZONE_OFFSET_HOURS

_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))

_conn: aiosqlite.Connection | None = None
logger = logging.getLogger(__name__)


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

        CREATE TABLE IF NOT EXISTS migrations (
            name TEXT PRIMARY KEY,
            applied_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weekly_rewards (
            week_start INTEGER PRIMARY KEY,
            paid_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            currency TEXT NOT NULL,
            amount INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_transfers_sender ON transfers (sender_id, created_at);

        -- Telegram Stars to'lovlari. charge_id — Telegram'ning telegram_payment_charge_id si:
        -- PRIMARY KEY bo'lgani uchun bitta to'lov ikki marta hisoblanmaydi.
        CREATE TABLE IF NOT EXISTS star_payments (
            charge_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            diamonds INTEGER NOT NULL,
            stars INTEGER NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'paid',
            created_at INTEGER NOT NULL,
            refunded_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_star_payments_user ON star_payments (user_id, created_at);

        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            settings TEXT NOT NULL
        );

        -- Har bir rol bo'yicha o'yinlar va g'alabalar (/profile statistikasi uchun).
        CREATE TABLE IF NOT EXISTS role_stats (
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            games INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, role)
        );

        -- Tunda yopilgan guruhlarning asl ruxsatlari (bot qayta ishga tushsa tiklash uchun).
        CREATE TABLE IF NOT EXISTS chat_locks (
            chat_id INTEGER PRIMARY KEY,
            permissions TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """
    )
    await _conn.commit()
    await _ensure_column("users", "coins", "coins INTEGER NOT NULL DEFAULT 0")
    await _refund_legacy_hero_shot_items()
    await _run_migrations()


async def _migrate_killer_shield_x10() -> None:
    """⛑ Qotildan himoya endi sarflanadi: avval (cheksiz) sotib olingan har bir dona 10 donaga aylanadi."""
    await _conn.execute("UPDATE inventory SET count = count * 10 WHERE item_key = 'killer_shield' AND count > 0")


async def _migrate_users_lang() -> None:
    """Foydalanuvchi tili ustuni (i18n). Mavjud foydalanuvchilar uchun — o'zbekcha (lotin)."""
    cur = await _conn.execute("PRAGMA table_info(users)")
    cols = [row["name"] for row in await cur.fetchall()]
    await cur.close()
    if "lang" not in cols:
        await _conn.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'uz'")


# Tartib muhim: yangi migratsiyalar faqat ro'yxat oxiriga qo'shiladi.
_MIGRATIONS = (
    ("2026_09_killer_shield_x10", _migrate_killer_shield_x10),
    ("2026_10_users_lang", _migrate_users_lang),
)


async def _run_migrations() -> None:
    """Har bir migratsiya bir marta ishlaydi. Birinchi yangi migratsiyadan oldin baza fayli nusxalanadi."""
    cur = await _conn.execute("SELECT name FROM migrations")
    applied = {row["name"] for row in await cur.fetchall()}
    await cur.close()
    pending = [(name, fn) for name, fn in _MIGRATIONS if name not in applied]
    if not pending:
        return

    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup-{datetime.now(_TZ).strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(DB_PATH, backup_path)
        logger.info("Migratsiyadan oldin baza nusxalandi: %s", backup_path)

    for name, fn in pending:
        await fn()
        await _conn.execute("INSERT INTO migrations (name, applied_at) VALUES (?, ?)", (name, int(time.time())))
        await _conn.commit()
        logger.info("Migratsiya bajarildi: %s", name)


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


_BALANCE_COLUMNS = {"dollars", "diamonds", "coins"}


async def spend_balance(user_id: int, column: str, amount: int) -> bool:
    """Balansdan atomik ayiradi: mablag' yetarli bo'lmasa hech narsa o'zgarmaydi va False qaytadi.
    Tekshiruv va ayirish bitta SQL so'rovda — tugmani tez-tez bosish balansni minusga tushira olmaydi."""
    if column not in _BALANCE_COLUMNS or amount <= 0:
        raise ValueError(f"invalid spend: {column}={amount}")
    cur = await _conn.execute(
        f"UPDATE users SET {column} = {column} - ? WHERE user_id = ? AND {column} >= ?",
        (amount, user_id, amount),
    )
    await _conn.commit()
    return cur.rowcount > 0


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


def period_starts() -> dict[str, int]:
    """Kalendar davrlari boshlanishi (unix-vaqt): bugun 00:00, shu hafta dushanba 00:00, oyning 1-sanasi 00:00."""
    today = datetime.now(_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=today.weekday())
    month = today.replace(day=1)
    return {"daily": int(today.timestamp()), "weekly": int(week.timestamp()), "monthly": int(month.timestamp())}


async def points_summary(user_id: int) -> dict[str, int]:
    starts = period_starts()
    cur = await _conn.execute(
        "SELECT "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS daily, "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS weekly, "
        "COALESCE(SUM(CASE WHEN created_at >= ? THEN points END), 0) AS monthly, "
        "COALESCE(SUM(points), 0) AS total "
        "FROM points_log WHERE user_id = ?",
        (starts["daily"], starts["weekly"], starts["monthly"], user_id),
    )
    row = await cur.fetchone()
    await cur.close()
    return {"daily": row["daily"], "weekly": row["weekly"], "monthly": row["monthly"], "total": row["total"]}


async def top_points(since: int | None = None, limit: int = 10, until: int | None = None) -> list[aiosqlite.Row]:
    """Reyting: `since` bo'lsa shu unix-vaqtdan beri (`until` bo'lsa undan oldingacha), aks holda umumiy TOP."""
    if until is not None:
        cur = await _conn.execute(
            "SELECT points_log.user_id AS user_id, users.full_name AS full_name, SUM(points_log.points) AS total "
            "FROM points_log JOIN users ON users.user_id = points_log.user_id "
            "WHERE points_log.created_at >= ? AND points_log.created_at < ? "
            "GROUP BY points_log.user_id ORDER BY total DESC, points_log.user_id LIMIT ?",
            (since or 0, until, limit),
        )
    elif since is None:
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


async def create_hero(user_id: int) -> bool:
    """Geroyni 1-daraja bilan yaratadi; allaqachon bo'lsa False qaytaradi."""
    cur = await _conn.execute("INSERT OR IGNORE INTO hero (user_id, level) VALUES (?, 1)", (user_id,))
    await _conn.commit()
    return cur.rowcount > 0


async def increment_hero_level(user_id: int) -> int | None:
    """Darajani atomik +1 qiladi va yangi darajani qaytaradi (Geroy bo'lmasa None)."""
    cur = await _conn.execute("UPDATE hero SET level = level + 1 WHERE user_id = ? AND level > 0", (user_id,))
    await _conn.commit()
    if cur.rowcount == 0:
        return None
    return await get_hero_level(user_id)


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


async def pay_weekly_rewards(week_start: int, awards: list[tuple[int, int]]) -> bool:
    """Hafta mukofotini bir marta beradi: (user_id, olmos) ro'yxati. Shu hafta uchun allaqachon
    berilgan bo'lsa False qaytaradi va hech narsa o'zgarmaydi. Belgi va balanslar bitta commit'da yoziladi."""
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO weekly_rewards (week_start, paid_at) VALUES (?, ?)", (week_start, int(time.time()))
    )
    if cur.rowcount == 0:
        return False
    for user_id, diamonds in awards:
        await _conn.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (diamonds, user_id))
    await _conn.commit()
    return True


async def transfer_balance(sender_id: int, recipient_id: int, currency: str, column: str, amount: int) -> bool:
    """Yuboruvchidan atomik ayirib, qabul qiluvchiga qo'shadi va jurnalga yozadi."""
    if not await spend_balance(sender_id, column, amount):
        return False
    await _conn.execute(
        f"UPDATE users SET {column} = {column} + ? WHERE user_id = ?", (amount, recipient_id)
    )
    await _conn.execute(
        "INSERT INTO transfers (sender_id, recipient_id, currency, amount, created_at) VALUES (?, ?, ?, ?, ?)",
        (sender_id, recipient_id, currency, amount, int(time.time())),
    )
    await _conn.commit()
    return True


async def sent_today(sender_id: int, currency: str) -> int:
    """Bugun (Toshkent vaqti bilan 00:00 dan) yuborilgan jami miqdor."""
    cur = await _conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transfers WHERE sender_id = ? AND currency = ? AND created_at >= ?",
        (sender_id, currency, period_starts()["daily"]),
    )
    row = await cur.fetchone()
    await cur.close()
    return row["total"]


async def save_chat_lock(chat_id: int, permissions_json: str) -> bool:
    """Asl ruxsatlarni saqlaydi. Allaqachon saqlangan bo'lsa (yopiq guruhning ruxsatlarini
    asl deb yozib qo'ymaslik uchun) o'zgartirmaydi va False qaytaradi."""
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO chat_locks (chat_id, permissions, created_at) VALUES (?, ?, ?)",
        (chat_id, permissions_json, int(time.time())),
    )
    await _conn.commit()
    return cur.rowcount > 0


async def get_chat_lock(chat_id: int) -> str | None:
    cur = await _conn.execute("SELECT permissions FROM chat_locks WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["permissions"] if row else None


async def delete_chat_lock(chat_id: int) -> None:
    await _conn.execute("DELETE FROM chat_locks WHERE chat_id = ?", (chat_id,))
    await _conn.commit()


async def all_chat_locks() -> list[aiosqlite.Row]:
    cur = await _conn.execute("SELECT chat_id, permissions FROM chat_locks")
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def get_group_settings(chat_id: int) -> str | None:
    cur = await _conn.execute("SELECT settings FROM group_settings WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["settings"] if row else None


async def set_group_settings(chat_id: int, settings_json: str) -> None:
    await _conn.execute(
        "INSERT INTO group_settings (chat_id, settings) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET settings = excluded.settings",
        (chat_id, settings_json),
    )
    await _conn.commit()


async def all_group_settings() -> list[aiosqlite.Row]:
    cur = await _conn.execute("SELECT chat_id, settings FROM group_settings")
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def record_role_result(user_id: int, role: str, won: bool) -> None:
    await _conn.execute(
        "INSERT INTO role_stats (user_id, role, games, wins) VALUES (?, ?, 1, ?) "
        "ON CONFLICT(user_id, role) DO UPDATE SET games = games + 1, wins = wins + excluded.wins",
        (user_id, role, 1 if won else 0),
    )
    await _conn.commit()


async def get_role_stats(user_id: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT role, games, wins FROM role_stats WHERE user_id = ? ORDER BY games DESC", (user_id,)
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def points_rank(user_id: int, since: int | None = None) -> tuple[int, int] | None:
    """Foydalanuvchining reytingdagi o'rni va bali; shu davrda bali bo'lmasa None."""
    since = since or 0
    cur = await _conn.execute(
        "SELECT SUM(points) AS total FROM points_log WHERE user_id = ? AND created_at >= ?", (user_id, since)
    )
    row = await cur.fetchone()
    await cur.close()
    if not row or row["total"] is None:
        return None
    total = row["total"]
    cur = await _conn.execute(
        "SELECT COUNT(*) AS higher FROM (SELECT user_id, SUM(points) AS t FROM points_log "
        "WHERE created_at >= ? GROUP BY user_id) WHERE t > ?",
        (since, total),
    )
    higher = (await cur.fetchone())["higher"]
    await cur.close()
    return higher + 1, total


async def record_star_payment(charge_id: str, user_id: int, diamonds: int, stars: int, payload: str) -> bool:
    """To'lovni saqlaydi va olmosni qo'shadi (bitta commit'da). Shu charge_id allaqachon
    bo'lsa (Telegram update'ni qayta yuborgan) hech narsa qilmaydi va False qaytaradi."""
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO star_payments (charge_id, user_id, diamonds, stars, payload, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (charge_id, user_id, diamonds, stars, payload, int(time.time())),
    )
    if cur.rowcount == 0:
        return False
    await _conn.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (diamonds, user_id))
    await _conn.commit()
    return True


async def get_star_payment(charge_id: str) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT * FROM star_payments WHERE charge_id = ?", (charge_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def user_star_payments(user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM star_payments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def set_star_payment_status(charge_id: str, from_status: str, to_status: str) -> bool:
    """Holatni atomik o'zgartiradi (masalan paid -> refunded); boshqa holatda bo'lsa False."""
    cur = await _conn.execute(
        "UPDATE star_payments SET status = ?, refunded_at = CASE WHEN ? = 'refunded' THEN ? ELSE refunded_at END "
        "WHERE charge_id = ? AND status = ?",
        (to_status, to_status, int(time.time()), charge_id, from_status),
    )
    await _conn.commit()
    return cur.rowcount > 0


async def take_diamonds(user_id: int, amount: int, allow_partial: bool) -> int | None:
    """Pul qaytarilganda olmosni balansdan oladi. Yetarli bo'lmasa: allow_partial=False — None
    (hech narsa o'zgarmaydi), True — bor olmosni oladi. Olingan miqdorni qaytaradi."""
    if await spend_balance(user_id, "diamonds", amount):
        return amount
    if not allow_partial:
        return None
    row = await get_user(user_id)
    available = max(0, row["diamonds"]) if row else 0
    if available and not await spend_balance(user_id, "diamonds", available):
        return 0
    return available


async def set_user_lang(user_id: int, lang: str) -> None:
    await _conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    await _conn.commit()
