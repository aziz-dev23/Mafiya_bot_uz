"""Tillar: o'zbekcha (lotin) — asosiy matnlar texts.py da; o'zbekcha (kirill) — lotindan avtomatik
transliteratsiya; ruscha — texts_ru.py (yo'q kalitlar o'zbekcha lotinda qoladi).

Foydalanish: L = get_texts(lang); L.SHOP_TITLE ... — texts moduli bilan bir xil nomlar."""
import re
from types import SimpleNamespace

import texts
import texts_ru

UZ = "uz"
UZ_CYRL = "uz_cyrl"
RU = "ru"
LANGS = (UZ, UZ_CYRL, RU)
DEFAULT_LANG = UZ
LANG_NAMES = {UZ: "🇺🇿 O'zbekcha (lotin)", UZ_CYRL: "🇺🇿 Ўзбекча (кирилл)", RU: "🇷🇺 Русский"}

# ---------- Lotin -> kirill transliteratsiya ----------

_APOS = "'ʻ’`ʼ"
_DIGRAPHS = [
    ("sh", "ш"), ("ch", "ч"),
    *[(f"yo{a}", "йў") for a in _APOS],
    *[(f"o{a}", "ў") for a in _APOS],
    *[(f"g{a}", "ғ") for a in _APOS],
    ("ya", "я"), ("yo", "ё"), ("yu", "ю"), ("ye", "е"),
]
_LETTERS = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "x": "х", "y": "й", "z": "з", "c": "к", "w": "в",
}
_TOKEN = re.compile(
    "|".join(re.escape(d) for d, _ in _DIGRAPHS) + "|[a-z]|[" + re.escape(_APOS) + "]",
    re.IGNORECASE,
)
# Tarjima qilinmaydigan qismlar: HTML teglar va entity'lar, {placeholder}, /buyruq, @username, URL, <code>...</code>.
_PROTECTED = re.compile(
    r"<code>.*?</code>|<[^>]+>|&[a-z]+;|\{[^{}]*\}|(?<![A-Za-z0-9'])/[A-Za-z_0-9]+|@[A-Za-z_0-9]+"
    r"|https?://\S+|tg://\S+|\b(?:Telegram|Stars|MVP|AFK|ID|ON|OFF)\b",
    re.DOTALL,
)
# O'zlashma so'zlar — harfma-harf o'girilganda noto'g'ri chiqadi.
_WORD_EXCEPTIONS = {"sudya": "судья"}
_EXCEPTION_RE = re.compile(r"\b(" + "|".join(_WORD_EXCEPTIONS) + r")", re.IGNORECASE)
_DIGRAPH_MAP = {d: c for d, c in _DIGRAPHS}


def _match_case(src: str, cyr: str) -> str:
    if src.isupper() and (len(src) > 1 or len(cyr) == 1):
        return cyr.upper()
    if src[0].isupper():
        return cyr[0].upper() + cyr[1:]
    return cyr


def _translit_plain(text: str) -> str:
    out = []
    pos = 0
    for m in _TOKEN.finditer(text):
        out.append(text[pos : m.start()])
        prev_is_letter = m.start() > 0 and text[m.start() - 1].isalpha()
        token = m.group(0)
        low = token.lower()
        if low in _APOS:
            # tutuq belgisi (ta'lim -> таълим); harf yonida bo'lmasa — oddiy apostrof.
            nxt = text[m.end() : m.end() + 1]
            cyr = "ъ" if prev_is_letter and nxt.isalpha() else token
            out.append(cyr)
        elif low in _DIGRAPH_MAP:
            cyr = _DIGRAPH_MAP[low]
            if low == "ye" and not prev_is_letter:
                cyr = "е"
            out.append(_match_case(token, cyr))
        else:
            cyr = _LETTERS[low]
            if low == "e" and not prev_is_letter:
                cyr = "э"  # so'z boshidagi e -> э
            out.append(_match_case(token, cyr))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _translit_segment(text: str) -> str:
    result, pos = [], 0
    for m in _EXCEPTION_RE.finditer(text):
        result.append(_translit_plain(text[pos : m.start()]))
        result.append(_match_case(m.group(0), _WORD_EXCEPTIONS[m.group(0).lower()]))
        pos = m.end()
    result.append(_translit_plain(text[pos:]))
    return "".join(result)


