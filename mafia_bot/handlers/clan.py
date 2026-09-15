import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from economy import (
    CLAN_CREATE_COST_DIAMONDS,
    CLAN_CREATE_COST_DOLLARS,
    LEVEL_NAMES,
    clan_bonus_pct,
    clan_capacity,
    clan_level,
)

router = Router(name="clan")

TAG_RE = re.compile(r"^[A-Z0-9]{2,6}$")

ROLE_LABELS = {"don": "👑 Boshliq", "deputy": "⭐️ O'rinbosar", "member": "🥷 Jangchi"}


class ClanCreation(StatesGroup):
    name = State()
    tag = State()
    payment = State()


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


async def build_clan_card(clan_row) -> str:
    level = clan_level(clan_row["xp"])
    members = await db.clan_members(clan_row["clan_id"])
    lines = [
        f"🏰 <b>{clan_row['name']}</b> [{clan_row['tag']}]",
        clan_row["motto"] or "<i>(shior yo'q)</i>",
        "",
        f"📊 Daraja: {level} — {LEVEL_NAMES[level]}",
        f"✨ XP: {clan_row['xp']}",
        f"👥 A'zolar: {len(members)}/{clan_capacity(level)}",
        f"💰 G'azna: {clan_row['treasury_dollars']}💵 / {clan_row['treasury_diamonds']}💎",
        f"📈 G'alaba bonusi: +{clan_bonus_pct(level)}%",
        "",
        "<b>A'zolar:</b>",
    ]
    for m in members:
        lines.append(f"• {role_label(m['clan_role'])} — {m['full_name']}")
    return "\n".join(lines)


async def show_clan_menu(message: Message) -> None:
    clan_row = await db.get_user_clan(message.from_user.id)
    if not clan_row:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏰 Klan yaratish", callback_data="clan:create_start")]]
        )
        await message.answer(
            "Siz hali hech qanday klanga a'zo emassiz.\n\n"
            f"Klan ochish narxi: {CLAN_CREATE_COST_DIAMONDS} 💎 YOKI {CLAN_CREATE_COST_DOLLARS} 💵",
            reply_markup=kb,
        )
        return
    await message.answer(await build_clan_card(clan_row))


@router.message(Command("clan", "myclan"))
async def cmd_clan(message: Message, bot: Bot) -> None:
    await db.ensure_user(message.from_user.id, message.from_user.full_name, message.from_user.username)

    if message.chat.type != "private":
        me = await bot.get_me()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏰 Klan menyusini ochish", url=f"https://t.me/{me.username}?start=clan")]
            ]
        )
        await message.answer("Klan menyusi shaxsiy xabarlarda ochiladi 👇", reply_markup=kb)
        return

    await show_clan_menu(message)


@router.callback_query(F.data == "clan:create_start")
async def on_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if await db.get_user_clan(callback.from_user.id):
        await callback.answer("Siz allaqachon klanga a'zosiz.", show_alert=True)
        return
    await state.set_state(ClanCreation.name)
    await callback.answer()
    await callback.message.answer("Klan nomini kiriting (3-30 belgi):")


@router.message(ClanCreation.name)
async def on_clan_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not (3 <= len(name) <= 30):
        await message.answer("Nom 3 dan 30 belgigacha bo'lishi kerak. Qayta kiriting:")
        return
    if await db.get_clan_by_name_or_tag(name):
        await message.answer("Bu nom band. Boshqa nom kiriting:")
        return

    await state.update_data(name=name)
    await state.set_state(ClanCreation.tag)
    await message.answer("Endi klan tegini kiriting (2-6 ta lotin bosh harf/raqam, masalan: BOSS):")


