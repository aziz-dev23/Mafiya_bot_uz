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
DETECTIVE_BONUS_DOLLARS = 200
KILLER_SOLO_WIN_DOLLARS = 5000
HITMAN_CONTRACT_BONUS_DOLLARS = 2000
MINER_SLIP_CHANCE = 0.20

# Bosqich 1 buyumlari — Mafiya/Doktor/Komissar/Tinch aholi bilan ishlaydiganlar.
ITEMS = {
    "shield": {"name": "Himoya", "emoji": "🛡", "price": 100, "currency": "dollar"},
    "fake_doc": {"name": "Soxta hujjat", "emoji": "📁", "price": 190, "currency": "dollar"},
    "vote_shield": {"name": "Ovozdan himoya", "emoji": "⚖️", "price": 1, "currency": "diamond"},
    "rifle": {"name": "Miltiq", "emoji": "🔫", "price": 1, "currency": "diamond"},
    "mirror": {"name": "Sehrli oyna", "emoji": "🔮", "price": 1000, "currency": "diamond"},
    # Bosqich 2 buyumlari — yangi rollarga (Qotil/Yollanma qotil/Kezuvchi/Daydi/Konchi) bog'liq.
    "killer_shield": {"name": "Qotildan himoya", "emoji": "⛑", "price": 2, "currency": "diamond"},
    "poison_shield": {"name": "Doridan himoya", "emoji": "💊", "price": 100, "currency": "dollar"},
    "mask": {"name": "Maska", "emoji": "🎭", "price": 100, "currency": "dollar"},
    "miner_shield": {"name": "Sirpanishdan himoya", "emoji": "🪤", "price": 300, "currency": "dollar"},
    "hero_shot": {"name": "Geroy", "emoji": "🥷", "price": 90, "currency": "diamond"},
    "hero_immunity": {"name": "Geroydan himoya", "emoji": "🔰", "price": 5, "currency": "diamond"},
}

# Bir o'yin ichida cheksiz marta ishlaydigan (sarflanmaydigan) buyumlar.
UNLIMITED_ITEMS = {"killer_shield"}

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


MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON)


def _did_win(role: Role, winner: str) -> bool:
    if winner == "killer":
        return role == Role.KILLER
    if winner == "mafia":
        return role in MAFIA_TEAM_ROLES
    # town — Yollanma qotil alohida g'alaba sharti yo'q, tomon natijasiga qo'shiladi
    return role not in MAFIA_TEAM_ROLES and role != Role.KILLER


async def payout_game_results(game: Game, winner: str) -> list[str]:
    lines: list[str] = []
    for p in game.players.values():
        won = _did_win(p.role, winner)

        if winner == "killer" and p.role == Role.KILLER:
            total = KILLER_SOLO_WIN_DOLLARS
            await db.add_balance(p.user_id, dollars=total)
            await db.record_game_result(p.user_id, won)
            lines.append(f"• {p.full_name}: +{total}💵 (🔪 yakka g'alaba!)")
            continue

        base = (DOLLARS_WIN_ALIVE if p.alive else DOLLARS_WIN_DEAD) if won else DOLLARS_LOSE

        bonus_pct = 0
        clan_row = await db.get_user_clan(p.user_id)
        if clan_row:
            bonus_pct = clan_bonus_pct(clan_level(clan_row["xp"]))
        total = base + (base * bonus_pct // 100)

        detective_bonus = 0
        if p.role == Role.DETECTIVE and getattr(game, "detective_correct", False):
            detective_bonus = DETECTIVE_BONUS_DOLLARS
            total += detective_bonus

        await db.add_balance(p.user_id, dollars=total)
        await db.record_game_result(p.user_id, won)

        notes = []
        if bonus_pct:
            notes.append("klan bonusi")
        if detective_bonus:
            notes.append(f"🕵️ komissar bonusi +{detective_bonus}💵")
        note = f" ({', '.join(notes)})" if notes else ""
        lines.append(f"• {p.full_name}: +{total}💵{note}")
    return lines
