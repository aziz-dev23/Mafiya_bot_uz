from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

import db
import texts
from economy import HERO_ELIGIBLE_ROLES, ITEMS, MVP_DETECTIVE_FOUND_MAFIA, POISONER_MAX_USES, add_mvp
from game.engine import announce, doctor_forbidden_ids, log, maybe_end_night, team_of, update_mafia_status
from game.manager import manager
from game.models import MAFIA_KILL_ROLES, MAFIA_TEAM_ROLES, Game, GameState, Player, Role
from texts import ROLE_NAMES
from utils import build_mafia_kill_keyboard, build_target_keyboard, esc

router = Router(name="night")


async def _night_actor(callback: CallbackQuery, *roles: Role) -> tuple[Game, Player] | None:
    """Tun ekanini va tugmani bosgan o'yinchi tirik hamda kerakli rolda ekanini tekshiradi."""
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return None
    player = game.players.get(callback.from_user.id)
    if not player or not player.alive or player.role not in roles:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return None
    return game, player


async def _target(callback: CallbackQuery, game: Game) -> Player | None:
    raw = callback.data.rsplit(":", 1)[1]
    target = game.players.get(int(raw)) if raw.lstrip("-").isdigit() else None
    if not target or not target.alive:
        await callback.answer("Bu o'yinchi mavjud emas.", show_alert=True)
        return None
    return target


async def _edit(callback: CallbackQuery, text: str, **kwargs) -> None:
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest:
        pass


def _log_item(game: Game, owner: Player, key: str) -> None:
    item = ITEMS[key]
    log(game, texts.H_ITEM.format(emoji=item["emoji"], owner=esc(owner.full_name), item=item["name"]))


def _acted(game: Game, player: Player) -> bool:
    """O'yinchini shu tun harakat qilganlar ro'yxatiga qo'shadi; birinchi marta bo'lsa True."""
    first_time = player.user_id not in game.night_acted
    game.night_acted.add(player.user_id)
    maybe_end_night(game)
    return first_time


@router.callback_query(F.data.startswith("m_kill:"))
async def on_mafia_kill(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, *MAFIA_KILL_ROLES)
    if not actor:
        return
    game, voter = actor
    target = await _target(callback, game)
    if not target:
        return
    if target.role in MAFIA_TEAM_ROLES:
        await callback.answer(texts.NOT_FOR_TEAMMATE, show_alert=True)
        return

    if game.mafia_votes.get(voter.user_id) == target.user_id:
        await callback.answer("Ovozingiz allaqachon qabul qilingan.")
        return
    killers = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_KILL_ROLES}
    all_voted_before = killers <= set(game.mafia_votes)
    game.mafia_votes[voter.user_id] = target.user_id
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    # Tugmalar qoladi — vaqt tugaguncha ovozni o'zgartirish mumkin.
    team_ids = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES}
    await _edit(
        callback,
        texts.MAFIA_VOTE_CHOSEN.format(name=esc(target.full_name)),
        reply_markup=build_mafia_kill_keyboard(game, voter.user_id, team_ids),
    )
    await update_mafia_status(bot, game)

    if not all_voted_before and killers <= set(game.mafia_votes):
        announce(bot, game, "🔪 Mafiya o'ljasini tanladi.")
    _acted(game, voter)


@router.callback_query(F.data == "m_rifle_toggle")
async def on_rifle_toggle(callback: CallbackQuery) -> None:
    actor = await _night_actor(callback, *MAFIA_KILL_ROLES)
    if not actor:
        return
    game, mafia = actor
    if mafia.items.get("rifle", 0) <= 0:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    if mafia.user_id in game.mafia_rifle_users:
        game.mafia_rifle_users.discard(mafia.user_id)
        await callback.answer("Miltiq o'chirildi.")
    else:
        game.mafia_rifle_users.add(mafia.user_id)
        await callback.answer("Miltiq yoqildi — himoyani bekor qiladi!")

    team_ids = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES}
    try:
        await callback.message.edit_reply_markup(reply_markup=build_mafia_kill_keyboard(game, mafia.user_id, team_ids))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("d_save:"))
