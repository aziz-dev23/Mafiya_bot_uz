"""📒 /hisobot — kirim-chiqim hisoboti, faqat bot egasiga (OWNER_IDS): nima sotildi, kim kimga nima berdi,
adminlar qancha berdi, bozor savdolari va bot o'zi bergan mukofotlar."""
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import texts
from config import OWNER_IDS, TIMEZONE_OFFSET_HOURS
from economy import CURRENCY_EMOJI
from owner_share import MILLI
from utils import esc

router = Router(name="report")
TZ = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))
PERIODS = ("today", "week", "month", "all")
STAR_KINDS = ("diamonds", "starter", "gift", "vip", "group_premium")


def period_start(period: str, now: datetime | None = None) -> int:
    now = now or datetime.now(TZ)
    if period == "today":
        return int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    if period == "week":
        return int((now - timedelta(days=7)).timestamp())
    if period == "month":
        return int((now - timedelta(days=30)).timestamp())
    return 0


def _amount(amount: int, currency: str | None) -> str:
    return f"{amount:,}".replace(",", " ") + CURRENCY_EMOJI.get(currency or "", "")


def _time(ts: int) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%d.%m %H:%M")


def stars_block(rows, L) -> list[str]:
    lines = [L.REPORT_STARS_HEADER]
    paid = {r["kind"]: r for r in rows if r["status"] != "refunded"}
    refunded = [r for r in rows if r["status"] == "refunded"]
    total = 0
    for kind in STAR_KINDS:
        r = paid.get(kind)
        if not r:
            continue
        total += r["stars"]
        lines.append(L.REPORT_STARS_LINE.format(
            name=L.REPORT_KIND_NAMES[kind], n=r["n"], stars=r["stars"], diamonds=r["diamonds"]
        ))
    if refunded:
        lines.append(L.REPORT_REFUNDED_LINE.format(
            n=sum(r["n"] for r in refunded), stars=sum(r["stars"] for r in refunded),
            diamonds=sum(r["diamonds"] for r in refunded),
        ))
    if total == 0 and not refunded:
        lines.append(L.REPORT_NONE)
    else:
        lines.append(L.REPORT_STARS_TOTAL.format(stars=total))
    return lines


def card_block(rows, L) -> list[str]:
    by = {r["status"]: r for r in rows}
    if not by:
        return [L.REPORT_CARD_HEADER, L.REPORT_NONE]
    approved = by.get("approved")
    return [
        L.REPORT_CARD_HEADER,
        L.REPORT_CARD_APPROVED.format(
            n=approved["n"] if approved else 0,
            som=_amount(approved["som"] if approved else 0, None),
            diamonds=approved["diamonds"] if approved else 0,
        ),
        L.REPORT_CARD_OTHER.format(
            rejected=by["rejected"]["n"] if "rejected" in by else 0,
            pending=by["pending"]["n"] if "pending" in by else 0,
        ),
    ]


def transfers_block(rows, L) -> list[str]:
    lines = [L.REPORT_TRANSFERS_HEADER]
    for r in rows:
        lines.append(L.REPORT_TRANSFER_LINE.format(n=r["n"], amount=_amount(r["amount"], r["currency"])))
    if not rows:
        lines.append(L.REPORT_NONE)
    return lines


def admins_block(rows, L) -> list[str]:
    lines = [L.REPORT_ADMINS_HEADER]
    by_admin: dict[int, list] = {}
    for r in rows:
        by_admin.setdefault(r["admin_id"], []).append(r)
    for admin_id, items in by_admin.items():
        name = items[0]["full_name"] or str(admin_id)
        parts = [
            L.ADMIN_ACTION_SHORT.get(r["action"], r["action"]).format(
                n=r["n"], amount=_amount(r["amount"], r["currency"])
            )
            for r in items
        ]
        lines.append(L.REPORT_ADMIN_LINE.format(name=esc(name), admin_id=admin_id, parts=", ".join(parts)))
    if not rows:
        lines.append(L.REPORT_NONE)
    return lines


def market_block(rows, L) -> list[str]:
    lines = [L.REPORT_MARKET_HEADER]
    for r in rows:
        lines.append(L.REPORT_MARKET_LINE.format(
            n=r["n"], sold=_amount(r["sold"], r["sell_currency"]), paid=_amount(r["paid"], r["price_currency"])
        ))
    if not rows:
        lines.append(L.REPORT_NONE)
    return lines


