import unittest
from unittest.mock import AsyncMock, patch

from helpers import make_game

import economy
from game.models import Role


class DidWinTest(unittest.TestCase):
    def test_dead_member_of_winning_team_wins(self):
        game = make_game(Role.DON, Role.CIVILIAN)
        game.players[2].alive = False
        self.assertTrue(economy.did_win(game.players[2], "town"))
        self.assertFalse(economy.did_win(game.players[1], "town"))

    def test_killer_never_wins_with_town(self):
        game = make_game(Role.KILLER)
        self.assertFalse(economy.did_win(game.players[1], "town"))
        self.assertTrue(economy.did_win(game.players[1], "killer"))


class PayoutTest(unittest.IsolatedAsyncioTestCase):
    async def _payout(self, game, winner):
        with patch.multiple(
            "economy.db", add_balance=AsyncMock(), record_game_result=AsyncMock(), add_points=AsyncMock(),
            record_role_result=AsyncMock(),
        ):
            await economy.payout_game_results(game, winner)
            dollars = {c.args[0]: c.kwargs["dollars"] for c in economy.db.add_balance.await_args_list}
            points = {c.args[0]: c.args[1] for c in economy.db.add_points.await_args_list}
        return dollars, points

    async def test_amounts(self):
        game = make_game(Role.DON, Role.MAFIA, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].alive = False
        game.players[3].alive = False
        dollars, points = await self._payout(game, "mafia")
        self.assertEqual(dollars[1], economy.DOLLARS_WIN_MAFIA + economy.DOLLARS_ALIVE_WINNER_BONUS)
        self.assertEqual(dollars[2], economy.DOLLARS_WIN_MAFIA)
        self.assertEqual(dollars[3], economy.DOLLARS_LOSE)
        self.assertEqual(points[2], economy.POINTS_WIN)
        self.assertEqual(points[3], economy.POINTS_LOSE)

    async def test_win_always_beats_loss(self):
        self.assertGreater(economy.DOLLARS_WIN_OTHER, economy.DOLLARS_LOSE)
        self.assertGreater(economy.DOLLARS_WIN_MAFIA, economy.DOLLARS_LOSE)

    async def test_mvp_top3_in_big_game(self):
        game = make_game(Role.DON, *([Role.CIVILIAN] * 9))
        game.mvp = {2: 5, 3: 1, 4: 3, 5: 2, 1: 10}
        _, points = await self._payout(game, "town")
        self.assertEqual(points[2], economy.POINTS_TOP_BONUS)
        self.assertEqual(points[4], economy.POINTS_TOP_BONUS)
        self.assertEqual(points[5], economy.POINTS_TOP_BONUS)
        self.assertEqual(points[3], economy.POINTS_WIN)
        self.assertEqual(points[6], economy.POINTS_WIN)  # MVP 0 — bonus yo'q
        self.assertEqual(points[1], economy.POINTS_LOSE)  # Don yutqazdi, MVP hisobga olinmaydi

    async def test_no_mvp_bonus_in_small_game(self):
        game = make_game(Role.DON, *([Role.CIVILIAN] * 8))
        game.mvp = {2: 5}
        _, points = await self._payout(game, "town")
        self.assertEqual(points[2], economy.POINTS_WIN)


if __name__ == "__main__":
    unittest.main()
