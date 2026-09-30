import db
from game.models import MAFIA_TEAM_ROLES, Game, Player, Role
import texts
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

DOLLARS_WIN_MAFIA = 40
DOLLARS_WIN_OTHER = 30
DOLLARS_LOSE = 15
# G'olib jamoaning oxirigacha tirik qolgan a'zolariga qo'shimcha mukofot.
DOLLARS_ALIVE_WINNER_BONUS = 10
DETECTIVE_BONUS_DOLLARS = 200
KILLER_SOLO_WIN_DOLLARS = 5000
HITMAN_CONTRACT_BONUS_DOLLARS = 2000

# 1 olmos qanchaga (Dollarga) almashtirilishini belgilaydi (/almashtir buyrug'i).
# Telegram Stars (XTR) orqali olmos paketlari: (olmos miqdori, narxi Stars'da).
# Baza narx: 1💎 = STARS_PER_DIAMOND⭐; katta paketlarda so'mdagi paketlar bilan bir xil chegirma
# (so'mdagi narx / DIAMOND_PRICE_SOM × STARS_PER_DIAMOND, yaxlitlangan).
STARS_PER_DIAMOND = 5
STARS_PACKAGES = [
    (1, 5),
    (5, 25),
    (10, 50),
    (30, 146),
    (50, 247),
    (799, 3591),
    (899, 3818),
    (999, 3990),
]
STARS_CURRENCY = "XTR"

DIAMOND_TO_DOLLAR_RATE = 250
# 1 coin qanchaga (Dollarga) almashtirilishi va /almashtir dagi coin tugmalari.
COIN_TO_DOLLAR_RATE = 10
COIN_EXCHANGE_AMOUNTS = (5, 10, 50, 100)

# Ball (ochko) tizimi — kunlik/haftalik/oylik reyting shu ballar asosida hisoblanadi.
POINTS_WIN = 10
POINTS_LOSE = 3
POINTS_TOP_BONUS = 50
POINTS_TOP_BONUS_COUNT = 3
POINTS_BIG_GAME_MIN_PLAYERS = 10

# MVP ochkolari — 10+ kishilik o'yinda g'oliblar ichida eng ko'p MVP ochkosi to'plagan
# top-3 o'yinchi POINTS_WIN o'rniga POINTS_TOP_BONUS oladi.
MVP_DETECTIVE_FOUND_MAFIA = 3
MVP_DOCTOR_SAVE = 3
MVP_WANDERER_SAW_KILLER = 2
MVP_SORCERER_DRAG = 3
MVP_VOTED_OUT_MAFIA = 1
MVP_MAFIA_KILL_VOTE = 1
MVP_HITMAN_CONTRACT = 3

# Konchi har kecha avtomatik qaziydi: MINER_COIN_CHANCE ehtimol bilan coin,
# keyingi MINER_ITEM_CHANCE ehtimol bilan arzon buyum, qolgan holatda hech narsa.
MINER_COIN_CHANCE = 0.6
MINER_COIN_MIN = 1
MINER_COIN_MAX = 5
MINER_ITEM_CHANCE = 0.1
MINER_ITEM_POOL = ("shield", "mask", "poison_shield")

