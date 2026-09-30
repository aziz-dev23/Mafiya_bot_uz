import os
import re
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import cosmetics
import db
import economy
import season
import texts
from economy import (
    COSMETICS,
    SEASON_MAX_LEVEL,
    season_free_rewards,
    season_level_for_xp,
    season_premium_rewards,
    season_xp_for_level,
)
from game import engine
from game.models import GameState, Role
from i18n import LANGS, get_texts

NOV = datetime(2026, 11, 10, 12, 0, tzinfo=season.TZ)


class SeasonMathTest(unittest.TestCase):
    def test_level_costs(self):
        self.assertEqual(season_xp_for_level(10), 50)
        self.assertEqual(season_xp_for_level(20), 120)
        self.assertEqual(season_xp_for_level(30), 210)
        self.assertEqual(season_level_for_xp(4), 0)
        self.assertEqual(season_level_for_xp(5), 1)
        self.assertEqual(season_level_for_xp(57), 11)
        self.assertEqual(season_level_for_xp(10_000), SEASON_MAX_LEVEL)

    def test_reward_tables_match_spec(self):
        premium_diamonds = sum(r[1] for lvl in range(1, 31) for r in season_premium_rewards(lvl) if r[0] == "diamond")
        self.assertEqual(premium_diamonds, 60)
        self.assertEqual(season_free_rewards(1), [("dollar", 100)])
        self.assertEqual(season_free_rewards(2), [("coin", 10)])
        self.assertIn(("item", "shield", 1), season_free_rewards(20))
        self.assertEqual(season_premium_rewards(3), [("item", "shield", 2)])
        self.assertEqual(season_premium_rewards(7), [("item", "poison_shield", 1)])
        self.assertEqual(season_premium_rewards(27), [("item", "mask", 1)])
        self.assertEqual(season_premium_rewards(12), [("cosmetic", "title")])
        self.assertEqual(season_premium_rewards(22), [("cosmetic", "death")])
        self.assertEqual(season_premium_rewards(30), [("diamond", 10), ("cosmetic", "frame")])
        self.assertEqual(season_premium_rewards(4), [("coin", 20)])

    def test_season_calendar(self):
        self.assertIsNone(season.current_season(datetime(2026, 10, 31, 23, 59, tzinfo=season.TZ)))
        self.assertEqual(season.current_season(datetime(2026, 11, 1, 0, 0, tzinfo=season.TZ)), 1)
        self.assertEqual(season.current_season(datetime(2027, 1, 5, tzinfo=season.TZ)), 3)
        self.assertEqual(season.days_left(1, datetime(2026, 11, 28, tzinfo=season.TZ)), 3)


class CatalogRulesTest(unittest.TestCase):
    FORBIDDEN = ["Don", "Komissar", "Mafiya", "👑", "🦸"] + [
        n.split(" ", 1)[0] for n in texts.ROLE_NAMES.values()
    ] + [i["emoji"] for i in economy.ITEMS.values()]

    def test_titles_short_and_clean(self):
        titles = [c["key"] for c in COSMETICS if c["kind"] == economy.TITLE]
        for lang in LANGS:
            L = get_texts(lang)
            for key in titles:
                name = L.COSMETIC_NAMES[key]
                with self.subTest(lang=lang, key=key):
                    self.assertLessEqual(len(name.split(" ", 1)[1]), economy.TITLE_MAX_LENGTH)
                    for bad in self.FORBIDDEN:
                        self.assertNotIn(bad, name)

    def test_every_cosmetic_has_texts(self):
        for c in COSMETICS:
            self.assertIn(c["key"], texts.COSMETIC_NAMES)
            if c["kind"] == economy.DEATH_STYLE:
                self.assertIn(c["key"], texts.DEATH_STYLES)
            if c["kind"] == economy.FRAME:
                self.assertIn(c["key"], texts.FRAME_LINES)

    def test_death_line(self):
        self.assertEqual(
            cosmetics.death_line("curtain", "Ali", "🕵️ Komissar", texts),
            "🎬 Parda yopildi: Ali sahnani tark etdi. U 🕵️ Komissar edi.",
        )
        self.assertEqual(cosmetics.death_line("curtain", "Ali", None, texts), "🎬 Parda yopildi: Ali sahnani tark etdi.")
        self.assertIsNone(cosmetics.death_line(None, "Ali", None, texts))


class DbCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.p.start()
        await db.init_db()
        await db.ensure_user(1, "Ali", None)
        await db.ensure_user(2, "Vali", None)

    async def asyncTearDown(self):
        await db.close_db()
        self.p.stop()
        self.tmp.cleanup()

    async def balance(self, uid):
        row = await db.get_user(uid)
        return row["dollars"], row["coins"], row["diamonds"]


