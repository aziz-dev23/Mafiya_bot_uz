import unittest
from unittest.mock import AsyncMock, patch

from helpers import make_bot, make_game, private_texts

import texts
from game import engine
from game.models import GameState, Role


class NightTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = patch.multiple(
            "game.engine.db",
            consume_item=AsyncMock(return_value=True),
            add_balance=AsyncMock(),
            add_item=AsyncMock(), item_count=AsyncMock(return_value=0),
        )
        self.db.start()
        self.bot = make_bot()

    def tearDown(self):
        self.db.stop()


class MafiaKillTest(NightTestCase):
    async def test_mafia_kill_records_voter_as_killer(self):
        game = make_game(Role.DON, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 3, 2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[3].alive)
        self.assertIn(game.night_kills[3], (1, 2))
        self.assertEqual(game.mvp, {1: 1, 2: 1})

    async def test_doctor_save(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 3}
        game.doctor_targets = {2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[3].alive)
        self.assertEqual(game.night_kills, {})
        self.assertEqual(game.mvp, {2: 3})

    async def test_wolf_turns_mafia(self):
        game = make_game(Role.DON, Role.WOLF, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive)
        self.assertEqual(game.players[2].role, Role.MAFIA)

    async def test_shield_saves_once(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].items = {"shield": 1}
        game.mafia_votes = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive)
        self.assertTrue(game.players[2].shield_used)

    async def test_rifle_pierces_shield(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].rifle_count = 1
        game.players[2].items = {"shield": 1}
        game.mafia_votes = {1: 2}
        game.mafia_rifle_users = {1}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[2].alive)
        self.assertTrue(game.players[1].rifle_used)
        self.assertEqual(game.players[2].items["shield"], 1)  # teshilgan Himoya sarflanmaydi

    async def test_rifle_not_spent_without_shield(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].rifle_count = 1
        game.mafia_votes = {1: 2}
        game.mafia_rifle_users = {1}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[1].rifle_used)
        self.assertEqual(game.players[1].rifle_count, 1)

    async def test_rifle_prefers_don_and_ignores_other_target(self):
        game = make_game(Role.DON, Role.MAFIA, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        for uid in (1, 2, 3):
            game.players[uid].rifle_count = 1
        game.players[4].items = {"shield": 1}
        game.mafia_votes = {1: 4, 2: 4, 3: 5}
        game.mafia_rifle_users = {1, 2, 3}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[4].alive)
        self.assertTrue(game.players[1].rifle_used)
        self.assertFalse(game.players[2].rifle_used)
        self.assertFalse(game.players[3].rifle_used)

    async def test_rifle_disabled_in_no_items_mode(self):
        game = make_game(Role.DON, Role.CIVILIAN)
        game.players[1].rifle_count = 1
        game.settings.mode = "noitems"
        self.assertFalse(engine.rifle_available(game, game.players[1]))

    async def test_attackers_told_target_survived(self):
        game = make_game(Role.DON, Role.LAWYER, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 4}
        game.doctor_targets = {3: 4}
        await engine.resolve_night(self.bot, game)
        for uid in (1, 2):
            self.assertIn(texts.TARGET_SURVIVED, private_texts(self.bot, uid))

    async def test_mirror_bounces_to_voter(self):
        game = make_game(Role.DON, Role.LAWYER, Role.CIVILIAN, Role.CIVILIAN)
        game.players[3].items = {"mirror": 1}
        game.mafia_votes = {1: 3}
        game.state = engine.GameState.NIGHT
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[3].alive)
        self.assertFalse(game.players[1].alive)  # ovoz bergan Don
        self.assertTrue(game.players[2].alive)  # Advokat ovoz bermagan
        self.assertEqual(game.night_kills[1], 3)
        group = "\n".join(c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id)
        self.assertNotIn("🔮", group)
        self.assertIn(texts.ITEM_USED["mirror"].format(left=0), private_texts(self.bot, 3))

    async def test_sorcerer_drags_mafia(self):
        game = make_game(Role.DON, Role.SORCERER, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[2].alive)
        self.assertFalse(game.players[1].alive)
        self.assertEqual(game.mvp.get(2), 3)


