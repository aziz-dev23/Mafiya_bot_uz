import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from helpers import make_bot, make_game, private_texts

import texts
from aiogram.exceptions import TelegramForbiddenError
from game.models import Role
from handlers import common, lobby
from i18n import LANGS, get_texts
from utils import TELEGRAM_TEXT_LIMIT


def _callback(data: str, chat_type: str = "supergroup") -> MagicMock:
    callback = MagicMock()
    callback.data = data
    callback.from_user.id = 7
    callback.message.chat.type = chat_type
    callback.answer = AsyncMock()
    return callback


class GuideTest(unittest.IsolatedAsyncioTestCase):
    def test_rules_fit_one_message_in_all_languages(self):
        for lang in LANGS:
            self.assertLess(len(get_texts(lang).RULES_TEXT), TELEGRAM_TEXT_LIMIT, lang)

    def test_full_guide_button_only_with_url(self):
        with patch.object(common, "GUIDE_URL", ""):
            data = [b.callback_data for row in common.build_rules_keyboard().inline_keyboard for b in row]
        self.assertEqual(data, ["guide:roles", "guide:items"])
        with patch.object(common, "GUIDE_URL", "https://telegra.ph/x"):
            first = common.build_rules_keyboard().inline_keyboard[0][0]
        self.assertEqual(first.url, "https://telegra.ph/x")

    def test_lobby_has_rules_button(self):
        kb = lobby.build_lobby_keyboard(make_game(Role.MAFIA))
        self.assertEqual(kb.inline_keyboard[-1][0].callback_data, "guide:rules")

    def test_main_menu_starts_with_rules_button(self):
        from handlers.menu import build_main_menu_keyboard

        first = build_main_menu_keyboard("test_bot").inline_keyboard[0][0]
        self.assertEqual((first.text, first.callback_data), (texts.MENU_RULES, "guide:rules"))

    async def test_sections_go_to_private_chat(self):
        for section, expected in (("rules", texts.RULES_TEXT), ("roles", texts.ROLES_LIST_HEADER),
                                  ("items", texts.ITEMS_LIST_HEADER)):
            bot, callback = make_bot(), _callback(f"guide:{section}")
            await common.on_guide(callback, bot)
            self.assertIn(expected, private_texts(bot, 7)[0])
            callback.answer.assert_awaited_once_with(texts.RULES_SENT_PM)

    async def test_alert_when_bot_cannot_write(self):
        bot, callback = make_bot(), _callback("guide:rules")
        bot.send_message.side_effect = TelegramForbiddenError(method=MagicMock(), message="blocked")
        await common.on_guide(callback, bot)
        callback.answer.assert_awaited_once_with(texts.RULES_PM_FAILED, show_alert=True)
