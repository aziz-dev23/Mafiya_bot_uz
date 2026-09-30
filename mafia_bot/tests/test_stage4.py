import asyncio
import os
import tempfile
import time
import unittest
from collections import Counter
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import db
import economy
import texts
from game import engine
from game.manager import manager
from game.models import GameState, Role
from game.roles import build_role_list
from game.settings import LOCK_PLAYERS, GroupSettings, load_settings, save_settings
from handlers import afterlife, common, day, group_settings, lobby


def cb(user_id, data, chat_id=-100):
    c = MagicMock()
    c.from_user.id = user_id
    c.from_user.full_name = f"P{user_id}"
    c.data = data
    c.answer = AsyncMock()
    c.message.chat.id = chat_id
    c.message.edit_text = AsyncMock()
    return c


def msg(user_id, text):
    m = MagicMock()
    m.from_user.id = user_id
    m.text = text
    m.answer = AsyncMock()
    return m


class Registered(unittest.IsolatedAsyncioTestCase):
    """O'yinni manager'da ro'yxatdan o'tkazadi (handlerlar o'yinni shu orqali topadi)."""

    def register(self, game):
        manager.games[game.chat_id] = game
        for uid in game.players:
            manager.register_player(game, uid)
        self.addCleanup(manager.remove_game, game.chat_id)
        return game

    def setUp(self):
        self.db = patch.multiple(
            "game.engine.db", consume_item=AsyncMock(return_value=True), add_balance=AsyncMock(), add_item=AsyncMock(), item_count=AsyncMock(return_value=0)
        )
        self.db.start()
        self.addCleanup(self.db.stop)
        self.bot = make_bot()


class AfkTest(Registered):
    async def test_two_missed_votes_kick(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        voters = list(game.players.values())
        for _ in range(2):
            game.day_votes = {1: None, 2: None, 3: 4}  # "ovoz bermaslik" ham ovoz
            await engine._check_vote_afk(self.bot, game, voters)
        self.assertFalse(game.players[5].alive)
        self.assertTrue(game.players[5].afk)
        self.assertTrue(game.players[1].alive)

    async def test_vote_resets_counter(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN)
        voters = list(game.players.values())
        for votes in ({1: None}, {1: None, 3: 1}, {1: None}):
            game.day_votes = votes
            await engine._check_vote_afk(self.bot, game, voters)
        self.assertTrue(game.players[3].alive)

    async def test_two_missed_nights_kick(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        for _ in range(2):
            game.night_expected, game.night_acted = {1, 2}, {1}
            await engine._check_night_afk(self.bot, game)
        self.assertFalse(game.players[2].alive)

    async def test_afk_gets_no_reward(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].afk = True
        game.players[2].alive = False
        self.assertFalse(economy.did_win(game.players[2], "town"))
        with patch.multiple("economy.db", add_balance=AsyncMock(), record_game_result=AsyncMock(),
                            add_points=AsyncMock(), record_role_result=AsyncMock(), log_game=AsyncMock(return_value=1), log_player_game=AsyncMock(), is_group_premium=AsyncMock(return_value=False)):
            await economy.payout_game_results(game, "town")
            paid = {c.args[0] for c in economy.db.add_balance.await_args_list}
            economy.db.record_role_result.assert_any_await(2, "civilian", False)
        self.assertNotIn(2, paid)


class LastWordAndDeadChatTest(Registered):
    async def test_last_word_posted_once(self):
        game = self.register(make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN))
        game.state = GameState.DAY_DISCUSSION
        await engine._kill_player(self.bot, game, game.players[2])
        self.assertIn(2, game.last_word_deadline)
        filt = await afterlife.DeadPlayerFilter()(msg(2, "Men tinchman!"))
        self.assertTrue(filt)
        await afterlife.on_dead_player_message(msg(2, "Men tinchman!"), self.bot, **filt)
        group = [c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id]
        self.assertTrue(any("Men tinchman!" in t for t in group))
        self.assertNotIn(2, game.last_word_deadline)

    async def test_too_long_rejected(self):
        game = self.register(make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN))
        game.state = GameState.DAY_DISCUSSION
        await engine._kill_player(self.bot, game, game.players[2])
        m = msg(2, "x" * 201)
        await afterlife.on_dead_player_message(m, self.bot, game=game, player=game.players[2])
        m.answer.assert_awaited()
        self.assertIn(2, game.last_word_deadline)

    async def test_dead_chat_relay(self):
        game = self.register(make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN))
        game.state = GameState.NIGHT
        for uid in (2, 3):
            game.players[uid].alive = False
        game.last_word_deadline[2] = time.monotonic() - 1  # muddati o'tgan
        await afterlife.on_dead_player_message(msg(2, "salom"), self.bot, game=game, player=game.players[2])
        self.assertIn("☠️ P2: salom", private_texts(self.bot, 3))
        self.assertEqual(private_texts(self.bot, 4), [])

    async def test_alive_player_not_matched(self):
        game = self.register(make_game(Role.DON, Role.CIVILIAN))
        game.state = GameState.NIGHT
        self.assertFalse(await afterlife.DeadPlayerFilter()(msg(2, "salom")))

    async def test_last_word_disabled(self):
        game = make_game(Role.DON, Role.CIVILIAN)
        game.settings.last_word = False
        await engine._kill_player(self.bot, game, game.players[2])
        self.assertEqual(game.last_word_deadline, {})