async def on_doctor_save(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.DOCTOR)
    if not actor:
        return
    game, doctor = actor
    target = await _target(callback, game)
    if not target:
        return
    if target.user_id in doctor_forbidden_ids(game, doctor.user_id):
        await callback.answer(texts.DOCTOR_TARGET_FORBIDDEN, show_alert=True)
        return

    game.doctor_targets[doctor.user_id] = target.user_id
    await callback.answer(f"Siz {target.full_name}ni himoya qilyapsiz.")
    await _edit(callback, f"💉 Siz himoya qildingiz: {esc(target.full_name)}")
    if _acted(game, doctor):
        announce(bot, game, "💉 Doktor tungi navbatchilikka ketdi.")


@router.callback_query(F.data.startswith("c_check:"))
async def on_detective_check(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.DETECTIVE)
    if not actor:
        return
    game, detective = actor
    target = await _target(callback, game)
    if not target:
        return
    if detective.user_id in game.night_acted:
        await callback.answer("Siz bu kecha allaqachon tekshirgansiz.", show_alert=True)
        return

    game.detective_target = target.user_id
    faked = False
    if target.items.get("fake_doc", 0) > 0 and await db.consume_item(target.user_id, "fake_doc"):
        target.items["fake_doc"] -= 1
        faked = True
        _log_item(game, target, "fake_doc")
    if target.user_id == game.advokat_target:
        faked = True

    is_mafia = target.role in MAFIA_TEAM_ROLES and not faked
    if is_mafia:
        game.detective_correct = True
        add_mvp(game, detective.user_id, MVP_DETECTIVE_FOUND_MAFIA)
    result = "u — Mafiya a'zosi! 🔪" if is_mafia else "u — mafiya emas. ✅"
    log(game, texts.H_DETECTIVE.format(actor=esc(detective.full_name), target=esc(target.full_name), result=result))

    await callback.answer()
    await _edit(callback, f"🕵️ Tekshiruv natijasi: {esc(target.full_name)} — {result}")
    for sergeant in (p for p in game.players.values() if p.alive and p.role == Role.SERGEANT):
        try:
            await bot.send_message(
                sergeant.user_id, texts.SERGEANT_SEES_CHECK.format(name=esc(target.full_name), result=result)
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    if _acted(game, detective):
        announce(bot, game, "🕵️ Komissar tekshiruvini boshladi.")


@router.callback_query(F.data.startswith("q_kill:"))
async def on_killer_kill(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.KILLER)
    if not actor:
        return
    game, killer = actor
    target = await _target(callback, game)
    if not target:
        return

    game.killer_target = target.user_id
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    await _edit(callback, f"🔪 Siz tanladingiz: {esc(target.full_name)}")
    if _acted(game, killer):
        announce(bot, game, "🔪 Qotil nishonini tanladi.")


@router.callback_query(F.data.startswith("yq_kill:"))
async def on_hitman_kill(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.HITMAN)
    if not actor:
        return
    game, hitman = actor
    target = await _target(callback, game)
    if not target:
        return
    if target.role in MAFIA_TEAM_ROLES:
        await callback.answer(texts.NOT_FOR_TEAMMATE, show_alert=True)
        return

    game.hitman_target = target.user_id
    await callback.answer(f"Siz {target.full_name}ni tanladingiz.")
    await _edit(callback, f"🥷 Siz tanladingiz: {esc(target.full_name)}")
    if _acted(game, hitman):
        announce(bot, game, "🥷 Yollanma qotil nishonini tanladi.")


@router.callback_query(F.data.startswith("kez_dose:"))
async def on_poisoner_dose(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.POISONER)
    if not actor:
        return
    game, poisoner = actor
    target = await _target(callback, game)
    if not target:
        return
    if poisoner.user_id in game.night_acted:
        await callback.answer("Siz bu kecha allaqachon dori bergansiz.", show_alert=True)
        return
    if game.poison_uses >= POISONER_MAX_USES:
        await callback.answer(texts.POISONER_NO_USES_LEFT, show_alert=True)
        return

    game.poison_uses += 1
    log(game, texts.H_POISON.format(actor=esc(poisoner.full_name), target=esc(target.full_name)))
    if target.items.get("poison_shield", 0) > 0 and await db.consume_item(target.user_id, "poison_shield"):
        target.items["poison_shield"] -= 1
        _log_item(game, target, "poison_shield")
        # Kezuvchi natijani bilmaydi — himoya sezilmasdan sarflanadi, dori ta'sirsiz qoladi.
    else:
        game.pending_poison[target.user_id] = game.day_number + 1

    await callback.answer(f"Siz {target.full_name}ga dori berdingiz.")
    await _edit(callback, f"💊 Siz dori berdingiz: {esc(target.full_name)}")
    announce(bot, game, "💊 Kezuvchi kimgadir dori berdi.")
    _acted(game, poisoner)


@router.callback_query(F.data.startswith("daydi_visit:"))
async def on_wanderer_visit(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.WANDERER)
    if not actor:
        return
    game, wanderer = actor
    target = await _target(callback, game)
    if not target:
        return

    game.wanderer_target = target.user_id
    await callback.answer(f"Siz {target.full_name}ning oldiga bordingiz.")
    await _edit(callback, f"🚶 Siz tashrif buyurdingiz: {esc(target.full_name)}")
    if _acted(game, wanderer):
        announce(bot, game, "🚶 Daydi kimningdir oldiga bordi.")


@router.callback_query(F.data.startswith("don_check:"))
async def on_don_check(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.DON)
    if not actor:
        return
    game, _ = actor
    if game.don_check_used:
        await callback.answer("Siz bu imkoniyatdan allaqachon foydalangansiz.", show_alert=True)
        return
    target = await _target(callback, game)
    if not target:
        return

    game.don_check_used = True
    result = "u — Komissar! 🕵️" if target.role == Role.DETECTIVE else "u — komissar emas."
    log(game, texts.H_DON_CHECK.format(actor=esc(callback.from_user.full_name), target=esc(target.full_name),
                                       result=result))
    await callback.answer()
    await _edit(callback, f"🎩 Aniqlash natijasi: {esc(target.full_name)} — {result}")
    announce(bot, game, "🎩 Don o'z tekshiruvini o'tkazdi.")


@router.callback_query(F.data.startswith("advokat_shield:"))
async def on_advokat_shield(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.LAWYER)
    if not actor:
        return
    game, lawyer = actor
    target = await _target(callback, game)
    if not target:
        return

    game.advokat_target = target.user_id
    await callback.answer(f"Siz {target.full_name}ni himoya qilyapsiz.")
    await _edit(callback, f"👨‍💼 Siz himoya qildingiz: {esc(target.full_name)}")
    if _acted(game, lawyer):
        announce(bot, game, "👨‍💼 Advokat o'z himoyasini tayinladi.")


@router.callback_query(F.data.startswith("guard:"))
async def on_bodyguard(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.BODYGUARD)
    if not actor:
        return
    game, guard = actor
    target = await _target(callback, game)
    if not target:
        return
    if target.user_id == guard.user_id:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return

    game.bodyguard_targets[guard.user_id] = target.user_id
    await callback.answer()
    await _edit(callback, texts.BODYGUARD_CHOSEN.format(name=esc(target.full_name)))
    if _acted(game, guard):
        announce(bot, game, "🛡 Tansoqchi navbatchilikka chiqdi.")


@router.callback_query(F.data.startswith("spy:"))
async def on_spy(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.SPY)
    if not actor:
        return
    game, spy = actor
    if spy.user_id in game.night_acted:
        await callback.answer("Siz bu kecha allaqachon bilib olgansiz.", show_alert=True)
        return
    target = await _target(callback, game)
    if not target:
        return

    log(game, texts.H_SPY.format(actor=esc(spy.full_name), target=esc(target.full_name)))
    await callback.answer()
    await _edit(callback, texts.SPY_RESULT.format(name=esc(target.full_name), role=ROLE_NAMES[target.role]))
    _acted(game, spy)


@router.callback_query(F.data.startswith("jur1:"))
async def on_journalist_first(callback: CallbackQuery) -> None:
    actor = await _night_actor(callback, Role.JOURNALIST)
    if not actor:
        return
    game, journalist = actor
    if journalist.user_id in game.night_acted:
        await callback.answer("Siz bu kecha allaqachon bilib olgansiz.", show_alert=True)
        return
    first = await _target(callback, game)
    if not first:
        return

    game.journalist_first[journalist.user_id] = first.user_id
    await callback.answer()
    await _edit(
        callback,
        texts.JOURNALIST_PROMPT_SECOND.format(first=esc(first.full_name)),
        reply_markup=build_target_keyboard(game, {journalist.user_id, first.user_id}, "jur2"),
    )


@router.callback_query(F.data.startswith("jur2:"))
async def on_journalist_second(callback: CallbackQuery, bot: Bot) -> None:
    actor = await _night_actor(callback, Role.JOURNALIST)
    if not actor:
        return
    game, journalist = actor
    first = game.players.get(game.journalist_first.get(journalist.user_id, 0))
    second = await _target(callback, game)
    if not second:
        return
    if not first or journalist.user_id in game.night_acted:
        await callback.answer("Siz bu kecha allaqachon bilib olgansiz.", show_alert=True)
        return

    # Advokat va Soxta hujjat Jurnalistni aldamaydi — haqiqiy jamoa solishtiriladi.
    same = team_of(first) == team_of(second)
    template = texts.JOURNALIST_SAME if same else texts.JOURNALIST_DIFFERENT
    log(game, texts.H_JOURNALIST.format(actor=esc(journalist.full_name), first=esc(first.full_name),
                                        second=esc(second.full_name), result="bir jamoa" if same else "turli jamoa"))
    await callback.answer()
    await _edit(callback, template.format(first=esc(first.full_name), second=esc(second.full_name)))
    if _acted(game, journalist):
        announce(bot, game, "📰 Jurnalist tekshiruv o'tkazdi.")


@router.callback_query(F.data.startswith("cupid1:"))
async def on_cupid_first(callback: CallbackQuery) -> None:
    actor = await _night_actor(callback, Role.CUPID)
    if not actor:
        return
    game, cupid = actor
    if game.lovers is not None or cupid.user_id in game.night_acted:
        await callback.answer("Siz allaqachon tanlagansiz.", show_alert=True)
        return
    first = await _target(callback, game)
    if not first:
        return

    game.cupid_pick = [first.user_id]
    await callback.answer()
    await _edit(
        callback,
        texts.CUPID_PROMPT_SECOND.format(first=esc(first.full_name)),
        reply_markup=build_target_keyboard(game, {first.user_id}, "cupid2"),
    )


@router.callback_query(F.data.startswith("cupid2:"))
async def on_cupid_second(callback: CallbackQuery) -> None:
    actor = await _night_actor(callback, Role.CUPID)
    if not actor:
        return
    game, cupid = actor
    second = await _target(callback, game)
    if not second:
        return
    if len(game.cupid_pick) != 1 or second.user_id == game.cupid_pick[0]:
        await callback.answer("Siz allaqachon tanlagansiz.", show_alert=True)
        return

    game.cupid_pick.append(second.user_id)
    first = game.players[game.cupid_pick[0]]
    await callback.answer()
    await _edit(callback, texts.CUPID_CHOSEN.format(first=esc(first.full_name), second=esc(second.full_name)))
    _acted(game, cupid)


@router.callback_query(F.data.startswith("guess:"))
async def on_guess(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer("Hozir tun emas.", show_alert=True)
        return
    guesser = game.players.get(callback.from_user.id)
    if not guesser or not guesser.alive or guesser.user_id in game.night_expected:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return
    target = await _target(callback, game)
    if not target:
        return

    game.guesses[guesser.user_id] = target.user_id
    await callback.answer()
    await _edit(callback, texts.GUESS_CHOSEN.format(name=esc(target.full_name)))


@router.callback_query(F.data.startswith("hero_shot:"))
async def on_hero_shot(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.DAWN:
        await callback.answer("Hozir tong emas.", show_alert=True)
        return

    shooter = game.players.get(callback.from_user.id)
    if not shooter or not shooter.alive or shooter.hero_level <= 0 or shooter.role not in HERO_ELIGIBLE_ROLES:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return
    if shooter.user_id in game.hero_shot_used:
        await callback.answer(texts.HERO_SHOT_ALREADY_USED, show_alert=True)
        return
    target = await _target(callback, game)
    if not target:
        return

    game.dawn_shots[shooter.user_id] = target.user_id
    game.dawn_acted.add(shooter.user_id)
    await callback.answer(f"Siz {target.full_name}ni otishga qaror qildingiz.")
    await _edit(callback, f"🥷 Siz otishga qaror qildingiz: {esc(target.full_name)}")


@router.callback_query(F.data.startswith("sorcerer_revenge:"))
async def on_sorcerer_revenge(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.revenge_event is None:
        await callback.answer("Bu imkoniyat endi mavjud emas.", show_alert=True)
        return

    sorcerer = game.players.get(callback.from_user.id)
    if not sorcerer or sorcerer.role != Role.SORCERER:
        await callback.answer("Bu tugma siz uchun emas.", show_alert=True)
        return
    target = await _target(callback, game)
    if not target:
        return

    game.revenge_target = target.user_id
    await callback.answer(f"O'ch: {target.full_name}")
    await _edit(callback, f"🧞‍♂️ O'ch tanlandi: {esc(target.full_name)}")
    game.revenge_event.set()


@router.callback_query(F.data == "judge_cancel")
async def on_judge_cancel(callback: CallbackQuery) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    judge = game.players.get(callback.from_user.id) if game else None
    if not game or game.judge_event is None or not judge or not judge.alive or judge.role != Role.JUDGE:
        await callback.answer(texts.JUDGE_TOO_LATE, show_alert=True)
        return
    game.judge_event.set()
    await callback.answer()
    await _edit(callback, texts.JUDGE_DONE)


class MafiaChatFilter(Filter):
    """Tunda Mafiya jamoasining tirik a'zosi botga yozgan oddiy matnli xabar."""

    async def __call__(self, message: Message) -> bool | dict:
        if not message.from_user or not message.text or message.text.startswith("/"):
            return False
        game = manager.get_game_by_player(message.from_user.id)
        if not game or game.state != GameState.NIGHT:
            return False
        player = game.players.get(message.from_user.id)
        if not player or not player.alive or player.role not in MAFIA_TEAM_ROLES:
            return False
        return {"game": game, "player": player}


@router.message(F.chat.type == "private", MafiaChatFilter())
async def on_mafia_chat(message: Message, bot: Bot, game: Game, player: Player) -> None:
    line = texts.MAFIA_CHAT_LINE.format(name=esc(player.full_name), text=esc(message.text))
    for mate in game.players.values():
        if mate.alive and mate.role in MAFIA_TEAM_ROLES and mate.user_id != player.user_id:
            try:
                await bot.send_message(mate.user_id, line)
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
