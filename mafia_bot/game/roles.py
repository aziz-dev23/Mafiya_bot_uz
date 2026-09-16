import random

from .models import Game, Role


def build_role_list(player_count: int) -> list[Role]:
    mafia_count = max(1, round(player_count * 0.25))
    while mafia_count * 2 >= player_count and mafia_count > 1:
        mafia_count -= 1

    detective_count = 1 if player_count >= 5 else 0
    doctor_count = 1 if player_count >= 6 else 0
    poisoner_count = 1 if player_count >= 6 else 0
    killer_count = 1 if player_count >= 7 else 0
    wanderer_count = 1 if player_count >= 7 else 0
    hitman_count = 1 if player_count >= 8 else 0
    miner_count = 1 if player_count >= 8 else 0
    lawyer_count = 1 if player_count >= 9 else 0
    sorcerer_count = 1 if player_count >= 10 else 0
    wolf_count = 1 if player_count >= 11 else 0

    special = (
        mafia_count
        + detective_count
        + doctor_count
        + poisoner_count
        + killer_count
        + wanderer_count
        + hitman_count
        + miner_count
        + lawyer_count
        + sorcerer_count
        + wolf_count
    )
    civilian_count = max(0, player_count - special)

    roles = (
        [Role.MAFIA] * mafia_count
        + [Role.DETECTIVE] * detective_count
        + [Role.DOCTOR] * doctor_count
        + [Role.POISONER] * poisoner_count
        + [Role.KILLER] * killer_count
        + [Role.WANDERER] * wanderer_count
        + [Role.HITMAN] * hitman_count
        + [Role.MINER] * miner_count
        + [Role.LAWYER] * lawyer_count
        + [Role.SORCERER] * sorcerer_count
        + [Role.WOLF] * wolf_count
        + [Role.CIVILIAN] * civilian_count
    )
    return roles


def assign_roles(game: Game) -> None:
    roles = build_role_list(len(game.players))
    random.shuffle(roles)
    for player, role in zip(game.players.values(), roles):
        player.role = role

    # Mafiya jamoasidan biri Don bo'ladi (kichik o'yinlarda yagona mafiya "oddiy" qoladi).
    mafia_players = [p for p in game.players.values() if p.role == Role.MAFIA]
    if len(mafia_players) >= 2:
        random.choice(mafia_players).role = Role.DON

    # Yollanma qotilga maxfiy buyurtma nishoni tayinlanadi.
    hitmen = [p for p in game.players.values() if p.role == Role.HITMAN]
    for hitman in hitmen:
        candidates = [p for p in game.players.values() if p.user_id != hitman.user_id]
        if candidates:
            hitman.contract_target = random.choice(candidates).user_id