class SoloKillersTest(NightTestCase):
    async def test_killer_blocked_by_killer_shield(self):
        game = make_game(Role.KILLER, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].items = {"killer_shield": 1}
        game.killer_target = 2
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive)

    async def test_hitman_contract_bonus_and_mvp(self):
        game = make_game(Role.DON, Role.HITMAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].contract_target = 3
        game.hitman_target = 3
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[3].alive)
        self.assertEqual(game.night_kills[3], 2)
        self.assertEqual(game.mvp.get(2), 3)
        engine.db.add_balance.assert_awaited_with(2, dollars=engine.HITMAN_CONTRACT_BONUS_DOLLARS)


class WandererTest(NightTestCase):
    def _game(self):
        game = make_game(Role.DON, Role.WANDERER, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.mafia_votes = {1: 3}
        game.wanderer_target = 3
        return game

    async def test_learns_killer_name(self):
        game = self._game()
        await engine.resolve_night(self.bot, game)
        msgs = private_texts(self.bot, 2)
        self.assertTrue(any("P1" in m and "P3" in m for m in msgs), msgs)
        self.assertEqual(game.mvp.get(2), 2)

    async def test_mask_on_killer_hides(self):
        game = self._game()
        game.players[1].items = {"mask": 1}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(private_texts(self.bot, 2), [texts.WANDERER_SAW_NOTHING.format(victim="P3")])
        self.assertEqual(game.players[1].items["mask"], 0)

    async def test_mask_on_victim_does_nothing(self):
        game = self._game()
        game.players[3].items = {"mask": 1}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(any("P1" in m for m in private_texts(self.bot, 2)))
        self.assertEqual(game.players[3].items["mask"], 1)

    async def test_learns_solo_killer(self):
        game = make_game(Role.KILLER, Role.WANDERER, Role.CIVILIAN, Role.CIVILIAN)
        game.killer_target = 3
        game.wanderer_target = 3
        await engine.resolve_night(self.bot, game)
        self.assertTrue(any("P1" in m for m in private_texts(self.bot, 2)))

    async def test_nothing_if_visited_survives(self):
        game = self._game()
        game.wanderer_target = 4
        await engine.resolve_night(self.bot, game)
        self.assertEqual(private_texts(self.bot, 2), [])


class MinerTest(NightTestCase):
    async def _dig(self, roll):
        game = make_game(Role.DON, Role.MINER, Role.CIVILIAN, Role.CIVILIAN)
        with patch.object(engine.random, "random", return_value=roll), \
             patch.object(engine.random, "randint", return_value=3), \
             patch.object(engine.random, "choice", return_value="mask"):
            await engine.resolve_night(self.bot, game)
        return private_texts(self.bot, 2)

    async def test_coins(self):
        msgs = await self._dig(0.1)
        engine.db.add_balance.assert_awaited_with(2, coins=3)
        self.assertEqual(len(msgs), 1)

    async def test_item(self):
        await self._dig(0.65)
        engine.db.add_item.assert_awaited_with(2, "mask", 1)

    async def test_nothing(self):
        msgs = await self._dig(0.9)
        engine.db.add_balance.assert_not_awaited()
        engine.db.add_item.assert_not_awaited()
        self.assertEqual(msgs, [texts.MINER_FOUND_NOTHING])


class PoisonTest(NightTestCase):
    async def test_poison_kills_next_night(self):
        game = make_game(Role.DON, Role.POISONER, Role.CIVILIAN, Role.CIVILIAN)
        game.day_number = 2
        game.pending_poison = {3: 2}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[3].alive)
        self.assertEqual(game.night_kills[3], 2)

    async def test_doctor_blocks_poison(self):
        game = make_game(Role.DON, Role.POISONER, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.day_number = 2
        game.pending_poison = {4: 2}
        game.doctor_targets = {3: 4}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[4].alive)
        self.assertEqual(game.mvp.get(3), 3)
        self.assertEqual(game.pending_poison, {})


