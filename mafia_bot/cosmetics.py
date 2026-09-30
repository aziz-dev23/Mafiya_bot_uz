"""🎨 Kosmetika: unvon (ism oldidan), o'lim uslubi (guruhdagi o'lim xabari), profil ramkasi. O'yinga ta'sir qilmaydi."""
import time

import db
from economy import (
    COSMETICS,
    COSMETICS_BY_KEY,
    CURRENCY_COLUMN,
    DEATH_STYLE,
    FRAME,
    GROUP_TITLE_NAME_MAX,
    TITLE,
    WEEKLY_CHAMPION_SECONDS,
    WEEKLY_CHAMPION_TITLE,
)
from utils import hero_badge


def sellable(kind: str | None = None) -> list[dict]:
    return [c for c in COSMETICS if c["price"] is not None and (kind is None or c["kind"] == kind)]


GROUP_TITLE_PREFIX = db.GROUP_TITLE_PREFIX
# Guruh unvonlari nomlari keshi: chat_id -> "🏰 <nom>" (load_title bilan to'ldiriladi).
_group_titles: dict[int, str] = {}


def group_title_key(chat_id: int) -> str:
    return f"{GROUP_TITLE_PREFIX}{chat_id}"


def title_name(title_key: str | None, L) -> str | None:
    if not title_key:
        return None
    if title_key.startswith(GROUP_TITLE_PREFIX):
        return _group_titles.get(int(title_key[len(GROUP_TITLE_PREFIX):]))
    return L.COSMETIC_NAMES.get(title_key)


def title_prefix(title_key: str | None, L) -> str:
    name = title_name(title_key, L)
    return f"{name} " if name else ""


async def load_title(title_key: str | None) -> None:
    """Guruh unvoni bo'lsa, nomini keshga yuklaydi (display_name sinxron ishlashi uchun)."""
    if title_key and title_key.startswith(GROUP_TITLE_PREFIX):
        chat_id = int(title_key[len(GROUP_TITLE_PREFIX):])
        _group_titles[chat_id] = await group_title_text(chat_id)


async def group_title_text(chat_id: int) -> str:
    from game.settings import load_settings

    settings = await load_settings(chat_id)
    name = (settings.title_name or await db.get_group_title(chat_id) or str(chat_id))[:GROUP_TITLE_NAME_MAX]
    return f"🏰 {name}"


def display_name(name_html: str, L, title_key: str | None = None, hero_level: int = 0, vip: bool = False) -> str:
    """Ro'yxat, o'lim e'loni, o'yin yakuni va /top dagi ism: unvon + ism + 👑 (VIP) + 🦸N."""
    crown = L.VIP_BADGE if vip else ""
    return f"{title_prefix(title_key, L)}{name_html}{crown}{hero_badge(hero_level)}"


def death_line(style_key: str | None, name_html: str, role_name: str | None, L) -> str | None:
    """Egasining o'lim uslubi bo'lsa, guruhga chiqadigan matn (aks holda None). Kim o'ldirgani va qanday
    o'lgani aytilmaydi; role_name=None bo'lsa (rol e'loni o'chiq) rol qismi tushib qoladi."""
    template = L.DEATH_STYLES.get(style_key) if style_key else None
    if not template:
        return None
    text = template.format(name=name_html)
    if role_name is not None:
        text += L.DEATH_STYLE_ROLE.format(role=role_name)
    return text


def frame_line(frame_key: str | None, L) -> str | None:
    return L.FRAME_LINES.get(frame_key) if frame_key else None


async def buy(user_id: int, key: str) -> str:
    """Holat: "not_for_sale", "owned", "no_funds" yoki "ok". Sotib olingan narsa darhol faollashadi."""
    item = COSMETICS_BY_KEY.get(key)
    if not item or item["price"] is None:
        return "not_for_sale"
    if key in await db.owned_cosmetics(user_id):
        return "owned"
    if not await db.spend_balance(user_id, CURRENCY_COLUMN[item["currency"]], item["price"]):
        return "no_funds"
    if not await db.grant_cosmetic(user_id, key):
        # Ikki marta tez bosilgan — ikkinchi to'lov qaytariladi.
        await db.add_balance(user_id, **{CURRENCY_COLUMN[item["currency"]]: item["price"]})
        return "owned"
    await db.set_active_cosmetic(user_id, item["kind"], key)
    return "ok"


def kind_of(key: str) -> str | None:
    if key.startswith(GROUP_TITLE_PREFIX):
        return TITLE
    item = COSMETICS_BY_KEY.get(key)
    return item["kind"] if item else None


async def activate(user_id: int, key: str) -> bool:
    kind = kind_of(key)
    if not kind or key not in await db.owned_cosmetics(user_id):
        return False
    await db.set_active_cosmetic(user_id, kind, key)
    return True


async def take_off(user_id: int, kind: str) -> None:
    await db.set_active_cosmetic(user_id, kind, None)


async def grant_weekly_champion(user_id: int, now: float | None = None) -> None:
    """/top7 1-o'rin egasiga "🏆 Hafta chempioni" — bir hafta; tugagach oldingi unvon qaytadi."""
    expires = int((now or time.time()) + WEEKLY_CHAMPION_SECONDS)
    await db.grant_cosmetic(user_id, WEEKLY_CHAMPION_TITLE, expires_at=expires)
    await db.activate_temporary_cosmetic(user_id, TITLE, WEEKLY_CHAMPION_TITLE)


async def active(user_id: int) -> dict[str, str]:
    result = await db.active_cosmetics(user_id)
    await load_title(result.get(TITLE))
    return result


KINDS = (TITLE, DEATH_STYLE, FRAME)