def rewards_block(rewards: dict, L) -> list[str]:
    tournaments = {r["status"]: r for r in rewards["tournaments"]}
    finished = tournaments.get("finished")
    return [
        L.REPORT_REWARDS_HEADER,
        L.REPORT_REFERRAL_LINE.format(n=rewards["referral"]["n"], diamonds=rewards["referral"]["amount"]),
        L.REPORT_SHARE_LINE.format(diamonds=round(rewards["share_millis"] / MILLI, 1)),
        L.REPORT_TOURNAMENT_LINE.format(
            n=finished["n"] if finished else 0, diamonds=finished["prize"] if finished else 0,
            active=tournaments["active"]["n"] if "active" in tournaments else 0,
        ),
    ]


def recent_line(r: dict, L) -> str:
    a = esc(r["a_name"] or "—")
    b = esc(r["b_name"] or "—")
    t = _time(r["t"])
    kind = r["type"]
    if kind == "stars":
        mark = L.REPORT_REFUND_MARK if r["status"] == "refunded" else ""
        target = f" → {b}" if r["what"] == "gift" else ""
        return L.REPORT_RECENT["stars"].format(
            t=t, a=a, target=target, name=L.REPORT_KIND_NAMES.get(r["what"], r["what"]),
            diamonds=r["amount"], stars=r["extra"], mark=mark,
        )
    if kind == "card":
        mark = "✅" if r["status"] == "approved" else "❌"
        return L.REPORT_RECENT["card"].format(
            t=t, b=b, diamonds=r["amount"], som=_amount(r["extra"], None), mark=mark, a=a
        )
    if kind == "transfer":
        return L.REPORT_RECENT["transfer"].format(t=t, a=a, b=b, amount=_amount(r["amount"], r["what"]))
    if kind == "admin":
        action = L.ADMIN_ACTION_NAMES.get(r["status"], r["status"]).format(
            amount=r["amount"], emoji=CURRENCY_EMOJI.get(r["what"], ""), note=""
        )
        return L.REPORT_RECENT["admin"].format(t=t, a=a, b=b, action=action)
    return L.REPORT_RECENT["market"].format(
        t=t, a=a, b=b, sold=_amount(r["amount"], r["what"]), paid=_amount(r["extra"], r["status"])
    )


async def build_report(period: str, L=texts) -> str:
    since = period_start(period)
    lines = [L.REPORT_TITLE.format(period=L.REPORT_PERIODS[period]), ""]
    lines += stars_block(await db.report_stars(since), L) + [""]
    lines += card_block(await db.report_card_orders(since), L) + [""]
    lines += transfers_block(await db.report_transfers(since), L) + [""]
    lines += admins_block(await db.report_admin_grants(since), L) + [""]
    lines += market_block(await db.report_market(since), L) + [""]
    lines += rewards_block(await db.report_rewards(since), L) + [""]
    recent = await db.report_recent(since)
    lines.append(L.REPORT_RECENT_HEADER)
    lines += [recent_line(r, L) for r in recent] or [L.REPORT_NONE]
    lines += ["", L.REPORT_FOOTER]
    return "\n".join(lines)


def periods_keyboard(current: str, L=texts) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=("• " if p == current else "") + L.REPORT_PERIODS[p], callback_data=f"report:{p}"
        )
        for p in PERIODS
    ]])


def _trim(text: str) -> str:
    # Telegram xabari 4096 belgidan oshmasligi kerak.
    return text if len(text) <= 4000 else text[:4000] + "\n…"


@router.message(Command("hisobot", "report"), F.chat.type == "private")
async def cmd_report(message: Message, UL=texts) -> None:
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer(_trim(await build_report("today", UL)), reply_markup=periods_keyboard("today", UL))


@router.callback_query(F.data.startswith("report:"))
async def on_report_period(callback: CallbackQuery, UL=texts) -> None:
    if callback.from_user.id not in OWNER_IDS:
        await callback.answer()
        return
    period = callback.data.split(":", 1)[1]
    if period not in PERIODS:
        await callback.answer()
        return
    await callback.answer()
    try:
        await callback.message.edit_text(
            _trim(await build_report(period, UL)), reply_markup=periods_keyboard(period, UL)
        )
    except TelegramBadRequest:
        pass