class CosmeticsTest(DbCase):
    async def test_buy_with_each_currency_and_activate(self):
        await db.add_balance(1, dollars=3000, coins=150, diamonds=25)
        self.assertEqual(await cosmetics.buy(1, "night_guard"), "ok")  # 150🪙
        self.assertEqual(await cosmetics.buy(1, "orator"), "ok")  # 3000💵
        self.assertEqual(await cosmetics.buy(1, "rose"), "ok")  # 25💎
        self.assertEqual(await self.balance(1), (0, 0, 0))
        self.assertEqual(await cosmetics.buy(1, "orator"), "owned")
        self.assertEqual(await cosmetics.buy(1, "old_fox"), "no_funds")
        self.assertEqual(await cosmetics.buy(1, "newcomer"), "not_for_sale")
        active = await cosmetics.active(1)
        self.assertEqual(active, {"title": "orator", "death": "rose"})
        self.assertTrue(await cosmetics.activate(1, "night_guard"))
        self.assertFalse(await cosmetics.activate(1, "shadow"))  # sotib olinmagan
        await cosmetics.take_off(1, "death")
        self.assertEqual(await cosmetics.active(1), {"title": "night_guard"})

    async def test_champion_title_expires_and_restores(self):
        await db.grant_cosmetic(1, "owl")
        await db.set_active_cosmetic(1, "title", "owl")
        await cosmetics.grant_weekly_champion(1, now=time.time())
        self.assertEqual((await cosmetics.active(1))["title"], "weekly_champion")
        await cosmetics.grant_weekly_champion(1, now=time.time() - 8 * 24 * 3600)  # muddati o'tgan
        self.assertEqual((await cosmetics.active(1))["title"], "owl")

    async def test_public_profile_hides_balance(self):
        from handlers import admin

        await db.add_balance(1, dollars=999, diamonds=77)
        await db.grant_cosmetic(1, "fire_frame")
        await db.set_active_cosmetic(1, "frame", "fire_frame")
        text = await admin.build_public_profile(1)
        self.assertIn("🔥━━━━━━━━━━━━🔥", text)
        self.assertNotIn("999", text)
        self.assertNotIn("77", text)


class SeasonDbTest(DbCase):
    async def test_xp_rules(self):
        self.assertIsNone(await season.award_game_xp(1, True, 5, now=NOV))  # kamida 6 kishi
        xp, level, rewards = await season.award_game_xp(1, True, 6, now=NOV)
        self.assertEqual(xp, 5)  # 3 + kunning birinchi o'yini 2
        self.assertEqual(level, 1)
        self.assertEqual(rewards, [("dollar", 100)])
        xp, _, _ = await season.award_game_xp(1, False, 8, now=NOV)
        self.assertEqual(xp, 1)
        self.assertEqual(await self.balance(1), (100, 0, 0))

    async def test_premium_mid_season_catch_up(self):
        for _ in range(4):  # 4 × 3 + 2 = 14 XP -> 2-daraja
            await season.award_game_xp(2, True, 10, now=NOV)
        with patch.object(season, "current_season", return_value=1):
            self.assertEqual((await season.buy_premium(2))[0], "no_funds")
            await db.add_balance(2, diamonds=50)
            status, rewards = await season.buy_premium(2)
            self.assertEqual(status, "ok")
            self.assertEqual(rewards, [("coin", 20), ("coin", 20)])  # 1- va 2-daraja premium
            self.assertEqual((await season.buy_premium(2))[0], "already")
        self.assertEqual(await self.balance(2), (100, 10 + 40, 0))

    async def test_cosmetic_reward_level_12(self):
        with patch.object(season, "current_season", return_value=1):
            await db.add_balance(1, diamonds=50)
            await season.buy_premium(1)
        await db.add_season_xp(1, 1, season_xp_for_level(12), "2026-11-10")
        await season.grant_pending_rewards(1, 1)
        self.assertIn("s1_title", await db.owned_cosmetics(1))

    async def test_reminder_once(self):
        await season.award_game_xp(1, True, 6, now=NOV)
        bot = make_bot()
        near_end = datetime(2026, 11, 28, 10, 0, tzinfo=season.TZ)
        self.assertEqual(await season.send_reminders(bot, now=NOV), 0)  # hali erta
        self.assertEqual(await season.send_reminders(bot, now=near_end), 1)
        self.assertEqual(await season.send_reminders(bot, now=near_end), 0)

    async def test_view_texts_all_languages(self):
        with patch.object(season, "current_season", return_value=1):
            for lang in LANGS:
                text, can_buy = await season.season_view(1, get_texts(lang), now=NOV)
                self.assertTrue(can_buy)
                self.assertIn("1", text)
        text, _ = await season.season_view(1, texts, now=datetime(2026, 10, 5, tzinfo=season.TZ))
        self.assertIn("01.11.2026", text)


