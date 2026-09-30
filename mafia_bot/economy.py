import db
from game.models import MAFIA_TEAM_ROLES, Game, Player, Role
from i18n import get_texts

# (olmos miqdori, narxi so'mda) — o'zingizga mos narxlarni shu yerda o'zgartiring
# Baza narx: 1💎 = 990 so'm. Katta paketlarda skidka: 799💎 -10%, 899💎 -15%, 999💎 -20%.
# (Dastlab so'ralgan 10/20/30% variantda 999💎 paketi 799/899💎dan arzonroq chiqib qolardi —
# katta paket har doim ko'proq to'lansin degan mantiqni saqlab qolish uchun foizlar pasaytirildi.)
DIAMOND_PRICE_SOM = 990
DIAMOND_PACKAGES = [
    (1, 990),
    (5, 4_950),
    (10, 9_900),
    (30, 29_500),
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
    (30, 149),
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

# Buyum nomlari tillar bo'yicha texts.ITEM_NAMES da.
# Bosqich 1 buyumlari — Mafiya/Doktor/Komissar/Tinch aholi bilan ishlaydiganlar.
ITEMS = {
    "shield": {"emoji": "🛡", "price": 100, "currency": "dollar"},
    "fake_doc": {"emoji": "📁", "price": 190, "currency": "dollar"},
    "vote_shield": {"emoji": "⚖️", "price": 1, "currency": "diamond"},
    "rifle": {"emoji": "🔫", "price": 1, "currency": "diamond"},
    "mirror": {"emoji": "🔮", "price": 20, "currency": "diamond"},
    # Bosqich 2 buyumlari — yangi rollarga (Qotil/Yollanma qotil/Kezuvchi/Daydi/Konchi) bog'liq.
    "killer_shield": {"emoji": "⛑", "price": 2, "currency": "diamond"},
    "poison_shield": {"emoji": "💊", "price": 100, "currency": "dollar"},
    "mask": {"emoji": "🎭", "price": 100, "currency": "dollar"},
    "hero_immunity": {"emoji": "🔰", "price": 5, "currency": "diamond"},
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

# ---------- 🎨 Kosmetika (doimiy, o'yinga ta'sir qilmaydi) ----------
# Turlar: unvon (ism oldidan), o'lim uslubi (guruhdagi o'lim xabari), profil ramkasi (/profile bezagi).
# Har turdan bir vaqtda bittasi faol. price=None — do'konda sotilmaydi (to'plam, mavsum, guruh, chempion).
# Nomlar, o'lim matnlari va ramka qatorlari texts.py dagi COSMETIC_NAMES / DEATH_STYLES / FRAME_LINES da.
TITLE = "title"
DEATH_STYLE = "death"
FRAME = "frame"
COSMETIC_KINDS = (TITLE, DEATH_STYLE, FRAME)
# Unvon matnining ko'pi bilan uzunligi (emoji bilan birga, test tekshiradi).
TITLE_MAX_LENGTH = 16

COSMETICS = [
    # key, turi, narxi, valyutasi
    {"key": "night_guard", "kind": TITLE, "price": 150, "currency": "coin"},
    {"key": "orator", "kind": TITLE, "price": 3000, "currency": "dollar"},
    {"key": "old_fox", "kind": TITLE, "price": 15, "currency": "diamond"},
    {"key": "owl", "kind": TITLE, "price": 15, "currency": "diamond"},
    {"key": "cold_blooded", "kind": TITLE, "price": 30, "currency": "diamond"},
    {"key": "trickster", "kind": TITLE, "price": 30, "currency": "diamond"},
    {"key": "eagle_eye", "kind": TITLE, "price": 30, "currency": "diamond"},
    {"key": "shadow", "kind": TITLE, "price": 60, "currency": "diamond"},
    {"key": "legendary", "kind": TITLE, "price": 60, "currency": "diamond"},
    {"key": "newcomer", "kind": TITLE, "price": None, "currency": None},  # 🌱 boshlang'ich to'plamdan
    {"key": "weekly_champion", "kind": TITLE, "price": None, "currency": None},  # /top7 1-o'rin, 1 hafta
    {"key": "rose", "kind": DEATH_STYLE, "price": 25, "currency": "diamond"},
    {"key": "curtain", "kind": DEATH_STYLE, "price": 25, "currency": "diamond"},
    {"key": "ghost", "kind": DEATH_STYLE, "price": 40, "currency": "diamond"},
    {"key": "lightning", "kind": DEATH_STYLE, "price": 40, "currency": "diamond"},
    {"key": "stars_frame", "kind": FRAME, "price": 20, "currency": "diamond"},
    {"key": "ice_frame", "kind": FRAME, "price": 30, "currency": "diamond"},
    {"key": "fire_frame", "kind": FRAME, "price": 50, "currency": "diamond"},
    # Mavsumiy narsalar (faqat mavsum chiptasi orqali, keyin sotilmaydi).
    {"key": "s1_title", "kind": TITLE, "price": None, "currency": None},
    {"key": "s1_death", "kind": DEATH_STYLE, "price": None, "currency": None},
    {"key": "s1_frame", "kind": FRAME, "price": None, "currency": None},
]
COSMETICS_BY_KEY = {c["key"]: c for c in COSMETICS}
WEEKLY_CHAMPION_TITLE = "weekly_champion"
# Chempion unvoni shuncha soniya amal qiladi (keyingi hafta davomida).
WEEKLY_CHAMPION_SECONDS = 7 * 24 * 3600

# ---------- 🎟 Mavsum chiptasi ----------
# Mavsum har oyning 1-kuni 00:00 (Toshkent) boshlanib, oyning oxirgi kuni tugaydi.
# 1-mavsum shu oydan boshlanadi (yil, oy); keyingilari ketma-ket raqamlanadi.
SEASON_FIRST_MONTH = (2026, 11)
SEASON_PREMIUM_PRICE_DIAMONDS = 50
SEASON_XP_WIN = 3
SEASON_XP_LOSE = 1
SEASON_XP_FIRST_GAME_BONUS = 2
SEASON_XP_MIN_PLAYERS = 6
SEASON_MAX_LEVEL = 30
SEASON_REMINDER_DAYS_BEFORE_END = 3
# Mavsum raqami -> mavsumiy kosmetika kalitlari (nomi texts.SEASON_NAMES da).
SEASON_COSMETICS = {
    1: {"title": "s1_title", "death": "s1_death", "frame": "s1_frame"},
}


def season_level_cost(level: int) -> int:
    """level-darajaga yetish uchun kerak bo'lgan XP (oldingi darajadan)."""
    if level <= 10:
        return 5
    if level <= 20:
        return 7
    return 9


def season_level_for_xp(xp: int) -> int:
    level, need = 0, 0
    while level < SEASON_MAX_LEVEL:
        need += season_level_cost(level + 1)
        if xp < need:
            break
        level += 1
    return level


def season_xp_for_level(level: int) -> int:
    """Shu darajaga yetish uchun jami kerak bo'ladigan XP."""
    return sum(season_level_cost(n) for n in range(1, level + 1))


# Mukofot: ("dollar"|"coin"|"diamond", miqdor), ("item", buyum_kaliti, soni), ("cosmetic", "title"|"death"|"frame").
def season_free_rewards(level: int) -> list[tuple]:
    rewards = [("dollar", 100)] if level % 2 else [("coin", 10)]
    if level in (10, 20, 30):
        rewards.append(("item", "shield", 1))
    return rewards


def season_premium_rewards(level: int) -> list[tuple]:
    if level % 5 == 0:
        rewards = [("diamond", 10)]
    elif level in (3, 13, 23):
        rewards = [("item", "shield", 2)]
    elif level in (7, 17):
        rewards = [("item", "poison_shield", 1)]
    elif level == 27:
        rewards = [("item", "mask", 1)]
    elif level == 12:
        rewards = [("cosmetic", "title")]
    elif level == 22:
        rewards = [("cosmetic", "death")]
    else:
        rewards = [("coin", 20)]
    if level == 30:
        rewards.append(("cosmetic", "frame"))
    return rewards

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
        L = get_texts(p.lang)
        won = did_win(p, winner)
        stats_role = (p.initial_role or p.role).value
        if p.afk:
            await db.record_game_result(p.user_id, False)
            await db.record_role_result(p.user_id, stats_role, False)
            role_line = L.PAYOUT_ROLE_LINE.format(role=L.ROLE_NAMES[p.role], status=L.PAYOUT_DEAD)
            private_messages.append((p.user_id, f"{role_line}\n\n{L.PAYOUT_AFK}"))
            continue
        points = (POINTS_TOP_BONUS if p.user_id in top_bonus_ids else POINTS_WIN) if won else POINTS_LOSE
        status = L.PAYOUT_ALIVE if p.alive else L.PAYOUT_DEAD

        if won and winner == "killer":
            total = KILLER_SOLO_WIN_DOLLARS
        elif won:
            total = DOLLARS_WIN_MAFIA if p.role in MAFIA_TEAM_ROLES else DOLLARS_WIN_OTHER
        else:
            total = DOLLARS_LOSE

        notes = []
        if won and p.alive:
            total += DOLLARS_ALIVE_WINNER_BONUS
            notes.append(L.PAYOUT_NOTE_ALIVE.format(amount=DOLLARS_ALIVE_WINNER_BONUS))
        if p.role == Role.DETECTIVE and game.detective_correct:
            total += DETECTIVE_BONUS_DOLLARS
            notes.append(L.PAYOUT_NOTE_DETECTIVE.format(amount=DETECTIVE_BONUS_DOLLARS))
        if p.user_id in top_bonus_ids:
            notes.append(L.PAYOUT_NOTE_MVP)

        await db.add_balance(p.user_id, dollars=total)
        await db.record_game_result(p.user_id, won)
        await db.record_role_result(p.user_id, stats_role, won)
        await db.add_points(p.user_id, points)

        if won and winner == "killer":
            outcome_line = L.PAYOUT_KILLER_SOLO
        else:
            outcome_line = L.PAYOUT_WON if won else L.PAYOUT_LOST
        note = f" ({', '.join(notes)})" if notes else ""
        text = (
            L.PAYOUT_ROLE_LINE.format(role=L.ROLE_NAMES[p.role], status=status) + "\n\n"
            + outcome_line + "\n"
            + L.PAYOUT_TOTALS.format(dollars=total, points=points, note=note)
        )
        text += await _season_lines(p.user_id, won, len(game.players), L)
        private_messages.append((p.user_id, text))
    return private_messages


async def _season_lines(user_id: int, won: bool, player_count: int, L) -> str:
    """🎟 Mavsum XP'si (AFK bo'lmaganlar uchun) va yetilgan darajalar mukofoti."""
    import season

    result = await season.award_game_xp(user_id, won, player_count)
    if not result:
        return ""
    xp, level, rewards = result
    text = "\n" + L.SEASON_XP_LINE.format(xp=xp, level=level)
    if rewards:
        current = season.current_season()
        text += "\n" + L.SEASON_REWARDS_GOT.format(rewards=", ".join(season.reward_text(r, current, L) for r in rewards))
    return text
