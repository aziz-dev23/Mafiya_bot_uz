import asyncio
import os
import tempfile
import unittest
from collections import Counter
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import db
from game import chatlock, engine
from game import settings as settings_module
from game.models import GameState, Role
from game.roles import build_role_list
from ratelimit import RateLimiter
from utils import build_target_keyboard, split_text


class NewRolesDistributionTest(unittest.TestCase):
    def test_roles_appear_at_thresholds(self):
        thresholds = {Role.SERGEANT: 20, Role.JOURNALIST: 25, Role.BODYGUARD: 27, Role.SPY: 28,
                      Role.JUDGE: 30, Role.CUPID: 32}
        for role, n in thresholds.items():
            self.assertEqual(Counter(build_role_list(n - 1))[role], 0, role)
            self.assertEqual(Counter(build_role_list(n))[role], 1, role)
        self.assertEqual(Counter(build_role_list(21))[Role.DOCTOR], 1)
        self.assertEqual(Counter(build_role_list(22))[Role.DOCTOR], 2)

    def test_forty_players_have_about_30_percent_civilians(self):
        share = Counter(build_role_list(40))[Role.CIVILIAN] / 40
        self.assertTrue(0.25 <= share <= 0.35, share)


class NightBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = patch.multiple(
            "game.engine.db", consume_item=AsyncMock(return_value=True), add_balance=AsyncMock(), add_item=AsyncMock(), item_count=AsyncMock(return_value=0)
        )
        self.db.start()
        self.bot = make_bot()

    def tearDown(self):
        self.db.stop()

    def group_text(self, game):
        return "\n".join(c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id)


class BodyguardTest(NightBase):
    async def test_takes_mafia_hit(self):
        game = make_game(Role.DON, Role.BODYGUARD, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 3}
        game.bodyguard_targets = {2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[3].alive)
        self.assertFalse(game.players[2].alive)
        self.assertEqual(game.night_kills, {2: 1})

    async def test_takes_killer_hit(self):
        game = make_game(Role.KILLER, Role.BODYGUARD, Role.CIVILIAN, Role.CIVILIAN)
        game.killer_target = 3
        game.bodyguard_targets = {2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[3].alive)
        self.assertFalse(game.players[2].alive)

    async def test_doctor_save_keeps_bodyguard_alive(self):
        game = make_game(Role.DON, Role.BODYGUARD, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 4}
        game.bodyguard_targets = {2: 4}
        game.doctor_targets = {3: 4}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive and game.players[4].alive)


