"""7-bosqich: 🏰 guruh premiumi (statistika, unvon, turnir), 🌱/🎁 do'kon tugmalari, 🔗 taklif, ⚙️ guruh nomi."""
import os
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import db
import group_features
from economy import GROUP_TITLE_GAMES
from game.models import Role
from handlers import gifts, group_settings, shop


class DbCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.p.start()
        await db.init_db()
        for uid in range(1, 8):
            await db.ensure_user(uid, f"P{uid}", f"user{uid}")

    async def asyncTearDown(self):
        await db.close_db()
        self.p.stop()
        self.tmp.cleanup()

    async def diamonds(self, uid):
        return (await db.get_user(uid))["diamonds"]


def six_player_game():
    game = make_game(Role.MAFIA, Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.DOCTOR, Role.DETECTIVE)
    game.started_at = time.time()
    return game


class TournamentPointsTest(unittest.TestCase):
    def test_points(self):
        game = six_player_game()
        game.players[3].alive = False
        game.players[4].afk = True
        game.mvp = {5: 10, 6: 8, 3: 5, 1: 1}
        scores = group_features.tournament_points(game, "town")
        self.assertNotIn(4, scores)                 # AFK — ochko yo'q
        self.assertEqual(scores[5], (3 + 1 + 2, 1))  # g'alaba + tirik + MVP
        self.assertEqual(scores[3], (3 + 2, 1))      # halok, lekin g'olib jamoa va MVP
        self.assertEqual(scores[1], (1, 0))          # yutqazdi, tirik, MVP top-3 dan tashqarida


class TournamentDbTest(DbCase):
    async def test_prize_split_and_remainder(self):
        await db.add_balance(1, diamonds=100)
        tid = await db.create_tournament(-100, 1, 3, 11)
        self.assertIsNotNone(tid)
        self.assertEqual(await self.diamonds(1), 89)
        await db.add_tournament_game(tid, {2: (6, 1), 3: (4, 1), 4: (1, 0)})
        t = await db.active_tournament(-100)
        text = await group_features.finish_tournament(make_bot(), t, __import__("texts"))
        self.assertIn("P2", text)
        # 11💎: 50% → 5, 30% → 3, 20% → 2, qoldiq 1 → adminga
        self.assertEqual([await self.diamonds(u) for u in (2, 3, 4)], [5, 3, 2])
        self.assertEqual(await self.diamonds(1), 90)
        self.assertIsNone(await db.active_tournament(-100))

    async def test_not_enough_and_cancel(self):
        self.assertIsNone(await db.create_tournament(-100, 1, 3, 10))
        await db.add_balance(1, diamonds=10)
        await db.create_tournament(-100, 1, 3, 10)
        t = await db.active_tournament(-100)
        self.assertTrue(await group_features.cancel_tournament(t))
        self.assertEqual(await self.diamonds(1), 10)

    async def test_cannot_cancel_after_game(self):
        await db.add_balance(1, diamonds=10)
        tid = await db.create_tournament(-100, 1, 3, 10)
        await db.add_tournament_game(tid, {2: (3, 1)})
        self.assertFalse(await group_features.cancel_tournament(await db.active_tournament(-100)))

    async def test_game_end_appends_table_only_for_premium(self):
        game = six_player_game()
        await db.add_balance(1, diamonds=10)
        await db.create_tournament(-100, 1, 3, 10)
        game.started_at = time.time() + 1
        self.assertEqual(await group_features.on_game_finished(make_bot(), game, "town"), [])
        await db.set_group_premium(-100, int(time.time()) + 3600, 1, "c")
        lines = await group_features.on_game_finished(make_bot(), game, "town")
        self.assertIn("(1/3)", "\n".join(lines))

    async def test_small_game_not_counted(self):
        await db.set_group_premium(-100, int(time.time()) + 3600, 1, "c")
        await db.add_balance(1, diamonds=10)
        await db.create_tournament(-100, 1, 3, 10)
        game = make_game(Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN, Role.DOCTOR)
        game.started_at = time.time() + 1
        self.assertEqual(await group_features.on_game_finished(make_bot(), game, "town"), [])

    async def test_expired_tournament_is_distributed(self):
        await db.add_balance(1, diamonds=10)
        tid = await db.create_tournament(-100, 1, 5, 10)
        await db.add_tournament_game(tid, {2: (3, 1)})
        self.assertEqual(await group_features.finish_expired_tournaments(make_bot(), time.time() + 49 * 3600), 1)
        self.assertEqual(await self.diamonds(2), 5)
        self.assertEqual(await self.diamonds(1), 5)


