from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

import db
import texts
from economy import HERO_ELIGIBLE_ROLES, ITEMS, MVP_DETECTIVE_FOUND_MAFIA, POISONER_MAX_USES, add_mvp
from game.engine import announce, doctor_forbidden_ids, gt, log, maybe_end_night, team_of, update_mafia_status
from game.manager import manager
from game.models import MAFIA_KILL_ROLES, MAFIA_TEAM_ROLES, Game, GameState, Player, Role
from i18n import get_texts
from utils import build_mafia_kill_keyboard, build_target_keyboard, esc

router = Router(name="night")


async def _night_actor(callback: CallbackQuery, UL, *roles: Role) -> tuple[Game, Player] | None:
    """Tun ekanini va tugmani bosgan o'yinchi tirik hamda kerakli rolda ekanini tekshiradi."""
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer(UL.NOT_NIGHT, show_alert=True)
        return None
    player = game.players.get(callback.from_user.id)
    if not player or not player.alive or player.role not in roles:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return None
    return game, player


async def _target(callback: CallbackQuery, game: Game, UL=texts) -> Player | None:
    raw = callback.data.rsplit(":", 1)[1]
    target = game.players.get(int(raw)) if raw.lstrip("-").isdigit() else None
    if not target or not target.alive:
        await callback.answer(UL.PLAYER_NOT_AVAILABLE, show_alert=True)
        return None
    return target


async def _edit(callback: CallbackQuery, text: str, **kwargs) -> None:
    try:
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest:
        pass


def _log_item(game: Game, owner: Player, key: str) -> None:
    item = ITEMS[key]
    G = gt(game)
    log(game, G.H_ITEM.format(emoji=item["emoji"], owner=esc(owner.full_name), item=G.ITEM_NAMES[key]))


def _acted(game: Game, player: Player) -> bool:
    """O'yinchini shu tun harakat qilganlar ro'yxatiga qo'shadi; birinchi marta bo'lsa True."""
    first_time = player.user_id not in game.night_acted
    game.night_acted.add(player.user_id)
    maybe_end_night(game)
    return first_time


@router.callback_query(F.data.startswith("m_kill:"))
async def on_mafia_kill(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, *MAFIA_KILL_ROLES)
    if not actor:
        return
    game, voter = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if target.role in MAFIA_TEAM_ROLES:
        await callback.answer(UL.NOT_FOR_TEAMMATE, show_alert=True)
        return

    if game.mafia_votes.get(voter.user_id) == target.user_id:
        await callback.answer(UL.VOTE_ALREADY)
        return
    killers = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_KILL_ROLES}
    all_voted_before = killers <= set(game.mafia_votes)
    game.mafia_votes[voter.user_id] = target.user_id
    await callback.answer(UL.YOU_CHOSE_ALERT.format(name=target.full_name))
    # Tugmalar qoladi — vaqt tugaguncha ovozni o'zgartirish mumkin.
    team_ids = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES}
    await _edit(
        callback,
        UL.MAFIA_VOTE_CHOSEN.format(name=esc(target.full_name)),
        reply_markup=build_mafia_kill_keyboard(game, voter.user_id, team_ids),
    )
    await update_mafia_status(bot, game)

    if not all_voted_before and killers <= set(game.mafia_votes):
        announce(bot, game, gt(game).ANN_MAFIA_CHOSE)
    _acted(game, voter)


@router.callback_query(F.data == "m_rifle_toggle")
async def on_rifle_toggle(callback: CallbackQuery, UL=texts) -> None:
    actor = await _night_actor(callback, UL, *MAFIA_KILL_ROLES)
    if not actor:
        return
    game, mafia = actor
    if mafia.items.get("rifle", 0) <= 0:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return

    if mafia.user_id in game.mafia_rifle_users:
        game.mafia_rifle_users.discard(mafia.user_id)
        await callback.answer(UL.RIFLE_TOGGLED_OFF)
    else:
        game.mafia_rifle_users.add(mafia.user_id)
        await callback.answer(UL.RIFLE_TOGGLED_ON)

    team_ids = {p.user_id for p in game.players.values() if p.alive and p.role in MAFIA_TEAM_ROLES}
    try:
        await callback.message.edit_reply_markup(reply_markup=build_mafia_kill_keyboard(game, mafia.user_id, team_ids))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("d_save:"))