class LoversTest(NightBase):
    async def test_partner_dies_too(self):
        game = make_game(Role.DON, Role.CUPID, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.cupid_pick = [3, 4]
        game.state = GameState.NIGHT
        game.mafia_votes = {1: 3}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(game.lovers, (3, 4))
        self.assertFalse(game.players[3].alive)
        self.assertFalse(game.players[4].alive)
        self.assertIn(4, game.night_kills)

    async def test_random_pair_when_cupid_skips(self):
        game = make_game(Role.DON, Role.CUPID, Role.CIVILIAN, Role.CIVILIAN)
        await engine.resolve_night(self.bot, game)
        self.assertIsNotNone(game.lovers)
        self.assertEqual(len(set(game.lovers)), 2)
        for uid in game.lovers:
            self.assertTrue(any("oshiq" in m for m in private_texts(self.bot, uid)))

    async def test_day_elimination_kills_partner(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.lovers = (2, 3)
        game.state = GameState.DAY_VOTING
        await engine._kill_player(self.bot, game, game.players[2])
        self.assertFalse(game.players[3].alive)


class SergeantTest(NightBase):
    async def test_promoted_when_detective_dies(self):
        game = make_game(Role.DON, Role.DETECTIVE, Role.SERGEANT, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(game.players[3].role, Role.DETECTIVE)
        self.assertEqual(game.players[2].role, Role.DETECTIVE)  # halok bo'lgan asl Komissar


class MafiaVoteTest(NightBase):
    async def test_tie_resolved_by_don(self):
        game = make_game(Role.DON, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 4, 2: 3}
        for _ in range(20):
            self.assertEqual(engine._pick_mafia_target(game), 4)

    async def test_tie_without_don_vote_is_random(self):
        game = make_game(Role.DON, Role.MAFIA, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {2: 4, 3: 5}
        seen = {engine._pick_mafia_target(game) for _ in range(100)}
        self.assertEqual(seen, {4, 5})

    async def test_status_text_lists_votes(self):
        game = make_game(Role.DON, Role.MAFIA, Role.CIVILIAN)
        game.mafia_votes = {1: 3}
        text = engine.mafia_status_text(game)
        self.assertIn("P1 → P3", text)
        self.assertIn("P2 → …", text)

    async def test_spy_is_mafia_team(self):
        game = make_game(Role.SPY, Role.CIVILIAN)
        self.assertEqual(engine.team_of(game.players[1]), "mafia")


class TwoDoctorsTest(NightBase):
    async def test_either_doctor_saves(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 5}
        game.doctor_targets = {2: 4, 3: 5}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[5].alive)
        self.assertEqual(game.mvp, {3: 3})
        self.assertEqual(game.doctor_last_target, {2: 4, 3: 5})


class GuessTest(NightBase):
    async def test_correct_guess_gets_coins(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 3}
        game.guesses = {2: 3, 4: 5}
        await engine.resolve_night(self.bot, game)
        engine.db.add_balance.assert_awaited_once_with(2, coins=engine.GUESS_REWARD_COINS)


class NightResultsTest(NightBase):
    async def test_results_sent_as_one_message(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.state = GameState.NIGHT
        game.mafia_votes = {1: 3}
        game.killer_target = 4
        await engine.resolve_night(self.bot, game)
        group = [c for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id]
        self.assertEqual(len(group), 1)
        self.assertIn("P3", group[0].args[1])
        self.assertIn("P4", group[0].args[1])


class NightPhaseSmokeTest(NightBase):
    async def test_prompts_and_guesses(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.DETECTIVE, Role.CIVILIAN, Role.MINER)
        game.day_number = 1
        game.settings.night = 0.01
        with patch.object(engine, "NIGHT_RESULTS_DELAY", 0), \
             patch.object(engine, "lock_chat", AsyncMock()), patch.object(engine, "send_phase_image", AsyncMock()):
            await engine.night_phase(self.bot, game)
        self.assertEqual(game.night_expected, {1, 2, 3})
        for uid in (4, 5):
            self.assertTrue(any("halok bo'ladi deb" in m for m in private_texts(self.bot, uid)))
        self.assertIn(1, game.mafia_status_msgs)


class JudgeTest(NightBase):
    async def test_judge_cancels_once(self):
        game = make_game(Role.DON, Role.JUDGE, Role.CIVILIAN, Role.CIVILIAN)

        async def press():
            await asyncio.sleep(0)
            game.judge_event.set()

        with patch.object(settings_module, "JUDGE_DURATION", 1):
            asyncio.get_running_loop().call_soon(lambda: asyncio.ensure_future(press()))
            self.assertTrue(await engine._judge_cancels(self.bot, game, game.players[3]))
        self.assertTrue(game.judge_used)
        self.assertFalse(await engine._judge_cancels(self.bot, game, game.players[3]))

    async def test_no_press_no_cancel(self):
        game = make_game(Role.DON, Role.JUDGE, Role.CIVILIAN, Role.CIVILIAN)
        with patch.object(settings_module, "JUDGE_DURATION", 0.01):
            self.assertFalse(await engine._judge_cancels(self.bot, game, game.players[3]))
        self.assertFalse(game.judge_used)


class DurationsAndKeyboardsTest(unittest.TestCase):
    def test_dynamic_durations(self):
        from game.settings import GroupSettings

        s = GroupSettings(discussion=30, vote=30)
        self.assertEqual(s.discussion_seconds(10), 50)
        self.assertEqual(s.discussion_seconds(40), 110)
        self.assertEqual(s.discussion_seconds(100), 150)
        self.assertEqual(s.vote_seconds(40), 70)
        self.assertEqual(s.vote_seconds(100), 90)
        s.mode = "fast"
        self.assertEqual(s.discussion_seconds(40), 55)

    def test_two_columns_alive_only(self):
        game = make_game(*([Role.CIVILIAN] * 5))
        game.players[3].alive = False
        rows = build_target_keyboard(game, set(), "x").inline_keyboard
        self.assertEqual([len(r) for r in rows], [2, 2])
        self.assertNotIn("x:3", [b.callback_data for r in rows for b in r])

    def test_split_text(self):
        text = "\n".join("a" * 100 for _ in range(100))
        parts = split_text(text)
        self.assertTrue(all(len(p) <= 4096 for p in parts))
        self.assertEqual("\n".join(parts), text)


class RateLimiterTest(unittest.TestCase):
    def test_per_chat_interval(self):
        rl = RateLimiter(per_chat_interval=1, group_per_minute=20, global_per_second=25)
        rl._record(5, 100.0)
        self.assertAlmostEqual(rl._delay(5, 100.2), 0.8)
        self.assertLessEqual(rl._delay(6, 100.2), 0)

    def test_group_per_minute(self):
        rl = RateLimiter(per_chat_interval=0, group_per_minute=20, global_per_second=1000)
        for i in range(20):
            rl._record(-100, 100.0 + i)
        self.assertAlmostEqual(rl._delay(-100, 120.0), 40.0)
        self.assertLessEqual(rl._delay(-100, 160.5), 0)

    def test_global_per_second(self):
        rl = RateLimiter(per_chat_interval=0, group_per_minute=20, global_per_second=3)
        for chat in (1, 2, 3):
            rl._record(chat, 10.0)
        self.assertAlmostEqual(rl._delay(4, 10.5), 0.5)


class ChatLockTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.patch.start()
        await db.init_db()
        chatlock._warned_chats.clear()

    async def asyncTearDown(self):
        await db.close_db()
        self.patch.stop()
        self.tmp.cleanup()

    def _bot(self):
        from aiogram.types import ChatPermissions

        bot = make_bot()
        bot.get_chat = AsyncMock(return_value=MagicMock(permissions=ChatPermissions(can_send_messages=True,
                                                                                    can_send_photos=False)))
        bot.set_chat_permissions = AsyncMock()
        return bot

    async def test_lock_and_restore_original(self):
        bot = self._bot()
        game = make_game(Role.DON)
        await chatlock.lock_chat(bot, game)
        self.assertTrue(game.chat_locked)
        self.assertFalse(bot.set_chat_permissions.await_args.args[1].can_send_messages)
        await chatlock.unlock_chat(bot, game)
        restored = bot.set_chat_permissions.await_args.args[1]
        self.assertTrue(restored.can_send_messages)
        self.assertFalse(restored.can_send_photos)
        self.assertIsNone(await db.get_chat_lock(game.chat_id))

    async def test_restore_after_restart(self):
        bot = self._bot()
        game = make_game(Role.DON)
        await chatlock.lock_chat(bot, game)
        await chatlock.restore_all_locks(bot)  # bot qayta ishga tushdi
        self.assertTrue(bot.set_chat_permissions.await_args.args[1].can_send_messages)
        self.assertEqual(await db.all_chat_locks(), [])

    async def test_no_rights_warns_once(self):
        from aiogram.exceptions import TelegramBadRequest

        bot = self._bot()
        bot.set_chat_permissions = AsyncMock(side_effect=TelegramBadRequest(MagicMock(), "not enough rights"))
        for _ in range(2):
            game = make_game(Role.DON)
            await chatlock.lock_chat(bot, game)
            self.assertFalse(game.chat_locked)
        self.assertEqual(bot.send_message.await_count, 1)
        self.assertIsNone(await db.get_chat_lock(-100))


if __name__ == "__main__":
    unittest.main()


class RetryAfterTest(unittest.IsolatedAsyncioTestCase):
    async def test_retries_after_429(self):
        from aiogram.exceptions import TelegramRetryAfter
        from aiogram.methods import SendMessage

        import ratelimit

        method = SendMessage(chat_id=5, text="x")
        calls = []

        async def make_request(bot, m):
            calls.append(m)
            if len(calls) == 1:
                raise TelegramRetryAfter(method=m, message="Too Many Requests", retry_after=0)
            return "ok"

        mw = ratelimit.RateLimitMiddleware(RateLimiter(per_chat_interval=0))
        self.assertEqual(await mw(make_request, MagicMock(), method), "ok")
        self.assertEqual(len(calls), 2)