class GroupTitleTest(DbCase):
    async def test_title_granted_at_threshold(self):
        await db.set_group_premium(-100, int(time.time()) + 3600, 1, "c")
        await db.set_group_title(-100, "Mafia Klub Toshkent")
        game = six_player_game()
        bot = make_bot()
        with patch.object(db, "games_in_chat", AsyncMock(side_effect=lambda uid, chat: GROUP_TITLE_GAMES if uid == 2 else 3)):
            await group_features.on_game_finished(bot, game, "town")
        self.assertIn("group:-100", await db.owned_cosmetics(2))
        self.assertNotIn("group:-100", await db.owned_cosmetics(3))
        self.assertTrue(any("Mafia Klub Tosh" in t for t in private_texts(bot, 2)))

    async def test_title_hidden_when_premium_expires(self):
        await db.grant_cosmetic(2, "group:-100")
        await db.set_group_premium(-100, int(time.time()) + 3600, 1, "c")
        self.assertIn("group:-100", await db.owned_cosmetics(2))
        await db.set_group_premium(-100, int(time.time()) - 1, None, None)
        self.assertNotIn("group:-100", await db.owned_cosmetics(2))


class WeeklyStatsTest(DbCase):
    async def test_only_monday_after_ten_and_once(self):
        await db.set_group_premium(-100, int(time.time()) + 10 * 86400, 1, "c")
        bot = make_bot()
        monday = datetime.now(group_features.TZ)
        monday = group_features.week_start(monday).replace(hour=10, minute=5)
        stats = {"by_winner": {"town": 3, "mafia": 1}, "players": [
            {"user_id": 2, "full_name": "P2", "points": 30, "games": 4},
            {"user_id": 3, "full_name": "P3", "points": 10, "games": 2},
        ]}
        with patch.object(db, "group_week_stats", AsyncMock(return_value=stats)):
            self.assertEqual(await group_features.send_weekly_stats(bot, monday.replace(hour=9)), 0)
            self.assertEqual(await group_features.send_weekly_stats(bot, monday), 1)
            self.assertEqual(await group_features.send_weekly_stats(bot, monday), 0)
        text = bot.send_message.await_args.args[1]
        self.assertIn("75%", text)
        self.assertIn("25%", text)

    async def test_no_games_no_message(self):
        await db.set_group_premium(-100, int(time.time()) + 10 * 86400, 1, "c")
        bot = make_bot()
        monday = group_features.week_start(datetime.now(group_features.TZ)).replace(hour=11)
        self.assertEqual(await group_features.send_weekly_stats(bot, monday), 0)
        bot.send_message.assert_not_awaited()


class ShopAndGiftTest(DbCase):
    def test_shop_buttons(self):
        _, kb = shop.shop_view(starter=True, first=True)
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("stars:starter", data)
        self.assertIn("stars:gift", data)
        _, kb = shop.shop_view()
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertNotIn("stars:starter", data)

    async def test_find_recipient(self):
        self.assertEqual((await gifts.find_recipient("3"))["user_id"], 3)
        self.assertEqual((await gifts.find_recipient("@User4"))["user_id"], 4)
        self.assertIsNone(await gifts.find_recipient("@nobody"))

    async def test_referral_text(self):
        await db.add_referral(5, 1)
        text = await gifts.referral_text(make_bot(), 1)
        self.assertIn("start=ref_1", text)


class GroupNameTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(group_settings.clean_group_name("  Mafia   Klub "), "Mafia Klub")
        self.assertIsNone(group_settings.clean_group_name("x" * 15))
        self.assertIsNone(group_settings.clean_group_name("   "))