class DeathStyleInGameTest(unittest.IsolatedAsyncioTestCase):
    async def test_style_replaces_cause_and_respects_reveal(self):
        bot = make_bot()
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].death_key = "lightning"
        game.players[2].title_key = "owl"
        game.state = GameState.NIGHT
        game.mafia_votes = {1: 2}
        with patch.multiple("game.engine.db", consume_item=AsyncMock(), add_balance=AsyncMock(),
                            add_item=AsyncMock(), item_count=AsyncMock(return_value=0)):
            await engine.resolve_night(bot, game)
        group = [c.args[1] for c in bot.send_message.call_args_list if c.args[0] == game.chat_id][0]
        self.assertTrue(group.startswith("⚡ Bir zumda!"))
        self.assertIn("🦉 Boyo'g'li", group)
        self.assertIn(texts.ROLE_NAMES[Role.CIVILIAN], group)
        self.assertNotIn("Tun natijasi", group)

        game.settings.reveal_roles = False
        self.assertNotIn("edi", engine._styled_death(game, game.players[2]))



class DailyBonusTest(DbCase):
    def day(self, n):
        return datetime(2026, 10, 1 + n, 9, 0, tzinfo=season.TZ)

    async def test_streak_and_reset(self):
        import bonus

        got = []
        for n in range(8):
            r = await bonus.claim(1, now=self.day(n))
            got.append((r["day"], r["dollars"], r["diamonds"]))
        self.assertEqual(got[0], (1, 20, 0))
        self.assertEqual(got[1], (2, 30, 0))
        self.assertEqual(got[6], (7, 80, 1))
        self.assertEqual(got[7], (1, 20, 0))  # 7-kundan keyin yana 1-kun
        self.assertFalse((await bonus.claim(1, now=self.day(7)))["ok"])  # bugun ikkinchi marta
        r = await bonus.claim(1, now=self.day(9))  # 1 kun o'tkazib yuborildi
        self.assertEqual(r["day"], 1)
        dollars, _, diamonds = await self.balance(1)
        self.assertEqual((dollars, diamonds), (20 + 30 + 40 + 50 + 60 + 70 + 80 + 20 + 20, 1))

    async def test_vip_doubles_dollars_only(self):
        import bonus

        await db.set_vip_until(1, int(time.time()) + 3600, "ch")
        r = await bonus.claim(1, now=self.day(0))
        self.assertEqual((r["dollars"], r["diamonds"], r["vip"]), (40, 0, True))


def vip_payment_message(user_id, charge_id, first=True, amount=100):
    m = MagicMock()
    m.from_user.id = user_id
    m.from_user.full_name = "Ali"
    m.from_user.username = None
    m.answer = AsyncMock()
    p = m.successful_payment
    p.telegram_payment_charge_id = charge_id
    p.invoice_payload = f"vip:{user_id}"
    p.currency = "XTR"
    p.total_amount = amount
    p.subscription_expiration_date = int(time.time()) + 30 * 86400
    p.is_recurring = True
    p.is_first_recurring = first
    return m


class VipTest(DbCase):
    async def test_payment_renewal_and_refund(self):
        from handlers import stars

        bot = MagicMock(send_message=AsyncMock(), refund_star_payment=AsyncMock())
        await stars.on_successful_payment(vip_payment_message(1, "v1"), bot)
        await stars.on_successful_payment(vip_payment_message(1, "v1"), bot)  # takroriy update
        self.assertTrue(await db.is_vip(1))
        renewal = vip_payment_message(1, "v2", first=False)
        renewal.successful_payment.subscription_expiration_date = int(time.time()) + 60 * 86400
        await stars.on_successful_payment(renewal, bot)
        self.assertGreater(await db.vip_until(1), time.time() + 59 * 86400)
        self.assertIn("✅", await stars.refund_payment(bot, "v2", force=False))
        self.assertFalse(await db.is_vip(1))

    async def test_wrong_amount_rejected(self):
        from handlers import stars

        self.assertFalse(stars.validate_vip("vip:1", "XTR", 99, 1))
        self.assertFalse(stars.validate_vip("vip:1", "XTR", 100, 2))
        self.assertTrue(stars.validate_vip("vip:1", "XTR", 100, 1))

    async def test_weekly_item_once(self):
        import vip

        await db.set_vip_until(1, int(time.time()) + 3600, "ch")
        bot = make_bot()
        self.assertEqual(await vip.give_weekly_items(bot, 1000), 1)
        self.assertEqual(await vip.give_weekly_items(bot, 1000), 0)
        self.assertEqual(await db.item_count(1, "shield"), 1)

    async def test_history_in_profile_only_for_vip(self):
        from handlers import admin

        game_id = await db.log_game(-1, "town", 8)
        await db.log_player_game(game_id, 1, -1, "doctor", True, True, False, 10)
        text, _ = await admin.build_profile_view(1, "Ali")
        self.assertNotIn(texts.PROFILE_HISTORY_HEADER, text)
        await db.set_vip_until(1, int(time.time()) + 3600, "ch")
        text, _ = await admin.build_profile_view(1, "Ali")
        self.assertIn(texts.PROFILE_HISTORY_HEADER, text)
        self.assertIn(texts.ROLE_NAMES[Role.DOCTOR], text)
        self.assertIn("👑", text)


if __name__ == "__main__":
    unittest.main()
