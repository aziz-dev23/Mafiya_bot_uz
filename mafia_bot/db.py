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


async def _migrate_cosmetics_season() -> None:
    """7-bosqich: kosmetika (egalik va faol tanlov) va mavsum chiptasi progressi."""
    await _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cosmetics_owned (
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            expires_at INTEGER,
            acquired_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, key)
        );
        -- prev_key: vaqtinchalik unvon (Hafta chempioni) tugagach qaytariladigan oldingi unvon.
        CREATE TABLE IF NOT EXISTS cosmetics_active (
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            key TEXT NOT NULL,
            prev_key TEXT,
            PRIMARY KEY (user_id, kind)
        );
        -- rewarded_*: mukofoti berilgan eng yuqori daraja (qayta berilmasligi uchun).
        CREATE TABLE IF NOT EXISTS season_progress (
            user_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            premium INTEGER NOT NULL DEFAULT 0,
            rewarded_free INTEGER NOT NULL DEFAULT 0,
            rewarded_premium INTEGER NOT NULL DEFAULT 0,
            last_xp_day TEXT,
            reminded INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, season)
        );
        """
    )


async def _migrate_bonus_vip_logs() -> None:
    """7-bosqich: kunlik bonus, VIP obuna va o'yinlar jurnali (VIP tarixi, guruh statistikasi uchun)."""
    await _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_bonus (
            user_id INTEGER PRIMARY KEY,
            last_day TEXT NOT NULL,
            streak INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vip (
            user_id INTEGER PRIMARY KEY,
            until INTEGER NOT NULL,
            charge_id TEXT
        );
        -- Har dushanba beriladigan bepul buyum ikki marta berilmasligi uchun.
        CREATE TABLE IF NOT EXISTS vip_weekly_items (
            user_id INTEGER NOT NULL,
            week_start INTEGER NOT NULL,
            PRIMARY KEY (user_id, week_start)
        );
        CREATE TABLE IF NOT EXISTS game_results (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            winner TEXT NOT NULL,
            players INTEGER NOT NULL,
            ended_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS game_log (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            won INTEGER NOT NULL,
            alive INTEGER NOT NULL,
            afk INTEGER NOT NULL,
            points INTEGER NOT NULL,
            ended_at INTEGER NOT NULL,
            PRIMARY KEY (game_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_game_log_user ON game_log (user_id, ended_at);
        CREATE INDEX IF NOT EXISTS idx_game_log_chat ON game_log (chat_id, ended_at);
        CREATE INDEX IF NOT EXISTS idx_game_results_chat ON game_results (chat_id, ended_at);
        -- Stars to'lovi bilan (asosiy olmosdan tashqari) berilgan narsalar: pul qaytarilsa hammasi
        -- shu jurnal bo'yicha qaytarib olinadi. kind: diamond, item, vip, cosmetic, share.
        CREATE TABLE IF NOT EXISTS payment_grants (
            charge_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            key TEXT,
            amount INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_payment_grants_charge ON payment_grants (charge_id);
        -- payer_id: to'lagan kishi (sovg'ada olmos boshqa odamga — user_id ga tushadi); kind: to'lov turi.
        ALTER TABLE star_payments ADD COLUMN payer_id INTEGER;
        ALTER TABLE star_payments ADD COLUMN kind TEXT NOT NULL DEFAULT 'diamonds';
        """
    )


async def _migrate_purchases_groups() -> None:
    """7-bosqich: guruh egasi ulushi, do'st takliflari, guruh premiumi, haftalik statistika, turnirlar."""
    await _conn.executescript(
        """
        -- Ulush milli-olmosda yig'iladi (1000 = 1💎); manfiy bo'lishi mumkin (qaytarilgan xarid).
        CREATE TABLE IF NOT EXISTS owner_share (
            user_id INTEGER PRIMARY KEY,
            millis INTEGER NOT NULL DEFAULT 0
        );
        -- Guruh yaratuvchisi ulushni boshqa adminga o'tkazsa — shu yerda.
        CREATE TABLE IF NOT EXISTS group_owner (
            chat_id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS referrals (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER NOT NULL,
            rewarded INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS group_premium (
            chat_id INTEGER PRIMARY KEY,
            until INTEGER NOT NULL,
            payer_id INTEGER,
            charge_id TEXT
        );
        CREATE TABLE IF NOT EXISTS group_weekly_stats (
            chat_id INTEGER NOT NULL,
            week_start INTEGER NOT NULL,
            PRIMARY KEY (chat_id, week_start)
        );
        -- Guruh unvoni ("🏰 <nom>") uchun guruh nomi (o'yin paytida yangilanadi).
        CREATE TABLE IF NOT EXISTS group_chats (
            chat_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            games_total INTEGER NOT NULL,
            games_played INTEGER NOT NULL DEFAULT 0,
            prize INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tournaments_chat ON tournaments (chat_id, status);
        CREATE TABLE IF NOT EXISTS tournament_scores (
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (tournament_id, user_id)
        );
        """
    )


# Tartib muhim: yangi migratsiyalar faqat ro'yxat oxiriga qo'shiladi.
_MIGRATIONS = (
    ("2026_09_killer_shield_x10", _migrate_killer_shield_x10),
    ("2026_10_users_lang", _migrate_users_lang),
    ("2026_10_cosmetics_season", _migrate_cosmetics_season),
    ("2026_10_bonus_vip_logs", _migrate_bonus_vip_logs),
    ("2026_10_purchases_groups", _migrate_purchases_groups),
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
    """Reyting: `since` bo'lsa shu unix-vaqtdan beri (`until` bo'lsa undan oldingacha), aks holda umumiy TOP.
    Har bir qatorda Geroy darajasi ham qaytadi (🦸N belgisi uchun)."""
    cur = await _conn.execute(
        "SELECT points_log.user_id AS user_id, users.full_name AS full_name, SUM(points_log.points) AS total, "
        "COALESCE(hero.level, 0) AS hero_level "
        "FROM points_log JOIN users ON users.user_id = points_log.user_id "
        "LEFT JOIN hero ON hero.user_id = points_log.user_id "
        "WHERE points_log.created_at >= ? AND points_log.created_at < ? "
        "GROUP BY points_log.user_id ORDER BY total DESC, points_log.user_id LIMIT ?",
        (since or 0, until if until is not None else 2**62, limit),
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


async def record_star_payment(
    charge_id: str,
    user_id: int,
    diamonds: int,
    stars: int,
    payload: str,
    payer_id: int | None = None,
    kind: str = "diamonds",
) -> bool:
    """To'lovni saqlaydi va olmosni user_id ga qo'shadi (bitta commit'da). Shu charge_id allaqachon
    bo'lsa (Telegram update'ni qayta yuborgan) hech narsa qilmaydi va False qaytaradi.
    payer_id — to'lagan kishi (sovg'ada user_id dan farq qiladi), kind — to'lov turi."""
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO star_payments (charge_id, user_id, diamonds, stars, payload, created_at, payer_id, kind) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (charge_id, user_id, diamonds, stars, payload, int(time.time()), payer_id or user_id, kind),
    )
    if cur.rowcount == 0:
        return False
    if diamonds:
        await _conn.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (diamonds, user_id))
    await _conn.commit()
    return True


async def add_payment_grant(charge_id: str, user_id: int, kind: str, key: str | None = None, amount: int = 0) -> None:
    await _conn.execute(
        "INSERT INTO payment_grants (charge_id, user_id, kind, key, amount) VALUES (?, ?, ?, ?, ?)",
        (charge_id, user_id, kind, key, amount),
    )
    await _conn.commit()


async def payment_grants(charge_id: str) -> list[aiosqlite.Row]:
    cur = await _conn.execute("SELECT * FROM payment_grants WHERE charge_id = ?", (charge_id,))
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def take_item(user_id: int, item_key: str, count: int) -> int:
    """Buyumni qaytarib oladi (bor miqdordan ko'p emas). Olingan sonni qaytaradi."""
    have = await item_count(user_id, item_key)
    taken = min(have, count)
    if taken:
        await _conn.execute(
            "UPDATE inventory SET count = count - ? WHERE user_id = ? AND item_key = ?", (taken, user_id, item_key)
        )
        await _conn.commit()
    return taken


async def revoke_cosmetic(user_id: int, key: str) -> None:
    await _conn.execute("DELETE FROM cosmetics_owned WHERE user_id = ? AND key = ?", (user_id, key))
    await _conn.execute("DELETE FROM cosmetics_active WHERE user_id = ? AND key = ?", (user_id, key))
    await _conn.commit()


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


async def item_count(user_id: int, item_key: str) -> int:
    cur = await _conn.execute("SELECT count FROM inventory WHERE user_id = ? AND item_key = ?", (user_id, item_key))
    row = await cur.fetchone()
    await cur.close()
    return row["count"] if row else 0


# ---------- 🎨 Kosmetika ----------


async def grant_cosmetic(user_id: int, key: str, expires_at: int | None = None) -> bool:
    """Kosmetikani beradi. Doimiy narsa allaqachon bo'lsa False (qayta sotib olinmaydi);
    vaqtinchalik (expires_at) bo'lsa muddati yangilanadi."""
    if expires_at is None:
        cur = await _conn.execute(
            "INSERT OR IGNORE INTO cosmetics_owned (user_id, key, expires_at, acquired_at) VALUES (?, ?, NULL, ?)",
            (user_id, key, int(time.time())),
        )
        await _conn.commit()
        return cur.rowcount > 0
    await _conn.execute(
        "INSERT INTO cosmetics_owned (user_id, key, expires_at, acquired_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET expires_at = excluded.expires_at",
        (user_id, key, expires_at, int(time.time())),
    )
    await _conn.commit()
    return True


GROUP_TITLE_PREFIX = "group:"


async def owned_cosmetics(user_id: int) -> set[str]:
    """Muddati o'tmagan barcha kosmetika kalitlari. Guruh unvonlari ("group:<chat_id>") faqat shu
    guruhning premiumi faol bo'lganda hisoblanadi (premium yangilansa, unvon qaytadi)."""
    now = int(time.time())
    cur = await _conn.execute(
        "SELECT key FROM cosmetics_owned WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)",
        (user_id, now),
    )
    rows = await cur.fetchall()
    await cur.close()
    keys = set()
    for row in rows:
        key = row["key"]
        if key.startswith(GROUP_TITLE_PREFIX):
            chat_id = int(key[len(GROUP_TITLE_PREFIX):])
            if await group_premium_until(chat_id) <= now:
                continue
        keys.add(key)
    return keys


async def set_active_cosmetic(user_id: int, kind: str, key: str | None, prev_key: str | None = None) -> None:
    if key is None:
        await _conn.execute("DELETE FROM cosmetics_active WHERE user_id = ? AND kind = ?", (user_id, kind))
    else:
        await _conn.execute(
            "INSERT INTO cosmetics_active (user_id, kind, key, prev_key) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, kind) DO UPDATE SET key = excluded.key, prev_key = excluded.prev_key",
            (user_id, kind, key, prev_key),
        )
    await _conn.commit()


async def active_cosmetics(user_id: int) -> dict[str, str]:
    """Faol kosmetika {tur: kalit}. Faol narsaning muddati o'tgan bo'lsa (Hafta chempioni),
    oldingi tanlov (prev_key) qaytariladi va bazada tiklanadi."""
    owned = await owned_cosmetics(user_id)
    cur = await _conn.execute("SELECT kind, key, prev_key FROM cosmetics_active WHERE user_id = ?", (user_id,))
    rows = await cur.fetchall()
    await cur.close()
    active = {}
    for row in rows:
        if row["key"] in owned:
            active[row["kind"]] = row["key"]
            continue
        if row["key"].startswith(GROUP_TITLE_PREFIX):
            continue  # premium tugagan — unvonsiz ko'rinadi, lekin tanlov saqlanadi
        restored = row["prev_key"] if row["prev_key"] in owned else None
        await set_active_cosmetic(user_id, row["kind"], restored)
        if restored:
            active[row["kind"]] = restored
    return active


async def activate_temporary_cosmetic(user_id: int, kind: str, key: str) -> None:
    """Vaqtinchalik narsani faollashtiradi; hozirgi tanlov prev_key sifatida saqlanadi."""
    cur = await _conn.execute(
        "SELECT key, prev_key FROM cosmetics_active WHERE user_id = ? AND kind = ?", (user_id, kind)
    )
    row = await cur.fetchone()
    await cur.close()
    prev = None
    if row:
        prev = row["prev_key"] if row["key"] == key else row["key"]
    await set_active_cosmetic(user_id, kind, key, prev)


# ---------- 🎟 Mavsum ----------


async def season_progress(user_id: int, season: int) -> aiosqlite.Row | None:
    cur = await _conn.execute(
        "SELECT * FROM season_progress WHERE user_id = ? AND season = ?", (user_id, season)
    )
    row = await cur.fetchone()
    await cur.close()
    return row


async def add_season_xp(user_id: int, season: int, xp: int, day: str) -> None:
    await _conn.execute(
        "INSERT INTO season_progress (user_id, season, xp, last_xp_day) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, season) DO UPDATE SET xp = xp + excluded.xp, last_xp_day = excluded.last_xp_day",
        (user_id, season, xp, day),
    )
    await _conn.commit()


async def set_season_rewarded(user_id: int, season: int, free_level: int, premium_level: int) -> None:
    await _conn.execute(
        "UPDATE season_progress SET rewarded_free = ?, rewarded_premium = ? WHERE user_id = ? AND season = ?",
        (free_level, premium_level, user_id, season),
    )
    await _conn.commit()


async def set_season_premium(user_id: int, season: int) -> bool:
    """Premium yo'lakni yoqadi; allaqachon premium bo'lsa False."""
    await _conn.execute(
        "INSERT OR IGNORE INTO season_progress (user_id, season) VALUES (?, ?)", (user_id, season)
    )
    cur = await _conn.execute(
        "UPDATE season_progress SET premium = 1 WHERE user_id = ? AND season = ? AND premium = 0", (user_id, season)
    )
    await _conn.commit()
    return cur.rowcount > 0


async def season_players_to_remind(season: int) -> list[int]:
    """Shu mavsumda qatnashgan va hali eslatma olmaganlar; eslatildi deb belgilaydi."""
    cur = await _conn.execute(
        "SELECT user_id FROM season_progress WHERE season = ? AND reminded = 0 AND (xp > 0 OR premium = 1)",
        (season,),
    )
    rows = await cur.fetchall()
    await cur.close()
    await _conn.execute("UPDATE season_progress SET reminded = 1 WHERE season = ?", (season,))
    await _conn.commit()
    return [row["user_id"] for row in rows]


# ---------- 🎁 Kunlik bonus ----------


async def daily_bonus_state(user_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute("SELECT last_day, streak FROM daily_bonus WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def claim_daily_bonus(user_id: int, day: str, streak: int, dollars: int, diamonds: int) -> bool:
    """Bugungi bonusni atomik beradi: shu kun uchun allaqachon olingan bo'lsa False (hech narsa o'zgarmaydi)."""
    cur = await _conn.execute(
        "INSERT INTO daily_bonus (user_id, last_day, streak) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET last_day = excluded.last_day, streak = excluded.streak "
        "WHERE daily_bonus.last_day != excluded.last_day",
        (user_id, day, streak),
    )
    if cur.rowcount == 0:
        await _conn.commit()
        return False
    await _conn.execute(
        "UPDATE users SET dollars = dollars + ?, diamonds = diamonds + ? WHERE user_id = ?",
        (dollars, diamonds, user_id),
    )
    await _conn.commit()
    return True


# ---------- 👑 VIP ----------


async def vip_until(user_id: int) -> int:
    cur = await _conn.execute("SELECT until FROM vip WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["until"] if row else 0


async def is_vip(user_id: int) -> bool:
    return await vip_until(user_id) > time.time()


async def set_vip_until(user_id: int, until: int, charge_id: str | None) -> None:
    await _conn.execute(
        "INSERT INTO vip (user_id, until, charge_id) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET until = excluded.until, charge_id = excluded.charge_id",
        (user_id, until, charge_id),
    )
    await _conn.commit()


async def active_vip_users() -> list[int]:
    cur = await _conn.execute("SELECT user_id FROM vip WHERE until > ?", (int(time.time()),))
    rows = await cur.fetchall()
    await cur.close()
    return [row["user_id"] for row in rows]


async def mark_vip_weekly_item(user_id: int, week_start: int) -> bool:
    """Shu hafta uchun birinchi marta bo'lsa True (buyumni berish mumkin)."""
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO vip_weekly_items (user_id, week_start) VALUES (?, ?)", (user_id, week_start)
    )
    await _conn.commit()
    return cur.rowcount > 0


# ---------- O'yinlar jurnali ----------


async def log_game(chat_id: int, winner: str, players: int) -> int:
    cur = await _conn.execute(
        "INSERT INTO game_results (chat_id, winner, players, ended_at) VALUES (?, ?, ?, ?)",
        (chat_id, winner, players, int(time.time())),
    )
    await _conn.commit()
    return cur.lastrowid


async def log_player_game(
    game_id: int, user_id: int, chat_id: int, role: str, won: bool, alive: bool, afk: bool, points: int
) -> None:
    await _conn.execute(
        "INSERT OR IGNORE INTO game_log (game_id, user_id, chat_id, role, won, alive, afk, points, ended_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, user_id, chat_id, role, int(won), int(alive), int(afk), points, int(time.time())),
    )
    await _conn.commit()


async def recent_games(user_id: int, limit: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT role, won, afk, ended_at FROM game_log WHERE user_id = ? ORDER BY ended_at DESC, game_id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def games_in_chat(user_id: int, chat_id: int) -> int:
    cur = await _conn.execute(
        "SELECT COUNT(*) AS n FROM game_log WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)
    )
    row = await cur.fetchone()
    await cur.close()
    return row["n"]


# ---------- Xaridlar tarixi ----------


async def has_any_purchase(user_id: int) -> bool:
    """Hech qachon xarid qilganmi (Stars — sovg'adan tashqari, yoki tasdiqlangan karta buyurtmasi)."""
    cur = await _conn.execute(
        "SELECT 1 FROM star_payments WHERE COALESCE(payer_id, user_id) = ? AND kind != 'gift' LIMIT 1", (user_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    if row:
        return True
    cur = await _conn.execute(
        "SELECT 1 FROM diamond_orders WHERE user_id = ? AND status = 'approved' LIMIT 1", (user_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    return row is not None


async def star_purchase_count(user_id: int, kinds: tuple[str, ...]) -> int:
    marks = ",".join("?" * len(kinds))
    cur = await _conn.execute(
        f"SELECT COUNT(*) AS n FROM star_payments WHERE COALESCE(payer_id, user_id) = ? AND kind IN ({marks})",
        (user_id, *kinds),
    )
    row = await cur.fetchone()
    await cur.close()
    return row["n"]


async def last_played_chat(user_id: int) -> int | None:
    cur = await _conn.execute(
        "SELECT chat_id FROM game_log WHERE user_id = ? ORDER BY ended_at DESC, game_id DESC LIMIT 1", (user_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    return row["chat_id"] if row else None


# ---------- 🤝 Guruh egasi ulushi ----------


async def add_owner_share(user_id: int, millis: int) -> int:
    """Ulush yig'indisiga qo'shadi (manfiy ham bo'lishi mumkin) va yangi yig'indini qaytaradi."""
    await _conn.execute(
        "INSERT INTO owner_share (user_id, millis) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET millis = millis + excluded.millis",
        (user_id, millis),
    )
    await _conn.commit()
    cur = await _conn.execute("SELECT millis FROM owner_share WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["millis"]


async def settle_owner_share(user_id: int) -> int:
    """Yig'ilgan butun olmoslarni hisobga o'tkazadi (foydalanuvchi botda bo'lsa). O'tkazilgan olmos soni."""
    if await get_user(user_id) is None:
        return 0
    cur = await _conn.execute("SELECT millis FROM owner_share WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    whole = (row["millis"] // 1000) if row and row["millis"] > 0 else 0
    if whole <= 0:
        return 0
    await _conn.execute("UPDATE owner_share SET millis = millis - ? WHERE user_id = ?", (whole * 1000, user_id))
    await _conn.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (whole, user_id))
    await _conn.commit()
    return whole


async def get_group_owner_override(chat_id: int) -> int | None:
    cur = await _conn.execute("SELECT owner_id FROM group_owner WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["owner_id"] if row else None


async def set_group_owner_override(chat_id: int, owner_id: int | None) -> None:
    if owner_id is None:
        await _conn.execute("DELETE FROM group_owner WHERE chat_id = ?", (chat_id,))
    else:
        await _conn.execute(
            "INSERT INTO group_owner (chat_id, owner_id) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET owner_id = excluded.owner_id",
            (chat_id, owner_id),
        )
    await _conn.commit()


# ---------- 🔗 Do'st taklifi ----------


async def add_referral(user_id: int, referrer_id: int) -> bool:
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO referrals (user_id, referrer_id, created_at) VALUES (?, ?, ?)",
        (user_id, referrer_id, int(time.time())),
    )
    await _conn.commit()
    return cur.rowcount > 0


async def claim_referral_reward(user_id: int) -> int | None:
    """Taklif qilgan kishining id si — faqat bir marta (keyin None)."""
    # RETURNING ishlatilmaydi — serverdagi eski SQLite (< 3.35) ham qo'llab-quvvatlashi uchun.
    cur = await _conn.execute("SELECT referrer_id FROM referrals WHERE user_id = ? AND rewarded = 0", (user_id,))
    row = await cur.fetchone()
    await cur.close()
    if not row:
        return None
    cur = await _conn.execute("UPDATE referrals SET rewarded = 1 WHERE user_id = ? AND rewarded = 0", (user_id,))
    await _conn.commit()
    return row["referrer_id"] if cur.rowcount > 0 else None


async def referral_count(referrer_id: int) -> tuple[int, int]:
    """(taklif qilinganlar, ulardan xarid qilganlar)."""
    cur = await _conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(rewarded), 0) AS r FROM referrals WHERE referrer_id = ?", (referrer_id,)
    )
    row = await cur.fetchone()
    await cur.close()
    return row["n"], row["r"]


# ---------- 🏰 Guruh premiumi ----------


async def group_premium_until(chat_id: int) -> int:
    cur = await _conn.execute("SELECT until FROM group_premium WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["until"] if row else 0


async def is_group_premium(chat_id: int) -> bool:
    return await group_premium_until(chat_id) > time.time()


async def set_group_premium(chat_id: int, until: int, payer_id: int | None, charge_id: str | None) -> None:
    await _conn.execute(
        "INSERT INTO group_premium (chat_id, until, payer_id, charge_id) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET until = excluded.until, payer_id = excluded.payer_id, "
        "charge_id = excluded.charge_id",
        (chat_id, until, payer_id, charge_id),
    )
    await _conn.commit()


async def premium_group_ids() -> list[int]:
    cur = await _conn.execute("SELECT chat_id FROM group_premium WHERE until > ?", (int(time.time()),))
    rows = await cur.fetchall()
    await cur.close()
    return [row["chat_id"] for row in rows]


async def mark_group_weekly_stats(chat_id: int, week_start: int) -> bool:
    cur = await _conn.execute(
        "INSERT OR IGNORE INTO group_weekly_stats (chat_id, week_start) VALUES (?, ?)", (chat_id, week_start)
    )
    await _conn.commit()
    return cur.rowcount > 0


async def set_group_title(chat_id: int, title: str) -> None:
    await _conn.execute(
        "INSERT INTO group_chats (chat_id, title) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title",
        (chat_id, title),
    )
    await _conn.commit()


async def get_group_title(chat_id: int) -> str | None:
    cur = await _conn.execute("SELECT title FROM group_chats WHERE chat_id = ?", (chat_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["title"] if row else None


async def group_week_stats(chat_id: int, since: int, until: int) -> dict:
    """Guruhning [since, until) oralig'idagi statistikasi."""
    cur = await _conn.execute(
        "SELECT winner, COUNT(*) AS n FROM game_results WHERE chat_id = ? AND ended_at >= ? AND ended_at < ? "
        "GROUP BY winner",
        (chat_id, since, until),
    )
    by_winner = {row["winner"]: row["n"] for row in await cur.fetchall()}
    await cur.close()
    cur = await _conn.execute(
        "SELECT game_log.user_id AS user_id, users.full_name AS full_name, SUM(points) AS points, COUNT(*) AS games "
        "FROM game_log JOIN users ON users.user_id = game_log.user_id "
        "WHERE chat_id = ? AND ended_at >= ? AND ended_at < ? GROUP BY game_log.user_id",
        (chat_id, since, until),
    )
    players = [dict(row) for row in await cur.fetchall()]
    await cur.close()
    return {"by_winner": by_winner, "players": players}


# ---------- 🏆 Turnirlar ----------


async def active_tournament(chat_id: int) -> aiosqlite.Row | None:
    cur = await _conn.execute(
        "SELECT * FROM tournaments WHERE chat_id = ? AND status = 'active' ORDER BY tournament_id DESC LIMIT 1",
        (chat_id,),
    )
    row = await cur.fetchone()
    await cur.close()
    return row


async def create_tournament(chat_id: int, admin_id: int, games_total: int, prize: int) -> int | None:
    """Sovrinni admin hisobidan yechib, turnir yaratadi. Olmos yetmasa yoki faol turnir bo'lsa None."""
    if await active_tournament(chat_id):
        return None
    if not await spend_balance(admin_id, "diamonds", prize):
        return None
    cur = await _conn.execute(
        "INSERT INTO tournaments (chat_id, admin_id, games_total, prize, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, admin_id, games_total, prize, int(time.time())),
    )
    await _conn.commit()
    return cur.lastrowid


async def set_tournament_status(tournament_id: int, from_status: str, to_status: str) -> bool:
    cur = await _conn.execute(
        "UPDATE tournaments SET status = ? WHERE tournament_id = ? AND status = ?", (to_status, tournament_id, from_status)
    )
    await _conn.commit()
    return cur.rowcount > 0


async def add_tournament_game(tournament_id: int, scores: dict[int, tuple[int, int]]) -> int:
    """O'yin natijasini qo'shadi: {user_id: (ochko, g'alaba 0/1)}. O'tgan o'yinlar sonini qaytaradi."""
    for user_id, (points, win) in scores.items():
        await _conn.execute(
            "INSERT INTO tournament_scores (tournament_id, user_id, points, wins) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(tournament_id, user_id) DO UPDATE SET points = points + excluded.points, "
            "wins = wins + excluded.wins",
            (tournament_id, user_id, points, win),
        )
    await _conn.execute("UPDATE tournaments SET games_played = games_played + 1 WHERE tournament_id = ?", (tournament_id,))
    await _conn.commit()
    cur = await _conn.execute("SELECT games_played FROM tournaments WHERE tournament_id = ?", (tournament_id,))
    row = await cur.fetchone()
    await cur.close()
    return row["games_played"]


async def tournament_scores(tournament_id: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT tournament_scores.user_id AS user_id, users.full_name AS full_name, "
        "tournament_scores.points AS points, tournament_scores.wins AS wins "
        "FROM tournament_scores JOIN users ON users.user_id = tournament_scores.user_id "
        "WHERE tournament_id = ?",
        (tournament_id,),
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def expired_tournaments(older_than: int) -> list[aiosqlite.Row]:
    cur = await _conn.execute(
        "SELECT * FROM tournaments WHERE status = 'active' AND created_at < ?", (older_than,)
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows
