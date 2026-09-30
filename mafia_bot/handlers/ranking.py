from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db
import texts
from utils import esc, hero_badge

router = Router(name="ranking")


async def _reply_top(message: Message, L, title: str, since: int | None) -> None:
    rows = await db.top_points(since=since, limit=10)
    if not rows:
        await message.answer(f"{title}\n\n{L.TOP_EMPTY}")
        return
    lines = [title, ""]
    for i, row in enumerate(rows, 1):
        name = esc(row["full_name"]) + hero_badge(row["hero_level"])
        lines.append(L.TOP_LINE.format(place=i, name=name, total=row["total"]))
    # Foydalanuvchi TOP-10 da bo'lmasa, oxirida uning o'z o'rni ko'rsatiladi.
    user_id = message.from_user.id if message.from_user else None
    if user_id and all(row["user_id"] != user_id for row in rows):
        rank = await db.points_rank(user_id, since)
        if rank:
            lines.append(L.TOP_YOUR_PLACE.format(place=rank[0], total=rank[1]))
    await message.answer("\n".join(lines))


@router.message(Command("top"))
async def cmd_top(message: Message, L=texts) -> None:
    await _reply_top(message, L, L.TOP_ALL_TITLE, since=None)


@router.message(Command("top1"))
async def cmd_top1(message: Message, L=texts) -> None:
    await _reply_top(message, L, L.TOP_DAY_TITLE, since=db.period_starts()["daily"])


@router.message(Command("top7"))
async def cmd_top7(message: Message, L=texts) -> None:
    await _reply_top(message, L, L.TOP_WEEK_TITLE, since=db.period_starts()["weekly"])


@router.message(Command("top30"))
async def cmd_top30(message: Message, L=texts) -> None:
    await _reply_top(message, L, L.TOP_MONTH_TITLE, since=db.period_starts()["monthly"])
