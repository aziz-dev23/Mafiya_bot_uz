import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import texts
from economy import ITEMS
from game.manager import manager
from game.models import GameState, Role
from handlers import items, lobby, night
from i18n import LANGS, get_texts


def cb(user_id, data):
    c = MagicMock()
    c.from_user.id = user_id
    c.data = data
    c.answer = AsyncMock()
    c.message.edit_text = AsyncMock()
    return c


class FakeDocTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = patch.multiple(
            "game.engine.db", consume_item=AsyncMock(return_value=True), item_count=AsyncMock(return_value=0)
        )
        self.db.start()
        self.addCleanup(self.db.stop)
        self.bot = make_bot()

    def _game(self, target_role):
        game = make_game(Role.DETECTIVE, target_role, Role.CIVILIAN, Role.CIVILIAN)
        game.state = GameState.NIGHT
        game.players[2].items = {"fake_doc": 1}
        manager.games[game.chat_id] = game
        for uid in game.players:
            manager.register_player(game, uid)
        self.addCleanup(manager.remove_game, game.chat_id)
        return game

    async def _check(self, game):
        c = cb(1, "c_check:2")
        await night.on_detective_check(c, self.bot)
        return c.message.edit_text.await_args.args[0]

    async def test_mafia_owner_spends_and_fools(self):
        game = self._game(Role.MAFIA)
        result = await self._check(game)
        self.assertIn(texts.DETECTIVE_RESULT_CLEAN, result)
        self.assertEqual(game.players[2].items["fake_doc"], 0)

    async def test_civilian_owner_not_spent(self):
        game = self._game(Role.CIVILIAN)
        await self._check(game)
        self.assertEqual(game.players[2].items["fake_doc"], 1)

    async def test_lawyer_protection_first(self):
        game = self._game(Role.SPY)
        game.advokat_target = 2
        result = await self._check(game)
        self.assertIn(texts.DETECTIVE_RESULT_CLEAN, result)
        self.assertEqual(game.players[2].items["fake_doc"], 1)


class InventoryViewTest(unittest.TestCase):
    def test_rifle_has_no_toggle_and_states_are_marks(self):
        rows = [
            {"item_key": "rifle", "count": 2, "enabled": 1},
            {"item_key": "shield", "count": 1, "enabled": 0},
        ]
        text, kb = items.build_inventory_text_and_keyboard(rows)
        self.assertIn(texts.INVENTORY_RIFLE_LINE.format(count=2), text)
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertEqual(data, ["toggleitem:shield", "cosm:mine"])
        self.assertTrue(kb.inline_keyboard[0][0].text.startswith("❌"))

    def test_cards_render_in_all_languages(self):
        for lang in LANGS:
            L = get_texts(lang)
            for key in ITEMS:
                card = items.item_card(key, L)
                self.assertIn(L.ITEM_NAMES[key], card)
                self.assertLess(len(card), 4096)
            self.assertIn("🦸", items.hero_card(L))

    def test_store_has_info_buttons(self):
        kb = items.build_store_keyboard()
        rows = kb.inline_keyboard
        self.assertEqual([row[1].callback_data for row in rows[:-1]], [f"iteminfo:{k}" for k in ITEMS])
        self.assertEqual(rows[-1][0].callback_data, "cosm:store")


class RoleMessageTest(unittest.TestCase):
    def test_enabled_items_listed(self):
        game = make_game(Role.DON, Role.CIVILIAN)
        don = game.players[1]
        don.items = {"shield": 1}
        don.rifle_count = 2
        msg = lobby.build_role_message(don, game)
        self.assertIn(texts.ROLE_ITEMS_HEADER, msg)
        self.assertIn(texts.ITEM_NAMES["shield"], msg)
        self.assertIn(texts.ROLE_ITEMS_RIFLE.format(count=2), msg)

    def test_no_items_line(self):
        game = make_game(Role.CIVILIAN)
        self.assertIn(texts.ROLE_ITEMS_NONE, lobby.build_role_message(game.players[1], game))

    def test_no_items_mode_hides_block(self):
        game = make_game(Role.CIVILIAN)
        game.settings.mode = "noitems"
        msg = lobby.build_role_message(game.players[1], game)
        self.assertNotIn(texts.ROLE_ITEMS_NONE, msg)

    def test_hero_badge_in_lobby(self):
        game = make_game(Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].hero_badge = 7
        self.assertIn("🦸7", lobby.build_lobby_text(game))


if __name__ == "__main__":
    unittest.main()