class RevealAndHistoryTest(Registered):
    async def test_no_role_reveal(self):
        game = make_game(Role.DON, Role.DETECTIVE, Role.CIVILIAN, Role.CIVILIAN)
        game.settings.reveal_roles = False
        game.state = GameState.NIGHT
        game.mafia_votes = {1: 2}
        await engine.resolve_night(self.bot, game)
        group = "\n".join(c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id)
        self.assertIn("P2", group)
        self.assertNotIn("Komissar", group)

    async def test_history_logged_and_posted(self):
        game = self.register(make_game(Role.DON, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN))
        game.state = GameState.NIGHT
        game.mafia_votes = {1: 3}
        game.doctor_targets = {2: 4}
        game.players[3].items = {"shield": 1}
        await engine.resolve_night(self.bot, game)
        history = "\n".join(game.history)
        self.assertIn("P1 → P3", history)
        self.assertIn("P2 P4ni himoya qildi", history)
        self.assertIn("Himoya", history)
        with patch.multiple("economy.db", add_balance=AsyncMock(), record_game_result=AsyncMock(),
                            add_points=AsyncMock(), record_role_result=AsyncMock(), log_game=AsyncMock(return_value=1), log_player_game=AsyncMock(), is_group_premium=AsyncMock(return_value=False)), \
             patch.object(engine, "unlock_chat", AsyncMock()):
            game.history += ["x" * 300] * 30  # 4096 dan uzun — bo'linib yuboriladi
            await engine.finish_game(self.bot, game, "town")
        group = [c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id]
        self.assertTrue(all(len(t) <= 4096 for t in group))
        self.assertTrue(any(texts.HISTORY_HEADER in t for t in group))


class ReminderTest(unittest.IsolatedAsyncioTestCase):
    async def test_reminder_called_before_end(self):
        remind = AsyncMock()
        with patch.object(engine, "REMINDER_BEFORE_END", 0.02):
            await engine._wait_with_reminder(asyncio.Event(), 0.05, remind)
        remind.assert_awaited_once()

    async def test_no_reminder_when_done_early(self):
        event = asyncio.Event()
        event.set()
        remind = AsyncMock()
        with patch.object(engine, "REMINDER_BEFORE_END", 0.02):
            await engine._wait_with_reminder(event, 0.05, remind)
        remind.assert_not_awaited()


