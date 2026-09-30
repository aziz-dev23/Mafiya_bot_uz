import re
import string
import unittest
from unittest.mock import AsyncMock, MagicMock

import helpers  # noqa: F401  (sys.path sozlaydi)

import texts
import texts_ru
from i18n import LANGS, RU, UZ, UZ_CYRL, get_texts, to_cyrillic

# Tilga bog'liq bo'lmagan (faqat emoji/o'rinbosar) matnlar — tarjima shart emas.
LANGUAGE_NEUTRAL = {
    "MAFIA_CHAT_LINE", "MAFIA_VOTE_LINE", "MAFIA_VOTE_PENDING", "DEAD_CHAT_LINE", "H_MAFIA_VOTE", "H_VOTE",
    "SETTINGS_ON", "SETTINGS_OFF", "SHOP_STARS_BUTTON", "INVOICE_LABEL", "PAYSUPPORT_PAYMENT_LINE",
    "PROFILE_ITEM_ON", "PROFILE_ITEM_OFF",
}


def _public(module) -> dict:
    return {n: v for n, v in vars(module).items() if n.isupper() and isinstance(v, (str, dict, list, tuple))}


def _strings(value, prefix=""):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, f"{prefix}[{k}]")


def _placeholders(s: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(s) if name is not None}


def _tags(s: str) -> list[str]:
    return sorted(re.findall(r"</?[a-z]+", s))


def _commands(s: str) -> set[str]:
    return set(re.findall(r"(?<![\w<])/[a-z_0-9]+", s))


class TranslationCompletenessTest(unittest.TestCase):
    def test_every_key_translated_to_russian(self):
        uz, ru = _public(texts), _public(texts_ru)
        missing = set(uz) - set(ru) - LANGUAGE_NEUTRAL
        self.assertEqual(missing, set(), f"texts_ru.py da yo'q: {sorted(missing)}")
        self.assertEqual(set(ru) - set(uz), set(), "texts_ru.py da ortiqcha kalit bor")

    def test_dict_keys_match(self):
        uz, ru = _public(texts), _public(texts_ru)
        for name, value in ru.items():
            if isinstance(value, dict):
                self.assertEqual(set(value), set(uz[name]), name)

    def test_placeholders_tags_commands_match(self):
        uz = get_texts(UZ)
        for lang in (UZ_CYRL, RU):
            other = get_texts(lang)
            for name in vars(uz):
                for path, src in _strings(getattr(uz, name), name):
                    dst = dict(_strings(getattr(other, name), name))[path]
                    with self.subTest(lang=lang, key=path):
                        self.assertEqual(_placeholders(src), _placeholders(dst))
                        self.assertEqual(_tags(src), _tags(dst))
                        self.assertEqual(_commands(src), _commands(dst))

    def test_all_texts_format_without_errors(self):
        """Har bir matn o'z o'rinbosarlari bilan xatosiz formatlanadi."""
        for lang in LANGS:
            L = get_texts(lang)
            for name in vars(L):
                for path, s in _strings(getattr(L, name), name):
                    fields = {k: "x" for k in _placeholders(s)}
                    with self.subTest(lang=lang, key=path):
                        s.format(**fields)


class TransliterationTest(unittest.TestCase):
    def test_words(self):
        cases = {
            "O'yin tugadi": "Ўйин тугади",
            "Qo'shilish": "Қўшилиш",
            "g'alaba": "ғалаба",
            "yo'q": "йўқ",
            "Shahar": "Шаҳар",
            "E'lon": "Эълон",
            "ma'lumot": "маълумот",
            "OLMOS DO'KONI": "ОЛМОС ДЎКОНИ",
            "Yollanma qotil": "Ёлланма қотил",
            "choy": "чой",
            "Coin": "Коин",
            "Sudya": "Судья",
            "yoqish/o'chirish": "ёқиш/ўчириш",
            "Telegram Stars": "Telegram Stars",
        }
        for src, dst in cases.items():
            self.assertEqual(to_cyrillic(src), dst)

    def test_protected_parts_untouched(self):
        s = "Salom <b>{name}</b>, /help va @theaziz_art23 — <code>#{order_id}</code> https://t.me/bot?start=x"
        out = to_cyrillic(s)
        for part in ("<b>", "{name}", "</b>", "/help", "@theaziz_art23", "<code>#{order_id}</code>",
                     "https://t.me/bot?start=x"):
            self.assertIn(part, out)
        self.assertIn("Салом", out)

    def test_cyrillic_namespace(self):
        self.assertEqual(get_texts(UZ_CYRL).SHOP_TITLE, "💎 <b>ОЛМОС ДЎКОНИ</b>")
        self.assertEqual(get_texts("unknown").SHOP_TITLE, texts.SHOP_TITLE)


class LanguageMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    async def test_private_and_group(self):
        import i18n

        i18n.remember_user_lang(501, RU)
        i18n.remember_group_lang(-501, UZ_CYRL)
        mw = i18n.LanguageMiddleware()
        handler = AsyncMock()

        await mw(handler, MagicMock(), {"event_from_user": MagicMock(id=501), "event_chat": MagicMock(type="private")})
        data = handler.await_args.args[1]
        self.assertIs(data["L"], get_texts(RU))
        self.assertIs(data["UL"], get_texts(RU))

        await mw(handler, MagicMock(), {"event_from_user": MagicMock(id=501), "event_chat": MagicMock(id=-501, type="group")})
        data = handler.await_args.args[1]
        self.assertIs(data["L"], get_texts(UZ_CYRL))
        self.assertIs(data["UL"], get_texts(RU))


class PerPlayerLanguageTest(unittest.IsolatedAsyncioTestCase):
    async def test_private_messages_use_player_language(self):
        from unittest.mock import patch

        from game import engine
        from game.models import GameState, Role
        from helpers import make_bot, make_game, private_texts

        game = make_game(Role.DON, Role.MINER, Role.CIVILIAN, Role.CIVILIAN)
        game.players[2].lang = RU
        game.state = GameState.NIGHT
        bot = make_bot()
        with patch.multiple("game.engine.db", add_balance=AsyncMock(), add_item=AsyncMock(), consume_item=AsyncMock()), \
             patch.object(engine.random, "random", return_value=0.99):
            await engine.resolve_night(bot, game)
        self.assertEqual(private_texts(bot, 2), [texts_ru.MINER_FOUND_NOTHING])
        group = [c.args[1] for c in bot.send_message.call_args_list if c.args[0] == game.chat_id]
        self.assertEqual(group, [texts.NIGHT_QUIET])  # guruh tili — standart o'zbekcha


if __name__ == "__main__":
    unittest.main()
