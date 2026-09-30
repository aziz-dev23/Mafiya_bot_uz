"""📒 /hisobot va adminlar jurnali."""
import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, private_texts

import audit
import db
import texts
from handlers import report

OWNER = 100
ADMIN = 200


def user(uid, name):
    u = MagicMock()
    u.id = uid
    u.full_name = name
    return u


class ReportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.p.start()
        await db.init_db()
        for uid, name in ((OWNER, "Aziz"), (ADMIN, "Vali"), (1, "Ali"), (2, "Bobur")):
            await db.ensure_user(uid, name, None)

    async def asyncTearDown(self):
        await db.close_db()
        self.p.stop()
        self.tmp.cleanup()

    async def test_admin_action_logged_and_owner_notified(self):
        bot = make_bot()
        with patch.object(audit, "OWNER_IDS", {OWNER}):
            await audit.record(bot, user(ADMIN, "Vali"), "addgem", 1, "diamond", 50)
            await audit.record(bot, user(OWNER, "Aziz"), "addcash", 2, "dollar", 1000)
        owner_msgs = private_texts(bot, OWNER)
        self.assertEqual(len(owner_msgs), 1)  # egasining o'z harakati uchun xabar yo'q
        self.assertIn("Vali", owner_msgs[0])
        self.assertIn("+50💎", owner_msgs[0])
        rows = await db.report_admin_grants(0)
        self.assertEqual({(r["admin_id"], r["amount"]) for r in rows}, {(ADMIN, 50), (OWNER, 1000)})

    async def test_full_report(self):
        await db.record_star_payment("c1", 1, 20, 50, "stars:10:1", payer_id=1, kind="diamonds")
        await db.record_star_payment("c2", 2, 10, 50, "gift:10:2:1", payer_id=1, kind="gift")
        await db.record_star_payment("c3", 1, 0, 100, "vip:1", payer_id=1, kind="vip")
        await db.add_payment_grant("c1", OWNER, "diamond", None, 5)  # taklif mukofoti
        order = await db.create_order(2, 10, 9900)
        await db.set_order_status(order, "approved", ADMIN)
        await db.log_admin_action(ADMIN, "addgem", 2, "diamond", 7)
        listing = await db.create_listing(1, "diamond", 5, "dollar", 1000)
        await db.transition_listing(listing, "sold", 2)

        text = await report.build_report("all", texts)
        self.assertIn("Jami tushum: <b>200⭐</b>", text)
        self.assertIn("🎁 Sovg'a (Stars): 1 ta · 50⭐ · 10💎", text)
        self.assertIn("✅ Tasdiqlangan: 1 ta · 9 900 so'm · 10💎", text)
        self.assertIn("Vali (<code>200</code>): +7💎", text)
        self.assertIn("1 ta: 5💎 sotildi ← 1 000💵 to'landi", text)
        self.assertIn("🔗 Taklif mukofoti: 1 ta · 5💎", text)
        self.assertIn("⭐ Ali → Bobur: 🎁 Sovg'a (Stars) — 10💎, 50⭐", text)
        self.assertIn("🛍 Ali → Bobur", text)
        self.assertLess(len(text), 4096)

    async def test_period_filters(self):
        await db.record_star_payment("old", 1, 10, 50, "stars:10:1", payer_id=1, kind="diamonds")
        await db._conn.execute("UPDATE star_payments SET created_at = ?", (int(time.time()) - 40 * 86400,))
        await db._conn.commit()
        self.assertIn("Jami tushum: <b>50⭐</b>", await report.build_report("all", texts))
        self.assertNotIn("Jami tushum", await report.build_report("month", texts))

    async def test_only_owner_can_open(self):
        message = MagicMock()
        message.answer = AsyncMock()
        message.from_user.id = ADMIN
        with patch.object(report, "OWNER_IDS", {OWNER}):
            await report.cmd_report(message)
            message.answer.assert_not_awaited()
            message.from_user.id = OWNER
            await report.cmd_report(message)
            message.answer.assert_awaited_once()