async def on_doctor_save(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.DOCTOR)
    if not actor:
        return
    game, doctor = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if target.user_id in doctor_forbidden_ids(game, doctor.user_id):
        await callback.answer(UL.DOCTOR_TARGET_FORBIDDEN, show_alert=True)
        return

    game.doctor_targets[doctor.user_id] = target.user_id
    await callback.answer(UL.YOU_PROTECT_ALERT.format(name=target.full_name))
    await _edit(callback, UL.YOU_PROTECTED.format(name=esc(target.full_name)))
    if _acted(game, doctor):
        announce(bot, game, gt(game).ANN_DOCTOR)


@router.callback_query(F.data.startswith("c_check:"))
async def on_detective_check(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.DETECTIVE)
    if not actor:
        return
    game, detective = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if detective.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_CHECKED, show_alert=True)
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
    result_key = "DETECTIVE_RESULT_MAFIA" if is_mafia else "DETECTIVE_RESULT_CLEAN"
    G = gt(game)
    log(game, G.H_DETECTIVE.format(actor=esc(detective.full_name), target=esc(target.full_name),
                                   result=getattr(G, result_key)))

    await callback.answer()
    await _edit(callback, UL.DETECTIVE_RESULT.format(name=esc(target.full_name), result=getattr(UL, result_key)))
    for sergeant in (p for p in game.players.values() if p.alive and p.role == Role.SERGEANT):
        SL = get_texts(sergeant.lang)
        try:
            await bot.send_message(
                sergeant.user_id,
                SL.SERGEANT_SEES_CHECK.format(name=esc(target.full_name), result=getattr(SL, result_key)),
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    if _acted(game, detective):
        announce(bot, game, G.ANN_DETECTIVE)


@router.callback_query(F.data.startswith("q_kill:"))
async def on_killer_kill(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.KILLER)
    if not actor:
        return
    game, killer = actor
    target = await _target(callback, game, UL)
    if not target:
        return

    game.killer_target = target.user_id
    await callback.answer(UL.YOU_CHOSE_ALERT.format(name=target.full_name))
    await _edit(callback, UL.KILLER_CHOSEN.format(name=esc(target.full_name)))
    if _acted(game, killer):
        announce(bot, game, gt(game).ANN_KILLER)


@router.callback_query(F.data.startswith("yq_kill:"))
async def on_hitman_kill(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.HITMAN)
    if not actor:
        return
    game, hitman = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if target.role in MAFIA_TEAM_ROLES:
        await callback.answer(UL.NOT_FOR_TEAMMATE, show_alert=True)
        return

    game.hitman_target = target.user_id
    await callback.answer(UL.YOU_CHOSE_ALERT.format(name=target.full_name))
    await _edit(callback, UL.HITMAN_CHOSEN.format(name=esc(target.full_name)))
    if _acted(game, hitman):
        announce(bot, game, gt(game).ANN_HITMAN)


@router.callback_query(F.data.startswith("kez_dose:"))
async def on_poisoner_dose(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.POISONER)
    if not actor:
        return
    game, poisoner = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if poisoner.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_POISONED, show_alert=True)
        return
    if game.poison_uses >= POISONER_MAX_USES:
        await callback.answer(UL.POISONER_NO_USES_LEFT, show_alert=True)
        return

    game.poison_uses += 1
    log(game, gt(game).H_POISON.format(actor=esc(poisoner.full_name), target=esc(target.full_name)))
    if target.items.get("poison_shield", 0) > 0 and await db.consume_item(target.user_id, "poison_shield"):
        target.items["poison_shield"] -= 1
        _log_item(game, target, "poison_shield")
        # Kezuvchi natijani bilmaydi — himoya sezilmasdan sarflanadi, dori ta'sirsiz qoladi.
    else:
        game.pending_poison[target.user_id] = game.day_number + 1

    await callback.answer(UL.YOU_POISONED_ALERT.format(name=target.full_name))
    await _edit(callback, UL.YOU_POISONED.format(name=esc(target.full_name)))
    announce(bot, game, gt(game).ANN_POISONER)
    _acted(game, poisoner)


@router.callback_query(F.data.startswith("daydi_visit:"))
async def on_wanderer_visit(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.WANDERER)
    if not actor:
        return
    game, wanderer = actor
    target = await _target(callback, game, UL)
    if not target:
        return

    game.wanderer_target = target.user_id
    await callback.answer(UL.YOU_VISITED_ALERT.format(name=target.full_name))
    await _edit(callback, UL.YOU_VISITED.format(name=esc(target.full_name)))
    if _acted(game, wanderer):
        announce(bot, game, gt(game).ANN_WANDERER)


