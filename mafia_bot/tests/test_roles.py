import unittest
from collections import Counter

from helpers import make_game

from game.models import MAFIA_TEAM_ROLES, Role
from game.roles import MIN_CIVILIAN_SHARE, assign_roles, build_role_list


class RoleListTest(unittest.TestCase):
    def test_counts_for_all_sizes(self):
        for n in range(4, 41):
            with self.subTest(players=n):
                roles = build_role_list(n)
                c = Counter(roles)
                self.assertEqual(len(roles), n)
                self.assertEqual(c[Role.DON], 1)
                mafia = c[Role.DON] + c[Role.MAFIA]
                self.assertLess(mafia * 2, n)
                self.assertGreaterEqual(c[Role.CIVILIAN], max(1, round(n * MIN_CIVILIAN_SHARE)))
                self.assertEqual(c[Role.DETECTIVE], 1)

    def test_four_players(self):
        self.assertEqual(Counter(build_role_list(4)), Counter({Role.DON: 1, Role.DETECTIVE: 1, Role.CIVILIAN: 2}))

    def test_all_special_roles_at_17(self):
        c = Counter(build_role_list(17))
        for role in (Role.DOCTOR, Role.POISONER, Role.KILLER, Role.WANDERER, Role.HITMAN,
                     Role.MINER, Role.LAWYER, Role.SORCERER, Role.WOLF):
            self.assertEqual(c[role], 1, role)


class HitmanContractTest(unittest.TestCase):
    def test_contract_never_targets_mafia_team(self):
        for _ in range(300):
            game = make_game(*([Role.CIVILIAN] * 12))
            assign_roles(game)
            for p in game.players.values():
                if p.role == Role.HITMAN:
                    target = game.players[p.contract_target]
                    self.assertNotIn(target.role, MAFIA_TEAM_ROLES)


if __name__ == "__main__":
    unittest.main()
