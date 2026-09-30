"""🎨 Kosmetika: unvon (ism oldidan), o'lim uslubi (guruhdagi o'lim xabari), profil ramkasi. O'yinga ta'sir qilmaydi."""
import time

import db
from economy import (
    COSMETICS,
    COSMETICS_BY_KEY,
    CURRENCY_COLUMN,
    DEATH_STYLE,
    FRAME,
    TITLE,
    WEEKLY_CHAMPION_SECONDS,
    WEEKLY_CHAMPION_TITLE,
)
from utils import hero_badge


def sellable(kind: str | None = None) -> list[dict]:
    return [c for c in COSMETICS if c["price"] is not None and (kind is None or c["kind"] == kind)]


def title_prefix(title_key: str | None, L) -> str:
    return f"{L.COSMETIC_NAMES[title_key]} " if title_key in L.COSMETIC_NAMES else ""


def display_name(name_html: str, L, title_key: str | None = None, hero_level: int = 0) -> str:
    """Ro'yxat, o'lim e'loni, o'yin yakuni va /top dagi ism: unvon + ism + 🦸N."""
    return f"{title_prefix(title_key, L)}{name_html}{hero_badge(hero_level)}"


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


async def activate(user_id: int, key: str) -> bool:
    item = COSMETICS_BY_KEY.get(key)
    if not item or key not in await db.owned_cosmetics(user_id):
        return False
    await db.set_active_cosmetic(user_id, item["kind"], key)
    return True


async def take_off(user_id: int, kind: str) -> None:
    await db.set_active_cosmetic(user_id, kind, None)


async def grant_weekly_champion(user_id: int, now: float | None = None) -> None:
    """/top7 1-o'rin egasiga "🏆 Hafta chempioni" — bir hafta; tugagach oldingi unvon qaytadi."""
    expires = int((now or time.time()) + WEEKLY_CHAMPION_SECONDS)
    await db.grant_cosmetic(user_id, WEEKLY_CHAMPION_TITLE, expires_at=expires)
    await db.activate_temporary_cosmetic(user_id, TITLE, WEEKLY_CHAMPION_TITLE)


async def active(user_id: int) -> dict[str, str]:
    return await db.active_cosmetics(user_id)


KINDS = (TITLE, DEATH_STYLE, FRAME)