@router.callback_query(F.data.startswith("don_check:"))
async def on_don_check(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.DON)
    if not actor:
        return
    game, _ = actor
    if game.don_check_used:
        await callback.answer(UL.ALREADY_USED_ABILITY, show_alert=True)
        return
    target = await _target(callback, game, UL)
    if not target:
        return

    game.don_check_used = True
    result_key = "DON_RESULT_DETECTIVE" if target.role == Role.DETECTIVE else "DON_RESULT_NOT"
    G = gt(game)
    log(game, G.H_DON_CHECK.format(actor=esc(callback.from_user.full_name), target=esc(target.full_name),
                                   result=getattr(G, result_key)))
    await callback.answer()
    await _edit(callback, UL.DON_RESULT.format(name=esc(target.full_name), result=getattr(UL, result_key)))
    announce(bot, game, G.ANN_DON)


@router.callback_query(F.data.startswith("advokat_shield:"))
async def on_advokat_shield(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.LAWYER)
    if not actor:
        return
    game, lawyer = actor
    target = await _target(callback, game, UL)
    if not target:
        return

    game.advokat_target = target.user_id
    await callback.answer(UL.YOU_PROTECT_ALERT.format(name=target.full_name))
    await _edit(callback, UL.LAWYER_CHOSEN.format(name=esc(target.full_name)))
    if _acted(game, lawyer):
        announce(bot, game, gt(game).ANN_LAWYER)


@router.callback_query(F.data.startswith("guard:"))
async def on_bodyguard(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.BODYGUARD)
    if not actor:
        return
    game, guard = actor
    target = await _target(callback, game, UL)
    if not target:
        return
    if target.user_id == guard.user_id:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return

    game.bodyguard_targets[guard.user_id] = target.user_id
    await callback.answer()
    await _edit(callback, UL.BODYGUARD_CHOSEN.format(name=esc(target.full_name)))
    if _acted(game, guard):
        announce(bot, game, gt(game).ANN_BODYGUARD)


@router.callback_query(F.data.startswith("spy:"))
async def on_spy(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.SPY)
    if not actor:
        return
    game, spy = actor
    if spy.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_LEARNED, show_alert=True)
        return
    target = await _target(callback, game, UL)
    if not target:
        return

    log(game, gt(game).H_SPY.format(actor=esc(spy.full_name), target=esc(target.full_name)))
    await callback.answer()
    await _edit(callback, UL.SPY_RESULT.format(name=esc(target.full_name), role=UL.ROLE_NAMES[target.role]))
    _acted(game, spy)


@router.callback_query(F.data.startswith("jur1:"))
async def on_journalist_first(callback: CallbackQuery, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.JOURNALIST)
    if not actor:
        return
    game, journalist = actor
    if journalist.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_LEARNED, show_alert=True)
        return
    first = await _target(callback, game, UL)
    if not first:
        return

    game.journalist_first[journalist.user_id] = first.user_id
    await callback.answer()
    await _edit(
        callback,
        UL.JOURNALIST_PROMPT_SECOND.format(first=esc(first.full_name)),
        reply_markup=build_target_keyboard(game, {journalist.user_id, first.user_id}, "jur2"),
    )


@router.callback_query(F.data.startswith("jur2:"))
async def on_journalist_second(callback: CallbackQuery, bot: Bot, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.JOURNALIST)
    if not actor:
        return
    game, journalist = actor
    first = game.players.get(game.journalist_first.get(journalist.user_id, 0))
    second = await _target(callback, game, UL)
    if not second:
        return
    if not first or journalist.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_LEARNED, show_alert=True)
        return

    # Advokat va Soxta hujjat Jurnalistni aldamaydi — haqiqiy jamoa solishtiriladi.
    same = team_of(first) == team_of(second)
    template = UL.JOURNALIST_SAME if same else UL.JOURNALIST_DIFFERENT
    G = gt(game)
    log(game, G.H_JOURNALIST.format(actor=esc(journalist.full_name), first=esc(first.full_name),
                                    second=esc(second.full_name), result=G.H_SAME_TEAM if same else G.H_DIFF_TEAM))
    await callback.answer()
    await _edit(callback, template.format(first=esc(first.full_name), second=esc(second.full_name)))
    if _acted(game, journalist):
        announce(bot, game, G.ANN_JOURNALIST)