class VoteChangeTest(Registered):
    async def asyncSetUp(self):
        self.game = self.register(make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN))
        self.game.state = GameState.DAY_VOTING
        self.game.vote_needed = 4
        self.game.vote_event = asyncio.Event()
        self.announced = []
        p = patch.object(day, "announce", lambda bot, game, text: self.announced.append(text))
        p.start()
        self.addCleanup(p.stop)

    async def test_change_vote(self):
        await day.on_vote(cb(2, "vote:3"), self.bot)
        await day.on_vote(cb(2, "vote:4"), self.bot)
        self.assertEqual(self.game.day_votes, {2: 4})
        self.assertIn("ovozini", self.announced[-1])

    async def test_anonymous_votes(self):
        self.game.settings.open_votes = False
        await day.on_vote(cb(2, "vote:3"), self.bot)
        await day.on_vote(cb(2, "vote:4"), self.bot)
        self.assertEqual(self.announced, [texts.VOTE_ANNOUNCE_ANON])


class SettingsTest(unittest.TestCase):
    def test_actions_and_bounds(self):
        s = GroupSettings(night=20)
        group_settings.apply_action(s, ["t", "night", "-"])
        group_settings.apply_action(s, ["t", "night", "-"])
        self.assertEqual(s.night, 15)  # minimum
        group_settings.apply_action(s, ["role", "don"])
        self.assertEqual(s.disabled_roles, [])  # majburiy
        group_settings.apply_action(s, ["role", "doctor"])
        self.assertEqual(s.disabled_role_set(), {Role.DOCTOR})
        group_settings.apply_action(s, ["role", "doctor"])
        self.assertEqual(s.disabled_roles, [])
        group_settings.apply_action(s, ["p", "min", "-"])
        self.assertEqual(s.min_players, 4)
        for mode in ("fast", "noitems", "classic"):
            group_settings.apply_action(s, ["mode"])
            self.assertEqual(s.mode, mode)

    def test_auto_time_wraps(self):
        s = GroupSettings()
        group_settings.apply_action(s, ["auto", "toggle"])
        self.assertEqual(s.auto_time, "20:00")
        for _ in range(4):
            group_settings.apply_action(s, ["auto", "h", "+"])
        self.assertEqual(s.auto_time, "00:00")
        group_settings.apply_action(s, ["auto", "m", "-"])
        self.assertEqual(s.auto_time, "23:45")

    def test_modes(self):
        s = GroupSettings(night=40, mode="fast")
        self.assertEqual(s.seconds("night"), 20)
        s.mode = "noitems"
        self.assertFalse(s.items_active or s.hero_active)

    def test_json_roundtrip_ignores_unknown(self):
        s = GroupSettings(night=60, disabled_roles=["spy"])
        restored = GroupSettings.from_json(s.to_json().replace("{", '{"old_field": 1, ', 1))
        self.assertEqual(restored, s)

    def test_disabled_roles_distribution(self):
        c = Counter(build_role_list(12, {Role.DOCTOR, Role.KILLER}))
        self.assertEqual(c[Role.DOCTOR] + c[Role.KILLER], 0)
        self.assertEqual(sum(c.values()), 12)

    def test_all_views_render(self):
        s = GroupSettings(auto_time="08:30")
        for view in group_settings.VIEWS.values():
            text, kb = view(s)
            for row in kb.inline_keyboard:
                for b in row:
                    self.assertLessEqual(len(b.callback_data.encode()), 64)


class RolesCommandTest(unittest.TestCase):
    def test_all_roles_listed_within_limit(self):
        parts = common.build_roles_text()
        joined = "\n".join(parts)
        for role in Role:
            self.assertIn(texts.ROLE_NAMES[role], joined)
        self.assertTrue(all(len(p) <= 4096 for p in parts))

    def test_every_role_has_tip(self):
        self.assertEqual(set(texts.ROLE_TIPS), set(Role))