@router.message(ClanCreation.tag)
async def on_clan_tag(message: Message, state: FSMContext) -> None:
    tag = message.text.strip().upper()
    if not TAG_RE.match(tag):
        await message.answer("Teg 2-6 ta lotin harfi yoki raqamdan iborat bo'lishi kerak. Qayta kiriting:")
        return
    if await db.get_clan_by_name_or_tag(tag):
        await message.answer("Bu teg band. Boshqa teg kiriting:")
        return

    await state.update_data(tag=tag)
    await state.set_state(ClanCreation.payment)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 {CLAN_CREATE_COST_DIAMONDS} Olmos bilan", callback_data="clan:pay:diamond")],
            [InlineKeyboardButton(text=f"💵 {CLAN_CREATE_COST_DOLLARS} Dollar bilan", callback_data="clan:pay:dollar")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="clan:cancel")],
        ]
    )
    await message.answer("To'lov usulini tanlang:", reply_markup=kb)


@router.callback_query(F.data == "clan:cancel", ClanCreation.payment)
async def on_cancel_creation(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi.")
    try:
        await callback.message.edit_text("❌ Klan yaratish bekor qilindi.")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("clan:pay:"), ClanCreation.payment)
async def on_pay(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    name, tag = data.get("name"), data.get("tag")
    if not name or not tag:
        await callback.answer("Xatolik, qaytadan boshlang: /clan", show_alert=True)
        await state.clear()
        return

    currency = callback.data.split(":")[2]
    user_row = await db.get_user(callback.from_user.id)

    if currency == "diamond":
        if user_row["diamonds"] < CLAN_CREATE_COST_DIAMONDS:
            await callback.answer("Olmosingiz yetarli emas.", show_alert=True)
            return
        await db.add_balance(callback.from_user.id, diamonds=-CLAN_CREATE_COST_DIAMONDS)
    else:
        if user_row["dollars"] < CLAN_CREATE_COST_DOLLARS:
            await callback.answer("Dollaringiz yetarli emas.", show_alert=True)
            return
        await db.add_balance(callback.from_user.id, dollars=-CLAN_CREATE_COST_DOLLARS)

    if await db.get_clan_by_name_or_tag(name) or await db.get_clan_by_name_or_tag(tag):
        if currency == "diamond":
            await db.add_balance(callback.from_user.id, diamonds=CLAN_CREATE_COST_DIAMONDS)
        else:
            await db.add_balance(callback.from_user.id, dollars=CLAN_CREATE_COST_DOLLARS)
        await callback.answer("Bu nom/teg band bo'lib qoldi.", show_alert=True)
        await state.clear()
        return

    clan_id = await db.create_clan(name, tag, callback.from_user.id)
    await state.clear()
    await callback.answer("Klan yaratildi! 🎉")

    clan_row = await db.get_clan(clan_id)
    try:
        await callback.message.edit_text(await build_clan_card(clan_row))
    except TelegramBadRequest:
        pass


async def build_topclans_text() -> str:
    clans = await db.top_clans(10)
    if not clans:
        return "Hozircha hech qanday klan yo'q."

    lines = ["🏆 <b>TOP-10 Klanlar</b>", ""]
    for i, c in enumerate(clans, 1):
        level = clan_level(c["xp"])
        lines.append(f"{i}. <b>{c['name']}</b> [{c['tag']}] — {level}-daraja, {c['xp']} XP")
    return "\n".join(lines)


@router.message(Command("topclans"))
async def cmd_topclans(message: Message) -> None:
    await message.answer(await build_topclans_text())


@router.message(Command("cinvite"))
async def cmd_cinvite(message: Message) -> None:
    if not message.reply_to_message:
        await message.answer("Klanga taklif qilish uchun o'yinchining xabariga reply qiling: /cinvite")
        return
    target = message.reply_to_message.from_user
    if target.is_bot:
        await message.answer("Botni klanga taklif qila olmaysiz.")
        return

    inviter_clan = await db.get_user_clan(message.from_user.id)
    if not inviter_clan:
        await message.answer("Sizda klan yo'q.")
        return
    inviter_row = await db.get_user(message.from_user.id)
    if inviter_row["clan_role"] not in ("don", "deputy"):
        await message.answer("Faqat Boshliq yoki O'rinbosar taklif qila oladi.")
        return

    await db.ensure_user(target.id, target.full_name, target.username)
    if await db.get_user_clan(target.id):
        await message.answer(f"{target.full_name} allaqachon boshqa klanda.")
        return

    level = clan_level(inviter_clan["xp"])
    count = await db.clan_member_count(inviter_clan["clan_id"])
    if count >= clan_capacity(level):
        await message.answer("Klan sig'imi to'lgan. Darajani oshiring.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Qabul qilish",
                    callback_data=f"cinv:accept:{inviter_clan['clan_id']}:{target.id}",
                ),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"cinv:decline:{target.id}"),
            ]
        ]
    )
    await message.answer(
        f"🏰 <b>{inviter_clan['name']}</b> [{inviter_clan['tag']}] klani "
        f'<a href="tg://user?id={target.id}">{target.full_name}</a>ni taklif qilmoqda!',
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("cinv:accept:"))
async def on_invite_accept(callback: CallbackQuery) -> None:
    _, _, clan_id_str, target_id_str = callback.data.split(":")
    clan_id, target_id = int(clan_id_str), int(target_id_str)

    if callback.from_user.id != target_id:
        await callback.answer("Bu taklif sizga emas.", show_alert=True)
        return
    if await db.get_user_clan(target_id):
        await callback.answer("Siz allaqachon klandasiz.", show_alert=True)
        return

    clan_row = await db.get_clan(clan_id)
    if not clan_row:
        await callback.answer("Klan endi mavjud emas.", show_alert=True)
        return

    level = clan_level(clan_row["xp"])
    count = await db.clan_member_count(clan_id)
    if count >= clan_capacity(level):
        await callback.answer("Klan sig'imi to'lgan.", show_alert=True)
        return

    await db.add_member(clan_id, target_id, "member")
    await callback.answer("Klanga qo'shildingiz! 🎉")
    try:
        await callback.message.edit_text(f"✅ {callback.from_user.full_name} klanga qo'shildi!")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("cinv:decline:"))