@router.callback_query(F.data.startswith("cupid1:"))
async def on_cupid_first(callback: CallbackQuery, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.CUPID)
    if not actor:
        return
    game, cupid = actor
    if game.lovers is not None or cupid.user_id in game.night_acted:
        await callback.answer(UL.ALREADY_CHOSEN, show_alert=True)
        return
    first = await _target(callback, game, UL)
    if not first:
        return

    game.cupid_pick = [first.user_id]
    await callback.answer()
    await _edit(
        callback,
        UL.CUPID_PROMPT_SECOND.format(first=esc(first.full_name)),
        reply_markup=build_target_keyboard(game, {first.user_id}, "cupid2"),
    )


@router.callback_query(F.data.startswith("cupid2:"))
async def on_cupid_second(callback: CallbackQuery, UL=texts) -> None:
    actor = await _night_actor(callback, UL, Role.CUPID)
    if not actor:
        return
    game, cupid = actor
    second = await _target(callback, game, UL)
    if not second:
        return
    if len(game.cupid_pick) != 1 or second.user_id == game.cupid_pick[0]:
        await callback.answer(UL.ALREADY_CHOSEN, show_alert=True)
        return

    game.cupid_pick.append(second.user_id)
    first = game.players[game.cupid_pick[0]]
    await callback.answer()
    await _edit(callback, UL.CUPID_CHOSEN.format(first=esc(first.full_name), second=esc(second.full_name)))
    _acted(game, cupid)


@router.callback_query(F.data.startswith("guess:"))
async def on_guess(callback: CallbackQuery, UL=texts) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.NIGHT:
        await callback.answer(UL.NOT_NIGHT, show_alert=True)
        return
    guesser = game.players.get(callback.from_user.id)
    if not guesser or not guesser.alive or guesser.user_id in game.night_expected:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return
    target = await _target(callback, game, UL)
    if not target:
        return

    game.guesses[guesser.user_id] = target.user_id
    await callback.answer()
    await _edit(callback, UL.GUESS_CHOSEN.format(name=esc(target.full_name)))


@router.callback_query(F.data.startswith("hero_shot:"))
async def on_hero_shot(callback: CallbackQuery, UL=texts) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.state != GameState.DAWN:
        await callback.answer(UL.NOT_DAWN, show_alert=True)
        return

    shooter = game.players.get(callback.from_user.id)
    if not shooter or not shooter.alive or shooter.hero_level <= 0 or shooter.role not in HERO_ELIGIBLE_ROLES:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return
    if shooter.user_id in game.hero_shot_used:
        await callback.answer(UL.HERO_SHOT_ALREADY_USED, show_alert=True)
        return
    target = await _target(callback, game, UL)
    if not target:
        return

    game.dawn_shots[shooter.user_id] = target.user_id
    game.dawn_acted.add(shooter.user_id)
    await callback.answer(UL.HERO_CHOSEN_ALERT.format(name=target.full_name))
    await _edit(callback, UL.HERO_CHOSEN.format(name=esc(target.full_name)))


@router.callback_query(F.data.startswith("sorcerer_revenge:"))
async def on_sorcerer_revenge(callback: CallbackQuery, UL=texts) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    if not game or game.revenge_event is None:
        await callback.answer(UL.ABILITY_GONE, show_alert=True)
        return

    sorcerer = game.players.get(callback.from_user.id)
    if not sorcerer or sorcerer.role != Role.SORCERER:
        await callback.answer(UL.NOT_FOR_YOU, show_alert=True)
        return
    target = await _target(callback, game, UL)
    if not target:
        return

    game.revenge_target = target.user_id
    await callback.answer(UL.REVENGE_CHOSEN_ALERT.format(name=target.full_name))
    await _edit(callback, UL.REVENGE_CHOSEN.format(name=esc(target.full_name)))
    game.revenge_event.set()


@router.callback_query(F.data == "judge_cancel")
async def on_judge_cancel(callback: CallbackQuery, UL=texts) -> None:
    game = manager.get_game_by_player(callback.from_user.id)
    judge = game.players.get(callback.from_user.id) if game else None
    if not game or game.judge_event is None or not judge or not judge.alive or judge.role != Role.JUDGE:
        await callback.answer(UL.JUDGE_TOO_LATE, show_alert=True)
        return
    game.judge_event.set()
    await callback.answer()
    await _edit(callback, UL.JUDGE_DONE)


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
    line = texts.MAFIA_CHAT_LINE.format(name=esc(player.full_name), text=esc(message.text))  # tilga bog'liq emas
    for mate in game.players.values():
        if mate.alive and mate.role in MAFIA_TEAM_ROLES and mate.user_id != player.user_id:
            try:
                await bot.send_message(mate.user_id, line)
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
