import db
from game.models import Game, Role

# NOTE: exact XP-per-level thresholds and per-game payout amounts are not
# specified anywhere the bot was given as a source — these are reasonable
# defaults, tune freely via this file.
LEVEL_XP_THRESHOLDS = {1: 0, 2: 100, 3: 300, 4: 700, 5: 1500}
LEVEL_CAPACITY = {1: 10, 2: 15, 3: 20, 4: 25, 5: 30}
LEVEL_BONUS_PCT = {1: 0, 2: 5, 3: 10, 4: 15, 5: 25}
LEVEL_NAMES = {
    1: "Boshlang'ich oila",
    2: "Tashkiliy to'da",
    3: "Sitsiliya sindikati",
    4: "Bosh mafiya ittifoqi",
    5: "Afsonaviy Kamorra",
}

CLAN_CREATE_COST_DIAMONDS = 30
CLAN_CREATE_COST_DOLLARS = 50_000

# (olmos miqdori, narxi so'mda) — o'zingizga mos narxlarni shu yerda o'zgartiring
DIAMOND_PACKAGES = [
    (1, 1_350),
    (5, 6_500),
    (10, 12_500),
    (15, 18_000),
    (30, 34_500),
    (50, 55_000),
    (200, 200_000),
    (500, 450_000),
    (1000, 800_000),
    (2000, 1_400_000),
]

DOLLARS_WIN_ALIVE = 1000
DOLLARS_WIN_DEAD = 400
DOLLARS_LOSE = 150

CURRENCY_COLUMN = {"dollar": "dollars", "diamond": "diamonds", "coin": "coins"}
CURRENCY_EMOJI = {"dollar": "💵", "diamond": "💎", "coin": "🪙"}
CURRENCY_ALIASES = {
    "dollar": "dollar",
    "dollars": "dollar",
    "$": "dollar",
    "dol": "dollar",
    "diamond": "diamond",
    "diamonds": "diamond",
    "gem": "diamond",
    "olmos": "diamond",
    "💎": "diamond",
    "coin": "coin",
    "coins": "coin",
    "tanga": "coin",
    "🪙": "coin",
}


def parse_currency(token: str) -> str | None:
    return CURRENCY_ALIASES.get(token.lower())


def clan_level(xp: int) -> int:
    level = 1
    for lvl, threshold in sorted(LEVEL_XP_THRESHOLDS.items()):
        if xp >= threshold:
            level = lvl
    return level


def clan_capacity(level: int) -> int:
    return LEVEL_CAPACITY.get(level, LEVEL_CAPACITY[5])


def clan_bonus_pct(level: int) -> int:
    return LEVEL_BONUS_PCT.get(level, LEVEL_BONUS_PCT[5])


async def payout_game_results(game: Game, winner: str) -> list[str]:
    lines: list[str] = []
    for p in game.players.values():
        won = (winner == "mafia" and p.role == Role.MAFIA) or (winner == "town" and p.role != Role.MAFIA)
        base = (DOLLARS_WIN_ALIVE if p.alive else DOLLARS_WIN_DEAD) if won else DOLLARS_LOSE

        bonus_pct = 0
        clan_row = await db.get_user_clan(p.user_id)
        if clan_row:
            bonus_pct = clan_bonus_pct(clan_level(clan_row["xp"]))
        total = base + (base * bonus_pct // 100)

        await db.add_balance(p.user_id, dollars=total)
        await db.record_game_result(p.user_id, won)

        bonus_note = " (klan bonusi bilan)" if bonus_pct else ""
        lines.append(f"• {p.full_name}: +{total}💵{bonus_note}")
    return lines
