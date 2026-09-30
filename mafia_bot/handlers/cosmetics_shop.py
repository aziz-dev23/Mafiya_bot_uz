"""🎨 Kosmetika: /dokon → sotib olish, /sumka → faol narsani tanlash yoki yechish."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import cosmetics
import db
import texts
from economy import COSMETICS, COSMETICS_BY_KEY, CURRENCY_EMOJI, DEATH_STYLE, FRAME

router = Router(name="cosmetics")


def _price(item: dict) -> str:
    return f"{item['price']}{CURRENCY_EMOJI[item['currency']]}"


def _preview(item: dict, L) -> str | None:
    if item["kind"] == DEATH_STYLE:
        line = cosmetics.death_line(item["key"], L.COSMETIC_PREVIEW_NAME, None, L)
        return L.COSMETIC_DEATH_PREVIEW.format(preview=line) if line else None
    if item["kind"] == FRAME:
        return cosmetics.frame_line(item["key"], L)
    return None


def store_view(owned: set[str], L=texts) -> tuple[str, InlineKeyboardMarkup]:
    lines = [L.COSMETICS_STORE_TITLE]
    rows = []
    for kind in cosmetics.KINDS:
        items = cosmetics.sellable(kind)
        if not items:
            continue
        lines += ["", f"<b>{L.COSMETIC_KIND_NAMES[kind]}</b>"]
        for item in items:
            name = L.COSMETIC_NAMES[item["key"]]
            if item["key"] in owned:
                label, data = L.COSMETIC_OWNED_LINE.format(name=name), f"cosm_use:{item['key']}"
            else:
                label = L.COSMETIC_PRICE_LINE.format(name=name, price=_price(item))
                data = f"cosm_buy:{item['key']}"
            lines.append(label)
            preview = _preview(item, L)
            if preview:
                lines.append(f"   {preview}")
            rows.append([InlineKeyboardButton(text=label, callback_data=data)])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


def mine_view(owned: set[str], active: dict[str, str], L=texts) -> tuple[str, InlineKeyboardMarkup]:
    mine = [c for c in COSMETICS if c["key"] in owned]
    if not mine:
        return L.COSMETICS_MY_EMPTY, InlineKeyboardMarkup(inline_keyboard=[])
    lines = [L.COSMETICS_MY_TITLE]
    rows = []
    for kind in cosmetics.KINDS:
        items = [c for c in mine if c["kind"] == kind]
        if not items:
            continue
        lines += ["", f"<b>{L.COSMETIC_KIND_NAMES[kind]}</b>"]
        for item in items:
            name = L.COSMETIC_NAMES[item["key"]]
            label = L.COSMETIC_OWNED_LINE.format(name=name) if active.get(kind) == item["key"] else name
            lines.append(label)
            rows.append([InlineKeyboardButton(text=label, callback_data=f"cosm_use:{item['key']}")])
        if kind in active:
            rows.append([InlineKeyboardButton(
                text=L.COSMETIC_TAKE_OFF.format(kind=L.COSMETIC_KIND_NAMES[kind]), callback_data=f"cosm_off:{kind}"
            )])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


async def _edit(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "cosm:store")
async def on_store(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    await db.ensure_user(callback.from_user.id, callback.from_user.full_name, callback.from_user.username)
    text, kb = store_view(await db.owned_cosmetics(callback.from_user.id), UL)
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "cosm:mine")
async def on_mine(callback: CallbackQuery, UL=texts) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    text, kb = mine_view(await db.owned_cosmetics(user_id), await cosmetics.active(user_id), UL)
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("cosm_buy:"))
async def on_buy(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    await db.ensure_user(user_id, callback.from_user.full_name, callback.from_user.username)
    status = await cosmetics.buy(user_id, key)
    if status == "not_for_sale":
        await callback.answer(UL.COSMETIC_NOT_FOR_SALE, show_alert=True)
        return
    if status == "owned":
        await callback.answer(UL.COSMETIC_ALREADY_OWNED, show_alert=True)
        return
    if status == "no_funds":
        currency = COSMETICS_BY_KEY[key]["currency"]
        await callback.answer(UL.NOT_ENOUGH_BALANCE.format(emoji=CURRENCY_EMOJI[currency]), show_alert=True)
        return
    await callback.answer(UL.COSMETIC_BOUGHT.format(name=UL.COSMETIC_NAMES[key]), show_alert=True)
    text, kb = store_view(await db.owned_cosmetics(user_id), UL)
    await _edit(callback, text, kb)


@router.callback_query(F.data.startswith("cosm_use:"))
async def on_use(callback: CallbackQuery, UL=texts) -> None:
    key = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    if not await cosmetics.activate(user_id, key):
        await callback.answer(UL.COSMETIC_NOT_FOR_SALE, show_alert=True)
        return
    await callback.answer(UL.COSMETIC_ACTIVATED)
    text, kb = mine_view(await db.owned_cosmetics(user_id), await cosmetics.active(user_id), UL)
    await _edit(callback, text, kb)


@router.callback_query(F.data.startswith("cosm_off:"))
async def on_take_off(callback: CallbackQuery, UL=texts) -> None:
    kind = callback.data.split(":", 1)[1]
    if kind not in cosmetics.KINDS:
        await callback.answer()
        return
    user_id = callback.from_user.id
    await cosmetics.take_off(user_id, kind)
    await callback.answer(UL.COSMETIC_REMOVED)
    text, kb = mine_view(await db.owned_cosmetics(user_id), await cosmetics.active(user_id), UL)
    await _edit(callback, text, kb)
