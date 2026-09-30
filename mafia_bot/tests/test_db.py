import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import helpers  # noqa: F401  (sys.path sozlaydi)

import db
import weekly
from economy import WEEKLY_REWARD_DIAMONDS

WEEK = 7 * 24 * 3600


class DbTestCase(unittest.IsolatedAsyncioTestCase):
    """Har bir test vaqtinchalik SQLite fayl bilan ishlaydi (haqiqiy mafia.db ga tegmaydi)."""

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        self.patch = patch.object(db, "DB_PATH", self.path)
        self.patch.start()

    async def asyncTearDown(self):
        await db.close_db()
        self.patch.stop()
        self.tmp.cleanup()


class MigrationTest(DbTestCase):
    async def test_killer_shield_x10_runs_once_with_backup(self):
        con = sqlite3.connect(self.path)
        con.execute("CREATE TABLE inventory (user_id INTEGER, item_key TEXT, count INTEGER, enabled INTEGER DEFAULT 1, "
                    "PRIMARY KEY (user_id, item_key))")
        con.execute("INSERT INTO inventory VALUES (1, 'killer_shield', 2, 1), (1, 'shield', 3, 1)")
        con.commit()
        con.close()

        await db.init_db()
        await db.close_db()
        await db.init_db()  # ikkinchi ishga tushish — qayta ko'paytirmasligi kerak

        rows = {r["item_key"]: r["count"] for r in await db.get_inventory(1)}
        self.assertEqual(rows, {"killer_shield": 20, "shield": 3})
        backups = [f for f in os.listdir(self.tmp.name) if ".backup-" in f]
        self.assertEqual(len(backups), 1)


class WeeklyRewardTest(DbTestCase):
    async def test_pays_top3_once(self):
        await db.init_db()
        last_week = db.period_starts()["weekly"] - WEEK
        for uid, pts in ((1, 50), (2, 80), (3, 10), (4, 30)):
            await db.ensure_user(uid, f"U{uid}", None)
            await db._conn.execute(
                "INSERT INTO points_log (user_id, points, created_at) VALUES (?, ?, ?)", (uid, pts, last_week + 100)
            )
        # Joriy haftadagi ball hisobga olinmasligi kerak
        await db._conn.execute("INSERT INTO points_log (user_id, points, created_at) VALUES (3, 999, ?)", (int(time.time()),))
        await db._conn.commit()

        bot = MagicMock(send_message=AsyncMock())
        self.assertTrue(await weekly.pay_last_week(bot))
        self.assertFalse(await weekly.pay_last_week(bot))

        diamonds = {uid: (await db.get_user(uid))["diamonds"] for uid in (1, 2, 3, 4)}
        self.assertEqual(diamonds, {2: WEEKLY_REWARD_DIAMONDS[0], 1: WEEKLY_REWARD_DIAMONDS[1],
                                    4: WEEKLY_REWARD_DIAMONDS[2], 3: 0})
        self.assertEqual(bot.send_message.await_count, 3)


class TransferTest(DbTestCase):
    async def test_transfer_logs_and_counts_today(self):
        await db.init_db()
        await db.ensure_user(1, "A", None)
        await db.ensure_user(2, "B", None)
        await db.add_balance(1, dollars=100)
        self.assertTrue(await db.transfer_balance(1, 2, "dollar", "dollars", 60))
        self.assertFalse(await db.transfer_balance(1, 2, "dollar", "dollars", 60))
        self.assertEqual(await db.sent_today(1, "dollar"), 60)
        self.assertEqual(await db.sent_today(1, "diamond"), 0)
        self.assertEqual((await db.get_user(2))["dollars"], 60)


    async def test_limits_and_admin_exemption(self):
        from handlers import transfer

        await db.init_db()
        await db.ensure_user(1, "A", None)
        await db.ensure_user(2, "B", None)
        self.assertIsNotNone(await transfer._limit_error(1, "dollar"))  # 0 ta o'yin
        await db._conn.execute("UPDATE users SET games = 20, dollars = 10000 WHERE user_id = 1")
        await db._conn.commit()
        self.assertIsNone(await transfer._limit_error(1, "dollar", 5000))
        await db.transfer_balance(1, 2, "dollar", "dollars", 4000)
        self.assertIsNone(await transfer._limit_error(1, "dollar", 1000))
        self.assertIsNotNone(await transfer._limit_error(1, "dollar", 1001))
        with patch.object(transfer, "ADMIN_IDS", {1}):
            self.assertIsNone(await transfer._limit_error(1, "dollar", 999999))


if __name__ == "__main__":
    unittest.main()