# Bosqich 1 buyumlari — Mafiya/Doktor/Komissar/Tinch aholi bilan ishlaydiganlar.
ITEMS = {
    "shield": {"name": "Himoya", "emoji": "🛡", "price": 100, "currency": "dollar"},
    "fake_doc": {"name": "Soxta hujjat", "emoji": "📁", "price": 190, "currency": "dollar"},
    "vote_shield": {"name": "Ovozdan himoya", "emoji": "⚖️", "price": 1, "currency": "diamond"},
    "rifle": {"name": "Miltiq", "emoji": "🔫", "price": 1, "currency": "diamond"},
    "mirror": {"name": "Sehrli oyna", "emoji": "🔮", "price": 20, "currency": "diamond"},
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

# Bitta o'yinchida har bir buyum turidan bir o'yinda ko'pi bilan shuncha dona ishlaydi.
ITEM_MAX_USES_PER_GAME = 1

# "Bu tun kim o'ladi?" taxminini to'g'ri topganga beriladigan coin.
GUESS_REWARD_COINS = 2

# Kezuvchi bir o'yinda ko'pi bilan shuncha marta zahar bera oladi.
POISONER_MAX_USES = 2

# Haftalik mukofot: har dushanba 00:00 da o'tgan haftaning /top7 dagi 1-, 2-, 3-o'rinlariga (olmos).
WEEKLY_REWARD_DIAMONDS = (10, 5, 3)

# /send va /sendgem cheklovlari (ADMIN_IDS ga qo'llanmaydi).
TRANSFER_MIN_GAMES = 20
TRANSFER_DAILY_LIMITS = {"dollar": 5000, "diamond": 50}

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



def add_mvp(game: Game, user_id: int, points: int) -> None:
    game.mvp[user_id] = game.mvp.get(user_id, 0) + points


def did_win(player: Player, winner: str) -> bool:
    """G'olib jamoaning barcha a'zolari (halok bo'lganlari ham) yutgan hisoblanadi; AFK sababli chiqarilganlar — yo'q."""
    if player.afk:
        return False
    if winner == "killer":
        return player.role == Role.KILLER
    if winner == "mafia":
        return player.role in MAFIA_TEAM_ROLES
    return player.role not in MAFIA_TEAM_ROLES and player.role != Role.KILLER


def _top_bonus_ids(game: Game, winner: str) -> set[int]:
    """10+ o'yinchili o'yinlarda g'oliblar ichidan MVP ochkosi eng ko'p top-3ga 50 balldan beriladi.
    MVP ochkosi 0 bo'lganlar bonus olmaydi."""
    if len(game.players) < POINTS_BIG_GAME_MIN_PLAYERS:
        return set()
    winners = [p for p in game.players.values() if did_win(p, winner) and game.mvp.get(p.user_id, 0) > 0]
    winners.sort(key=lambda p: game.mvp[p.user_id], reverse=True)
    return {p.user_id for p in winners[:POINTS_TOP_BONUS_COUNT]}


async def payout_game_results(game: Game, winner: str) -> list[tuple[int, str]]:
    """Har bir o'yinchi uchun (user_id, shaxsiy natija xabari) qaytaradi — guruhga emas,
    faqat o'sha o'yinchining o'ziga yuboriladi."""
    private_messages: list[tuple[int, str]] = []
    top_bonus_ids = _top_bonus_ids(game, winner)

    for p in game.players.values():
        won = did_win(p, winner)
        stats_role = (p.initial_role or p.role).value
        if p.afk:
            await db.record_game_result(p.user_id, False)
            await db.record_role_result(p.user_id, stats_role, False)
            private_messages.append((p.user_id, f"🎭 Rolingiz: {ROLE_NAMES[p.role]}\n\n{texts.PAYOUT_AFK}"))
            continue
        points = (POINTS_TOP_BONUS if p.user_id in top_bonus_ids else POINTS_WIN) if won else POINTS_LOSE
        status = "🟢 tirik" if p.alive else "⚰️ halok"

        if won and winner == "killer":
            total = KILLER_SOLO_WIN_DOLLARS
        elif won:
            total = DOLLARS_WIN_MAFIA if p.role in MAFIA_TEAM_ROLES else DOLLARS_WIN_OTHER
        else:
            total = DOLLARS_LOSE

        notes = []
        if won and p.alive:
            total += DOLLARS_ALIVE_WINNER_BONUS
            notes.append(texts.PAYOUT_NOTE_ALIVE.format(amount=DOLLARS_ALIVE_WINNER_BONUS))
        if p.role == Role.DETECTIVE and game.detective_correct:
            total += DETECTIVE_BONUS_DOLLARS
            notes.append(texts.PAYOUT_NOTE_DETECTIVE.format(amount=DETECTIVE_BONUS_DOLLARS))
        if p.user_id in top_bonus_ids:
            notes.append(texts.PAYOUT_NOTE_MVP)

        await db.add_balance(p.user_id, dollars=total)
        await db.record_game_result(p.user_id, won)
        await db.record_role_result(p.user_id, stats_role, won)
        await db.add_points(p.user_id, points)

        if won and winner == "killer":
            outcome_line = texts.PAYOUT_KILLER_SOLO
        else:
            outcome_line = texts.PAYOUT_WON if won else texts.PAYOUT_LOST
        note = f" ({', '.join(notes)})" if notes else ""
        text = (
            f"🎭 Rolingiz: {ROLE_NAMES[p.role]} ({status})\n\n"
            f"{outcome_line}\n"
            f"💰 +{total}💵  🏅 +{points} ball{note}"
        )
        private_messages.append((p.user_id, text))
    return private_messages
