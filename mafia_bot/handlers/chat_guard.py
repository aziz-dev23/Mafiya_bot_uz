from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from game.manager import manager
from game.models import GameState

router = Router(name="chat_guard")

# O'yin davomida guruhda faqat kunduzi yozish mumkin — tun va tong bosqichlarida xabarlar o'chiriladi.
NIGHT_STATES = (GameState.NIGHT, GameState.DAWN)
DAY_STATES = (GameState.DAY_DISCUSSION, GameState.DAY_VOTING, GameState.DAY_CONFIRM)


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def guard_group_chat(message: Message) -> None:
    game = manager.get_game(message.chat.id)
    if not game:
        return

    if game.state in NIGHT_STATES:
        should_delete = True
    elif game.state in DAY_STATES:
        # Halok bo'lgan o'yinchilar kunduzi ham yoza olmaydi.
        player = game.players.get(message.from_user.id) if message.from_user else None
        should_delete = player is not None and not player.alive
    else:
        should_delete = False

    if not should_delete:
        return
    # Bot guruhda "xabarlarni o'chirish" huquqiga ega admin bo'lishi kerak.
    try:
        await message.delete()
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
