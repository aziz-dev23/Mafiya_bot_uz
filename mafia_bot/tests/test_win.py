import unittest

from helpers import make_game

from game.engine import check_win
from game.models import Role


def kill(game, *ids):
    for i in ids:
        game.players[i].alive = False


class CheckWinTest(unittest.TestCase):
    def test_game_continues(self):
        game = make_game(Role.DON, Role.DETECTIVE, Role.CIVILIAN, Role.CIVILIAN)
        self.assertIsNone(check_win(game))

    def test_town_wins_when_mafia_and_killer_dead(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN, Role.CIVILIAN)
        kill(game, 1, 2)
        self.assertEqual(check_win(game), "town")

    def test_town_does_not_win_while_killer_alive(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN, Role.CIVILIAN)
        kill(game, 1)
        self.assertIsNone(check_win(game))

    def test_killer_alone_wins(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN)
        kill(game, 1, 3)
        self.assertEqual(check_win(game), "killer")

    def test_killer_wins_one_on_one(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN)
        kill(game, 1)
        self.assertEqual(check_win(game), "killer")

    def test_mafia_beats_killer_one_on_one(self):
        game = make_game(Role.DON, Role.KILLER, Role.CIVILIAN)
        kill(game, 3)
        self.assertEqual(check_win(game), "mafia")

    def test_mafia_parity_wins(self):
        game = make_game(Role.DON, Role.HITMAN, Role.CIVILIAN, Role.CIVILIAN, Role.DETECTIVE)
        kill(game, 5)
        self.assertEqual(check_win(game), "mafia")

    def test_lawyer_and_hitman_count_as_mafia(self):
        game = make_game(Role.DON, Role.LAWYER, Role.CIVILIAN, Role.CIVILIAN)
        kill(game, 1)
        self.assertIsNone(check_win(game))  # Advokat tirik — tinch aholi hali yutmagan


if __name__ == "__main__":
    unittest.main()