def to_cyrillic(text: str) -> str:
    """O'zbekcha lotin matnni kirillga o'giradi; HTML, {o'rinbosar}, /buyruq, @username va havolalar saqlanadi."""
    result, pos = [], 0
    for m in _PROTECTED.finditer(text):
        result.append(_translit_segment(text[pos : m.start()]))
        result.append(m.group(0))
        pos = m.end()
    result.append(_translit_segment(text[pos:]))
    return "".join(result)


def _convert(value, fn):
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, dict):
        return {k: _convert(v, fn) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_convert(v, fn) for v in value)
    return value


def _public_texts(module) -> dict:
    return {
        name: value
        for name, value in vars(module).items()
        if name.isupper() and isinstance(value, (str, dict, list, tuple))
    }


def _build() -> dict[str, SimpleNamespace]:
    base = _public_texts(texts)
    ru = dict(base)
    for name, value in _public_texts(texts_ru).items():
        if isinstance(value, dict) and isinstance(base.get(name), dict):
            ru[name] = {**base[name], **value}  # yo'q kalitlar o'zbekcha qoladi
        else:
            ru[name] = value
    return {
        UZ: SimpleNamespace(**base),
        UZ_CYRL: SimpleNamespace(**{k: _convert(v, to_cyrillic) for k, v in base.items()}),
        RU: SimpleNamespace(**ru),
    }


_TEXTS = _build()


def get_texts(lang: str | None) -> SimpleNamespace:
    return _TEXTS.get(lang or DEFAULT_LANG, _TEXTS[DEFAULT_LANG])


# ---------- Foydalanuvchi tili (xotirada kesh + bazada) ----------

_user_lang: dict[int, str] = {}


def cached_user_lang(user_id: int) -> str:
    return _user_lang.get(user_id, DEFAULT_LANG)


def remember_user_lang(user_id: int, lang: str | None) -> None:
    _user_lang[user_id] = lang if lang in LANGS else DEFAULT_LANG


async def user_lang(user_id: int) -> str:
    if user_id not in _user_lang:
        import db

        row = await db.get_user(user_id)
        remember_user_lang(user_id, row["lang"] if row and "lang" in row.keys() else None)
    return _user_lang[user_id]


async def texts_for_user(user_id: int) -> SimpleNamespace:
    return get_texts(await user_lang(user_id))


async def set_user_lang(user_id: int, lang: str) -> None:
    import db

    await db.set_user_lang(user_id, lang)
    remember_user_lang(user_id, lang)


# ---------- Guruh tili ----------

_group_lang: dict[int, str] = {}


def remember_group_lang(chat_id: int, lang: str | None) -> None:
    _group_lang[chat_id] = lang if lang in LANGS else DEFAULT_LANG


async def group_lang(chat_id: int) -> str:
    from game.manager import manager

    game = manager.get_game(chat_id)
    if game is not None:
        return game.settings.lang
    if chat_id not in _group_lang:
        from game.settings import load_settings

        remember_group_lang(chat_id, (await load_settings(chat_id)).lang)
    return _group_lang[chat_id]


# ---------- Middleware: har bir handlerga L (chat tili) va UL (foydalanuvchi tili) ----------

from aiogram import BaseMiddleware  # noqa: E402


class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        chat = data.get("event_chat")
        user_code = await user_lang(user.id) if user else DEFAULT_LANG
        if chat is not None and chat.type in ("group", "supergroup"):
            chat_code = await group_lang(chat.id)
        else:
            chat_code = user_code
        data["L"] = get_texts(chat_code)
        data["UL"] = get_texts(user_code)
        return await handler(event, data)
