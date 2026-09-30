import random

from .models import MAFIA_TEAM_ROLES, Game, Role

# Maxsus rollar ustuvorlik tartibida: (rol, shu rol paydo bo'ladigan minimal o'yinchi soni).
SPECIAL_ROLES = (
    (Role.DETECTIVE, 4),
    (Role.DOCTOR, 6),
    (Role.POISONER, 6),
    (Role.KILLER, 7),
    (Role.WANDERER, 7),
    (Role.HITMAN, 8),
    (Role.MINER, 8),
    (Role.LAWYER, 9),
    (Role.SORCERER, 10),
    (Role.WOLF, 11),
    # 40 kishilik o'yinlar uchun (40 kishida oddiy tinch aholi ~30% qoladi).
    (Role.SERGEANT, 20),
    (Role.DOCTOR, 22),  # ikkinchi Doktor
    (Role.JOURNALIST, 25),
    (Role.BODYGUARD, 27),
    (Role.SPY, 28),
    (Role.JUDGE, 30),
    (Role.CUPID, 32),
)
# O'yinchilarning kamida shuncha qismi oddiy aholi bo'lib qoladi.
MIN_CIVILIAN_SHARE = 0.2


def build_role_list(player_count: int, disabled: frozenset[Role] | set[Role] = frozenset()) -> list[Role]:
    """disabled — guruh sozlamalarida o'chirilgan maxsus rollar (ularning o'rni keyingi rollarga o'tadi)."""
    mafia_count = max(1, round(player_count * 0.25))
    while mafia_count * 2 >= player_count and mafia_count > 1:
        mafia_count -= 1

    # Har o'yinda aynan bitta Don, qolgan mafiyalar — oddiy Mafiya.
    roles = [Role.DON] + [Role.MAFIA] * (mafia_count - 1)

    min_civilians = max(1, round(player_count * MIN_CIVILIAN_SHARE))
    special_slots = player_count - len(roles) - min_civilians
    for role, min_players in SPECIAL_ROLES:
        if special_slots <= 0:
            break
        if player_count >= min_players and role not in disabled:
            roles.append(role)
            special_slots -= 1

    roles += [Role.CIVILIAN] * (player_count - len(roles))
    return roles


def assign_roles(game: Game) -> None:
    roles = build_role_list(len(game.players), game.settings.disabled_role_set())
    random.shuffle(roles)
    for player, role in zip(game.players.values(), roles):
        player.role = role
        player.initial_role = role

    # Yollanma qotilga maxfiy buyurtma nishoni tayinlanadi (Mafiya jamoasidan emas).
    hitmen = [p for p in game.players.values() if p.role == Role.HITMAN]
    for hitman in hitmen:
        candidates = [p for p in game.players.values() if p.role not in MAFIA_TEAM_ROLES]
        if candidates:
            hitman.contract_target = random.choice(candidates).user_id
