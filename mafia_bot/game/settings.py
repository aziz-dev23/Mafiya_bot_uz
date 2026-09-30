"""Har bir guruhning o'z sozlamalari. Standart qiymatlar .env (config.py) dan olinadi;
guruh o'zgartirgan qiymatlar bazada JSON ko'rinishida saqlanadi (group_settings jadvali)."""
import json
from dataclasses import asdict, dataclass, field, fields

import db
from config import (
    CONFIRM_VOTE_DURATION,
    DAWN_DURATION,
    DAY_DISCUSSION_DURATION,
    DAY_DISCUSSION_MAX,
    DAY_DISCUSSION_PER_PLAYER,
    JUDGE_DURATION,
    LAST_WORD_DURATION,
    MAX_PLAYERS,
    MIN_PLAYERS,
    NIGHT_DURATION,
    REVENGE_DURATION,
    VOTE_DURATION,
    VOTE_MAX,
    VOTE_PER_PLAYER,
)

from .models import Role

MODE_CLASSIC = "classic"
MODE_FAST = "fast"
MODE_NO_ITEMS = "noitems"
MODES = (MODE_CLASSIC, MODE_FAST, MODE_NO_ITEMS)
# Tezkor rejimda barcha vaqtlar shu koeffitsientga ko'paytiriladi.
FAST_MODE_MULTIPLIER = 0.5

LOCK_ALL = "all"
LOCK_PLAYERS = "players"

# O'chirib bo'lmaydigan rollar.
MANDATORY_ROLES = (Role.DON, Role.MAFIA, Role.DETECTIVE)

# /sozlamalar dagi vaqtlar: (maydon, qadam, minimum, maksimum).
TIME_LIMITS = {
    "night": (5, 15, 300),
    "dawn": (5, 10, 120),
    "discussion": (10, 10, 300),
    "vote": (5, 10, 300),
    "confirm": (5, 10, 120),
}
PLAYERS_MIN_BOUND = 4
PLAYERS_MAX_BOUND = 40


@dataclass
class GroupSettings:
    night: int = NIGHT_DURATION
    dawn: int = DAWN_DURATION
    discussion: int = DAY_DISCUSSION_DURATION
    vote: int = VOTE_DURATION
    confirm: int = CONFIRM_VOTE_DURATION
    min_players: int = MIN_PLAYERS
    max_players: int = MAX_PLAYERS
    disabled_roles: list[str] = field(default_factory=list)
    items_enabled: bool = True
    hero_enabled: bool = True
    reveal_roles: bool = True
    last_word: bool = True
    open_votes: bool = True
    lock_mode: str = LOCK_ALL
    mode: str = MODE_CLASSIC
    # "HH:MM" (Toshkent vaqti) — har kuni shu vaqtda ro'yxat avtomatik ochiladi; None — o'chiq.
    auto_time: str | None = None

    # --- Rejimni hisobga olgan "haqiqiy" qiymatlar ---

    @property
    def speed(self) -> float:
        return FAST_MODE_MULTIPLIER if self.mode == MODE_FAST else 1.0

    @property
    def items_active(self) -> bool:
        return self.items_enabled and self.mode != MODE_NO_ITEMS

    @property
    def hero_active(self) -> bool:
        return self.hero_enabled and self.mode != MODE_NO_ITEMS

    def seconds(self, name: str) -> float:
        base = {
            "night": self.night,
            "dawn": self.dawn,
            "confirm": self.confirm,
            "revenge": REVENGE_DURATION,
            "judge": JUDGE_DURATION,
            "last_word": LAST_WORD_DURATION,
        }[name]
        return base * self.speed

    def discussion_seconds(self, alive_count: int) -> float:
        return min(self.discussion + DAY_DISCUSSION_PER_PLAYER * alive_count, DAY_DISCUSSION_MAX) * self.speed

    def vote_seconds(self, alive_count: int) -> float:
        return min(self.vote + VOTE_PER_PLAYER * alive_count, VOTE_MAX) * self.speed

    def disabled_role_set(self) -> set[Role]:
        return {Role(r) for r in self.disabled_roles if r in Role._value2member_map_}

    # --- Saqlash ---

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str | None) -> "GroupSettings":
        settings = cls()
        if not raw:
            return settings
        data = json.loads(raw)
        known = {f.name for f in fields(cls)}
        for key, value in data.items():
            if key in known:
                setattr(settings, key, value)
        return settings


async def load_settings(chat_id: int) -> GroupSettings:
    return GroupSettings.from_json(await db.get_group_settings(chat_id))


async def save_settings(chat_id: int, settings: GroupSettings) -> None:
    await db.set_group_settings(chat_id, settings.to_json())
