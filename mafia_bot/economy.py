import db
from game.models import Game, Role
from texts import ROLE_NAMES

# (olmos miqdori, narxi so'mda) — o'zingizga mos narxlarni shu yerda o'zgartiring
# Baza narx: 1💎 = 990 so'm. Katta paketlarda skidka: 799💎 -10%, 899💎 -15%, 999💎 -20%.
# (Dastlab so'ralgan 10/20/30% variantda 999💎 paketi 799/899💎dan arzonroq chiqib qolardi —
# katta paket har doim ko'proq to'lansin degan mantiqni saqlab qolish uchun foizlar pasaytirildi.)
DIAMOND_PRICE_SOM = 990
DIAMOND_PACKAGES = [
    (1, 990),
    (5, 4_950),
    (10, 9_900),
    (30, 29_000),
    (50, 49_000),
    (799, 711_000),
    (899, 756_000),
    (999, 790_000),
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
    "hero_immunity": {"name": "Geroydan himoya", "emoji": "🔰", "price": 5, "currency": "diamond"},
}

# Geroy — do'kondagi oddiy buyum emas, /geroy orqali sotib olinadigan doimiy profil buyumi.
# Bir marta sotib olingach umrbod profilda qoladi, keyin darajasini cheksiz oshirish mumkin.
HERO_BUY_PRICE_DIAMONDS = 249
HERO_LEVEL_UP_PRICE_DIAMONDS = 100
HERO_BYPASS_LEVEL = 10
# Faqat shu rollarda bo'lgan Geroy egasi tongda zarba berish huquqiga ega.
HERO_ELIGIBLE_ROLES = (Role.MAFIA, Role.DON, Role.DETECTIVE)
# Eski (endi bekor qilingan) hero_shot buyumi narxi — mavjud zaxiralarni qaytarish uchun.
LEGACY_HERO_SHOT_REFUND_DIAMONDS = 90

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


MAFIA_TEAM_ROLES = (Role.MAFIA, Role.DON, Role.LAWYER, Role.HITMAN)


def _did_win(role: Role, winner: str) -> bool:
    if winner == "killer":
        return role == Role.KILLER
    if winner == "mafia":
        return role in MAFIA_TEAM_ROLES
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