async def on_invite_decline(callback: CallbackQuery) -> None:
    target_id = int(callback.data.split(":")[2])
    if callback.from_user.id != target_id:
        await callback.answer("Bu taklif sizga emas.", show_alert=True)
        return
    await callback.answer("Taklif rad etildi.")
    try:
        await callback.message.edit_text("❌ Taklif rad etildi.")
    except TelegramBadRequest:
        pass


@router.message(Command("ckick"))
async def cmd_ckick(message: Message) -> None:
    if not message.reply_to_message:
        await message.answer("A'zoni klandan chiqarish uchun uning xabariga reply qiling: /ckick")
        return
    target = message.reply_to_message.from_user

    actor_row = await db.get_user(message.from_user.id)
    if not actor_row or not actor_row["clan_id"]:
        await message.answer("Sizda klan yo'q.")
        return

    target_row = await db.get_user(target.id)
    if not target_row or target_row["clan_id"] != actor_row["clan_id"]:
        await message.answer(f"{target.full_name} sizning klaningizda emas.")
        return
    if target_row["clan_role"] == "don":
        await message.answer("Boshliqni klandan chiqarib bo'lmaydi.")
        return
    if actor_row["clan_role"] == "member":
        await message.answer("Faqat Boshliq yoki O'rinbosar a'zoni chiqara oladi.")
        return
    if actor_row["clan_role"] == "deputy" and target_row["clan_role"] == "deputy":
        await message.answer("O'rinbosar boshqa o'rinbosarni chiqara olmaydi.")
        return

    await db.remove_member(target.id)
    await message.answer(f"👢 {target.full_name} klandan chiqarildi.")


