import random

from .models import Game, Role


def build_role_list(player_count: int) -> list[Role]:
    mafia_count = max(1, round(player_count * 0.25))
    while mafia_count * 2 >= player_count and mafia_count > 1:
        mafia_count -= 1

    detective_count = 1 if player_count >= 5 else 0
    doctor_count = 1 if player_count >= 6 else 0

    special = mafia_count + detective_count + doctor_count
    civilian_count = max(0, player_count - special)

    roles = (
        [Role.MAFIA] * mafia_count
        + [Role.DETECTIVE] * detective_count
        + [Role.DOCTOR] * doctor_count
        + [Role.CIVILIAN] * civilian_count
    )
    return roles


def assign_roles(game: Game) -> None:
    roles = build_role_list(len(game.players))
    random.shuffle(roles)
    for player, role in zip(game.players.values(), roles):
        player.role = role
