"""To'liq o'yin simulyatsiyasi: soxta bot, haqiqiy handlerlar, o'yinchilar tugmalarni tasodifiy bosadi.
Maqsad — har xil sondagi o'yinchilar bilan o'yin xatoliksiz oxirigacha yetib borishini tekshirish."""
import asyncio
import inspect
import itertools
import random
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_game  # noqa: F401  (sys.path sozlaydi)

from game import engine
from game.manager import manager
from game.models import Game, GameState, Player
from game.roles import assign_roles
from handlers import day, night

HANDLERS = {
    "m_kill": night.on_mafia_kill,
    "d_save": night.on_doctor_save,
    "c_check": night.on_detective_check,
    "q_kill": night.on_killer_kill,
    "yq_kill": night.on_hitman_kill,
    "kez_dose": night.on_poisoner_dose,
    "daydi_visit": night.on_wanderer_visit,
    "don_check": night.on_don_check,
    "advokat_shield": night.on_advokat_shield,
    "guard": night.on_bodyguard,
    "spy": night.on_spy,
    "jur1": night.on_journalist_first,
    "jur2": night.on_journalist_second,
    "cupid1": night.on_cupid_first,
    "cupid2": night.on_cupid_second,
    "guess": night.on_guess,
    "hero_shot": night.on_hero_shot,
    "sorcerer_revenge": night.on_sorcerer_revenge,
    "judge_cancel": night.on_judge_cancel,
    "vote": day.on_vote,
    "confirm": day.on_confirm,
}


class FakeBot:
    """Yuborilgan tugmali xabarlarni eslab qoladi — "o'yinchilar" ularni bosadi."""

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.ids = itertools.count(1)
        self.pending: list[tuple[int, object]] = []  # (user_id yoki chat_id, markup)
        self.sent = 0
        self.pressed: set[str] = set()
        self.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
        self.delete_message = AsyncMock()
        self.edit_message_text = AsyncMock()
        self.send_photo = AsyncMock(side_effect=self._send_photo)

    async def _send_photo(self, chat_id, photo=None, caption=None, reply_markup=None):
        return MagicMock(photo=None)

    async def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self.sent += 1
        assert len(text) <= 4096, "Telegram limiti: xabar juda uzun"
        if reply_markup is not None and getattr(reply_markup, "inline_keyboard", None):
            self.pending.append((chat_id, reply_markup))
        return MagicMock(message_id=next(self.ids))


def _callback(bot: FakeBot, user_id: int, data: str, chat_id: int) -> MagicMock:
    cb = MagicMock()
    cb.from_user.id = user_id
    cb.data = data
    cb.answer = AsyncMock()
    cb.message.chat.id = chat_id

    async def edit_text(text, reply_markup=None, **kwargs):
        if reply_markup is not None:
            bot.pending.append((user_id, reply_markup))

    cb.message.edit_text = AsyncMock(side_effect=edit_text)
    cb.message.edit_reply_markup = AsyncMock()
    return cb


async def _press(bot: FakeBot, game: Game, owner: int, markup) -> None:
    buttons = [b for row in markup.inline_keyboard for b in row if b.callback_data]
    if not buttons:
        return
    presser_ids = (
        [p.user_id for p in game.players.values() if p.alive] if owner == game.chat_id else [owner]
    )
    for presser in presser_ids:
        if random.random() < 0.15:  # ba'zilar hech narsa bosmaydi (AFK)
            continue
        button = random.choice(buttons)
        prefix = button.callback_data.split(":", 1)[0]
        handler = HANDLERS.get(prefix)
        if handler is None:
            continue
        bot.pressed.add(prefix)
        cb = _callback(bot, presser, button.callback_data, game.chat_id)
        kwargs = {"bot": bot} if "bot" in inspect.signature(handler).parameters else {}
        await handler(cb, **kwargs)


async def _players(bot: FakeBot, game: Game) -> None:
    while True:
        await asyncio.sleep(0.001)
        while bot.pending:
            owner, markup = bot.pending.pop(0)
            await _press(bot, game, owner, markup)


