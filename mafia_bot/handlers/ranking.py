import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import db

router = Router(name="ranking")


async def _reply_top(message: Message, title: str, since: int | None) -> None:
    rows = await db.top_points(since=since, limit=10)
    if not rows:
        await message.answer(f"{title}\n\nHozircha ma'lumot yo'q.")
        return

    lines = [title, ""]
    for i, row in enumerate(rows, 1):
        lines.append(f"{i}. {row['full_name']} — {row['total']} ball")
    await message.answer("\n".join(lines))


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    await _reply_top(message, "🏆 <b>Umumiy TOP (barcha o'yinlar)</b>", since=None)


@router.message(Command("top1"))
async def cmd_top1(message: Message) -> None:
    await _reply_top(message, "🕐 <b>Kunlik TOP</b>", since=int(time.time()) - 86_400)


@router.message(Command("top7"))
async def cmd_top7(message: Message) -> None:
    await _reply_top(message, "📅 <b>Haftalik TOP</b>", since=int(time.time()) - 7 * 86_400)
