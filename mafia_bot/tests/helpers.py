import os
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.models import Game, Player, Role  # noqa: E402


def make_game(*roles: Role) -> Game:
    """O'yinchilar 1, 2, 3, ... user_id bilan, berilgan tartibdagi rollarda yaratiladi."""
    game = Game(chat_id=-100, host_id=1)
    for i, role in enumerate(roles, 1):
        game.players[i] = Player(user_id=i, full_name=f"P{i}", role=role)
    return game


def make_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.pin_chat_message = AsyncMock()
    bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
    return bot


def private_texts(bot: MagicMock, user_id: int) -> list[str]:
    return [c.args[1] for c in bot.send_message.call_args_list if c.args[0] == user_id]