# Tezlashtirilgan vaqtlar: modul konstantalari va guruh sozlamalari.
MODULE_FAST = {
    ("game.engine", "NIGHT_RESULTS_DELAY"): 0,
    ("game.engine", "ANNOUNCE_BATCH_DELAY"): 0,
    ("game.settings", "REVENGE_DURATION"): 0.02,
    ("game.settings", "JUDGE_DURATION"): 0.02,
    ("game.settings", "LAST_WORD_DURATION"): 0.02,
    ("game.settings", "DAY_DISCUSSION_PER_PLAYER"): 0,
    ("game.settings", "VOTE_PER_PLAYER"): 0,
}
SETTINGS_FAST = {"night": 0.05, "dawn": 0.01, "discussion": 0, "vote": 0.05, "confirm": 0.03}


class SimulationTest(unittest.IsolatedAsyncioTestCase):
    async def _play(self, n_players: int, seed: int) -> Game:
        random.seed(seed)
        chat_id = -1000 - seed
        bot = FakeBot(chat_id)
        game = manager.create_game(chat_id, host_id=1)
        for uid in range(1, n_players + 1):
            game.players[uid] = Player(user_id=uid, full_name=f"P{uid}")
            manager.register_player(game, uid)
        assign_roles(game)
        # Ba'zilarga buyum va Geroy beramiz
        for p in game.players.values():
            if random.random() < 0.3:
                p.items = {k: 1 for k in random.sample(["shield", "mirror", "killer_shield", "mask", "fake_doc",
                                                         "vote_shield", "poison_shield", "rifle"], 3)}
            if random.random() < 0.1:
                p.hero_level = random.choice([1, 10])

        for key, value in SETTINGS_FAST.items():
            setattr(game.settings, key, value)
        if seed % 2 == 0:
            # Juft seed'larda boshqa guruh sozlamalari bilan o'ynaymiz.
            game.settings.reveal_roles = False
            game.settings.open_votes = False
            game.settings.hero_enabled = False
            game.settings.last_word = False
            game.settings.lock_mode = "players"
        patches = [patch(f"{module}.{name}", value) for (module, name), value in MODULE_FAST.items()]
        patches += [
            patch.object(engine, "lock_chat", AsyncMock()),
            patch.object(engine, "unlock_chat", AsyncMock()),
            patch.multiple("db", consume_item=AsyncMock(return_value=True), add_balance=AsyncMock(),
                           add_item=AsyncMock(), record_game_result=AsyncMock(), add_points=AsyncMock(),
                           record_role_result=AsyncMock()),
        ]
        for p in patches:
            p.start()
        clicker = asyncio.create_task(_players(bot, game))
        try:
            task = asyncio.create_task(engine.run_game(bot, game))
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=30)
            except asyncio.CancelledError:
                pass  # finish_game o'z vazifasini remove_game orqali bekor qiladi
        finally:
            crashed = clicker.done() and not clicker.cancelled() and clicker.exception()
            clicker.cancel()
            for p in patches:
                p.stop()
            manager.remove_game(chat_id)
        if crashed:
            raise crashed
        self.pressed.update(bot.pressed)
        return game

    async def test_games_finish(self):
        self.pressed: set[str] = set()
        for n, seed in [(4, 1), (6, 2), (8, 3), (12, 4), (17, 5), (25, 6), (33, 7), (40, 8), (40, 9), (40, 10)]:
            with self.subTest(players=n, seed=seed):
                with self.assertLogs("game.engine", level="ERROR") as logs:
                    engine.logger.error("marker")  # assertLogs bo'sh bo'lsa xato beradi
                    game = await self._play(n, seed)
                self.assertEqual(logs.output, ["ERROR:game.engine:marker"], logs.output)
                self.assertEqual(game.state, GameState.FINISHED, f"{n} kishilik o'yin tugamadi")
                self.assertIsNotNone(engine.check_win(game))
        # Deyarli barcha tugmalar kamida bir marta bosilgan bo'lishi kerak.
        rare = {"hero_shot", "sorcerer_revenge", "judge_cancel"}
        self.assertEqual(set(HANDLERS) - rare - self.pressed, set())


if __name__ == "__main__":
    unittest.main()