class LockModeTest(Registered):
    async def test_players_mode_does_not_lock(self):
        game = make_game(Role.DON, Role.CIVILIAN)
        game.settings.lock_mode = LOCK_PLAYERS
        game.settings.night = 0.01
        with patch.object(engine, "lock_chat", AsyncMock()) as lock, \
             patch.object(engine, "NIGHT_RESULTS_DELAY", 0), patch.object(engine, "send_phase_image", AsyncMock()):
            await engine.night_phase(self.bot, game)
        lock.assert_not_awaited()


class DbBacked(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "t.db"))
        self.p.start()
        await db.init_db()

    async def asyncTearDown(self):
        await db.close_db()
        self.p.stop()
        self.tmp.cleanup()


class DbFeaturesTest(DbBacked):
    async def test_settings_persist(self):
        s = GroupSettings(night=90, open_votes=False)
        await save_settings(-5, s)
        self.assertEqual(await load_settings(-5), s)
        self.assertEqual(await load_settings(-6), GroupSettings())

    async def test_points_rank(self):
        for uid, pts in ((1, 50), (2, 80), (3, 10)):
            await db.ensure_user(uid, f"U{uid}", None)
            await db.add_points(uid, pts)
        self.assertEqual(await db.points_rank(3), (3, 10))
        self.assertEqual(await db.points_rank(2), (1, 80))
        self.assertIsNone(await db.points_rank(99))

    async def test_role_stats(self):
        await db.record_role_result(1, "doctor", True)
        await db.record_role_result(1, "doctor", False)
        rows = await db.get_role_stats(1)
        self.assertEqual((rows[0]["role"], rows[0]["games"], rows[0]["wins"]), ("doctor", 2, 1))

    async def test_auto_game_opens_once(self):
        import autogame

        await save_settings(-77, GroupSettings(auto_time="09:15"))
        bot = make_bot()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
        bot.pin_chat_message = AsyncMock()
        now = datetime(2026, 10, 1, 9, 15)
        try:
            self.assertEqual(await autogame.open_due_lobbies(bot, now), [-77])
            self.assertIsNotNone(manager.get_game(-77))
            manager.remove_game(-77)
            self.assertEqual(await autogame.open_due_lobbies(bot, now), [])  # shu kuni qayta ochilmaydi
        finally:
            manager.remove_game(-77)


class LobbyJoinLeaveTest(DbBacked):
    async def test_deeplink_join_and_leave(self):
        bot = make_bot()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
        game = manager.create_game(-300, host_id=1)
        self.addCleanup(manager.remove_game, -300)
        user = MagicMock(id=42, full_name="Ali", username=None)
        self.assertEqual(await lobby.join_from_deeplink(bot, user, -300), texts.JOIN_VIA_START_OK)
        self.assertIn(42, game.players)
        self.assertIs(manager.get_game_by_player(42), game)

        await lobby.on_leave(cb(42, "lobby:leave", chat_id=-300), bot)
        self.assertNotIn(42, game.players)
        self.assertIsNone(manager.get_game_by_player(42))

    async def test_join_button_opens_bot_when_cannot_write(self):
        from aiogram.exceptions import TelegramForbiddenError

        bot = make_bot()
        bot.send_message = AsyncMock(side_effect=TelegramForbiddenError(MagicMock(), "blocked"))
        manager.create_game(-301, host_id=1)
        self.addCleanup(manager.remove_game, -301)
        c = cb(43, "lobby:join", chat_id=-301)
        await lobby.on_join(c, bot)
        self.assertEqual(c.answer.await_args.kwargs["url"], "https://t.me/test_bot?start=join_-301")

    async def test_closed_lobby(self):
        user = MagicMock(id=44, full_name="B", username=None)
        self.assertEqual(await lobby.join_from_deeplink(make_bot(), user, -999), texts.JOIN_VIA_START_CLOSED)


if __name__ == "__main__":
    unittest.main()