class DoctorLimitsTest(NightTestCase):
    async def test_forbidden_after_nights(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.doctor_targets = {2: 2}  # o'zini himoya qildi
        await engine.resolve_night(self.bot, game)
        self.assertEqual(engine.doctor_forbidden_ids(game, 2), {2})
        game.doctor_targets = {2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(engine.doctor_forbidden_ids(game, 2), {2, 3})
        game.doctor_targets = {}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(engine.doctor_forbidden_ids(game, 2), {2})


class ItemLimitTest(NightTestCase):
    async def test_killer_shield_is_consumed(self):
        game = make_game(Role.KILLER, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].items = {"killer_shield": 1}
        game.killer_target = 2
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive)
        engine.db.consume_item.assert_awaited_with(2, "killer_shield")
        game.killer_target = 2
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[2].alive)

    async def test_hero_shoots_once_per_game(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].hero_level = 1
        game.hero_shots = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[2].alive)
        self.assertFalse(engine.hero_can_shoot(game, game.players[1]))

    async def test_hero_shot_kept_if_target_already_dead(self):
        game = make_game(Role.DON, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].hero_level = 1
        game.mafia_votes = {1: 3, 2: 3}
        game.hero_shots = {1: 3}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[3].alive)
        self.assertTrue(engine.hero_can_shoot(game, game.players[1]))
        self.assertIn(texts.HERO_SHOT_KEPT, private_texts(self.bot, 1))

    async def test_mirror_kills_hero_shooter(self):
        game = make_game(Role.DETECTIVE, Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].hero_level = 3
        game.players[2].items = {"mirror": 1}
        game.hero_shots = {1: 2}
        game.state = engine.GameState.NIGHT
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[2].alive)
        self.assertFalse(game.players[1].alive)
        group = "\n".join(c.args[1] for c in self.bot.send_message.call_args_list if c.args[0] == game.chat_id)
        self.assertNotIn("🔮", group)  # guruhga buyum nomi aytilmaydi

    async def test_hero_level_10_ignores_protection(self):
        game = make_game(Role.DON, Role.CIVILIAN, Role.CIVILIAN, Role.CIVILIAN)
        game.players[1].hero_level = 10
        game.players[2].items = {"mirror": 1, "hero_immunity": 1}
        game.hero_shots = {1: 2}
        await engine.resolve_night(self.bot, game)
        self.assertFalse(game.players[2].alive)
        self.assertEqual(game.players[2].items, {"mirror": 1, "hero_immunity": 1})


class ItemRulesTest(NightTestCase):
    async def test_poison_shield_not_spent_when_doctor_heals(self):
        game = make_game(Role.DON, Role.POISONER, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.day_number = 2
        game.pending_poison = {4: 2}
        game.doctor_targets = {3: 4}
        game.players[4].items = {"poison_shield": 1}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[4].alive)
        self.assertEqual(game.players[4].items["poison_shield"], 1)

    async def test_poison_shield_saves(self):
        game = make_game(Role.DON, Role.POISONER, Role.CIVILIAN, Role.CIVILIAN)
        game.day_number = 2
        game.pending_poison = {3: 2}
        game.players[3].items = {"poison_shield": 1}
        await engine.resolve_night(self.bot, game)
        self.assertTrue(game.players[3].alive)
        self.assertEqual(private_texts(self.bot, 2), [])  # Kezuvchi hech narsa bilmaydi

    async def test_shield_not_spent_when_doctor_saves(self):
        game = make_game(Role.DON, Role.DOCTOR, Role.CIVILIAN, Role.CIVILIAN)
        game.players[3].items = {"shield": 1}
        game.mafia_votes = {1: 3}
        game.doctor_targets = {2: 3}
        await engine.resolve_night(self.bot, game)
        self.assertEqual(game.players[3].items["shield"], 1)


if __name__ == "__main__":
    unittest.main()