@router.message(Command("csetrole"))
async def cmd_csetrole(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if not message.reply_to_message or len(parts) < 2 or parts[1].strip().lower() not in ("deputy", "member"):
        await message.answer("Foydalanish: xabarga reply qiling va /csetrole deputy yoki /csetrole member yozing.")
        return
    new_role = parts[1].strip().lower()

    target = message.reply_to_message.from_user
    actor_row = await db.get_user(message.from_user.id)
    if not actor_row or actor_row["clan_role"] != "don":
        await message.answer("Faqat Boshliq rutba bera oladi.")
        return

    target_row = await db.get_user(target.id)
    if not target_row or target_row["clan_id"] != actor_row["clan_id"]:
        await message.answer(f"{target.full_name} sizning klaningizda emas.")
        return
    if target_row["clan_role"] == "don":
        await message.answer("Boshliqning rutbasini o'zgartirib bo'lmaydi.")
        return

    await db.set_role(target.id, new_role)
    await message.answer(f"✅ {target.full_name} endi {role_label(new_role)}.")


@router.message(Command("cdonate"))
async def cmd_cdonate(message: Message) -> None:
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /cdonate 5000 (dollar) yoki /cdonate 5 gem (olmos)")
        return
    amount = int(parts[1])
    if amount <= 0:
        await message.answer("Miqdor musbat bo'lishi kerak.")
        return
    is_diamond = len(parts) >= 3 and parts[2].lower() in ("gem", "diamond", "diamonds", "olmos", "💎")

    clan_row = await db.get_user_clan(message.from_user.id)
    if not clan_row:
        await message.answer("Sizda klan yo'q.")
        return
    user_row = await db.get_user(message.from_user.id)

    if is_diamond:
        if user_row["diamonds"] < amount:
            await message.answer("Olmosingiz yetarli emas.")
            return
        xp_gain = amount * 3
        await db.donate_to_clan(message.from_user.id, clan_row["clan_id"], dollars=0, diamonds=amount, xp=xp_gain)
    else:
        if user_row["dollars"] < amount:
            await message.answer("Dollaringiz yetarli emas.")
            return
        xp_gain = amount // 5000
        await db.donate_to_clan(message.from_user.id, clan_row["clan_id"], dollars=amount, diamonds=0, xp=xp_gain)

    updated_clan = await db.get_clan(clan_row["clan_id"])
    old_level = clan_level(clan_row["xp"])
    new_level = clan_level(updated_clan["xp"])

    unit = "💎" if is_diamond else "💵"
    text = f"🙏 Siz klan g'aznasiga {amount}{unit} ehson qildingiz (+{xp_gain} XP)."
    if new_level > old_level:
        text += f"\n\n🎉 Klan {new_level}-darajaga ko'tarildi: {LEVEL_NAMES[new_level]}!"
    await message.answer(text)


@router.message(Command("cdisband"))
async def cmd_cdisband(message: Message) -> None:
    actor_row = await db.get_user(message.from_user.id)
    if not actor_row or actor_row["clan_role"] != "don":
        await message.answer("Faqat Boshliq klanni tarqata oladi.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, tarqatish", callback_data=f"cdisband:confirm:{actor_row['clan_id']}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="cdisband:cancel"),
            ]
        ]
    )
    await message.answer("⚠️ Klanni butunlay tarqatmoqchimisiz? G'aznadagi mablag' qaytarilmaydi!", reply_markup=kb)


@router.callback_query(F.data.startswith("cdisband:confirm:"))
async def on_disband_confirm(callback: CallbackQuery) -> None:
    clan_id = int(callback.data.split(":")[2])
    actor_row = await db.get_user(callback.from_user.id)
    if not actor_row or actor_row["clan_role"] != "don" or actor_row["clan_id"] != clan_id:
        await callback.answer("Bu amal sizga tegishli emas.", show_alert=True)
        return

    await db.disband_clan(clan_id)
    await callback.answer("Klan tarqatildi.")
    try:
        await callback.message.edit_text("💥 Klan tarqatildi.")
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "cdisband:cancel")
async def on_disband_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Bekor qilindi.")
    try:
        await callback.message.edit_text("Bekor qilindi.")
    except TelegramBadRequest:
        pass
