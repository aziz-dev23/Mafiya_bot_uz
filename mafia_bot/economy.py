import db
from game.models import Game, Role
from texts import ROLE_NAMES

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

DOLLARS_WIN_MAFIA = 35
DOLLARS_WIN_OTHER = 20
DOLLARS_LOSE = 25
DETECTIVE_BONUS_DOLLARS = 200
KILLER_SOLO_WIN_DOLLARS = 5000
HITMAN_CONTRACT_BONUS_DOLLARS = 2000

# 1 olmos qanchaga (Dollarga) almashtirilishini belgilaydi (/almashtir buyrug'i).
DIAMOND_TO_DOLLAR_RATE = 250

# Ball (ochko) tizimi — kunlik/haftalik/oylik reyting shu ballar asosida hisoblanadi.
POINTS_WIN = 10
POINTS_LOSE = 3
POINTS_TOP_BONUS = 50
POINTS_TOP_BONUS_COUNT = 3
POINTS_BIG_GAME_MIN_PLAYERS = 10

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


MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON, Role.LAWYER)


def _did_win(role: Role, winner: str) -> bool:
    if winner == "killer":
        return role == Role.KILLER
    if winner == "mafia":
        return role in MAFIA_TEAM_ROLES
    # town — Yollanma qotil alohida g'alaba sharti yo'q, tomon natijasiga qo'shiladi
    return role not in MAFIA_TEAM_ROLES and role != Role.KILLER


def _top_bonus_ids(game: Game, winner: str) -> set[int]:
    """>10 o'yinchili o'yinlarda g'olib bo'lgan (afzalroq — tirik qolgan) top-3ga 50 balldan beriladi."""
    if len(game.players) <= POINTS_BIG_GAME_MIN_PLAYERS:
        return set()
    winners = [p for p in game.players.values() if _did_win(p.role, winner)]
    ordered = sorted(winners, key=lambda p: not p.alive)
    return {p.user_id for p in ordered[:POINTS_TOP_BONUS_COUNT]}


async def payout_game_results(game: Game, winner: str) -> list[tuple[int, str]]:
    """Har bir o'yinchi uchun (user_id, shaxsiy natija xabari) qaytaradi — guruhga emas,
    faqat o'sha o'yinchining o'ziga yuboriladi."""
    private_messages: list[tuple[int, str]] = []
    top_bonus_ids = _top_bonus_ids(game, winner)

    for p in game.players.values():
        won = _did_win(p.role, winner)
        points = (POINTS_TOP_BONUS if p.user_id in top_bonus_ids else POINTS_WIN) if won else POINTS_LOSE
        status = "🟢 tirik" if p.alive else "⚰️ halok"

        if winner == "killer" and p.role == Role.KILLER:
            total = KILLER_SOLO_WIN_DOLLARS
            await db.add_balance(p.user_id, dollars=total)
            await db.record_game_result(p.user_id, won)
            await db.add_points(p.user_id, points)
            text = (
                f"🎭 Rolingiz: {ROLE_NAMES[p.role]} ({status})\n\n"
                f"🔪 Siz yakka o'zingiz g'alaba qozondingiz!\n"
                f"💰 +{total}💵  🏅 +{points} ball"
            )
            private_messages.append((p.user_id, text))
            continue

        total = DOLLARS_WIN_MAFIA if won and p.role in MAFIA_TEAM_ROLES else (DOLLARS_WIN_OTHER if won else DOLLARS_LOSE)

        detective_bonus = 0
        if p.role == Role.DETECTIVE and getattr(game, "detective_correct", False):
            detective_bonus = DETECTIVE_BONUS_DOLLARS
            total += detective_bonus

        await db.add_balance(p.user_id, dollars=total)
        await db.record_game_result(p.user_id, won)
        await db.add_points(p.user_id, points)

        notes = []
        if detective_bonus:
            notes.append(f"🕵️ komissar bonusi +{detective_bonus}💵")
        note = f" ({', '.join(notes)})" if notes else ""

        outcome_line = "🏆 Siz g'alaba qozondingiz!" if won else "💀 Siz mag'lub bo'ldingiz."
        text = (
            f"🎭 Rolingiz: {ROLE_NAMES[p.role]} ({status})\n\n"
            f"{outcome_line}\n"
            f"💰 +{total}💵  🏅 +{points} ball{note}"
        )
        private_messages.append((p.user_id, text))
    return private_messages
